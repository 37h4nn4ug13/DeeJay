use crossbeam_queue::ArrayQueue;
use std::sync::Arc;

/// Identifier for a deck feeding the summing bus.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DeckId {
    A = 0,
    B = 1,
}

/// Updates that can be applied to the summing bus from a control thread.
#[derive(Debug, Clone)]
pub enum ParameterUpdate {
    DeckGain { deck: DeckId, gain: f32 },
    Crossfader(f32),
    MasterGain(f32),
}

/// Sender side of a lock-free parameter queue.
#[derive(Clone)]
pub struct ParameterSender {
    queue: Arc<ArrayQueue<ParameterUpdate>>,
}

impl ParameterSender {
    /// Enqueue a parameter update. Returns `Err` if the queue is full.
    pub fn send(&self, update: ParameterUpdate) -> Result<(), ParameterUpdate> {
        self.queue.push(update)
    }
}

/// Receiver side of a lock-free parameter queue.
pub struct ParameterReceiver {
    queue: Arc<ArrayQueue<ParameterUpdate>>,
}

impl ParameterReceiver {
    fn pop(&self) -> Option<ParameterUpdate> {
        self.queue.pop()
    }
}

/// Create a bounded, lock-free channel for parameter updates.
///
/// The sender is intended to be owned by a control thread, while the receiver
/// stays on the audio thread.
pub fn parameter_channel(capacity: usize) -> (ParameterSender, ParameterReceiver) {
    let queue = Arc::new(ArrayQueue::new(capacity));
    (
        ParameterSender {
            queue: queue.clone(),
        },
        ParameterReceiver { queue },
    )
}

/// Summing bus that mixes two stereo decks with an equal-power crossfader and gain stages.
#[derive(Debug)]
pub struct SummingBus {
    deck_gains: [f32; 2],
    crossfader: f32,
    master_gain: f32,
    params: ParameterReceiver,
}

impl SummingBus {
    /// Create a summing bus with unity gains and centered crossfader.
    pub fn new(params: ParameterReceiver) -> Self {
        Self {
            deck_gains: [1.0, 1.0],
            crossfader: 0.5,
            master_gain: 1.0,
            params,
        }
    }

    /// Apply any pending parameter changes from the control thread.
    fn drain_updates(&mut self) {
        while let Some(update) = self.params.pop() {
            match update {
                ParameterUpdate::DeckGain { deck, gain } => {
                    let idx = deck as usize;
                    self.deck_gains[idx] = gain.max(0.0);
                }
                ParameterUpdate::Crossfader(value) => {
                    self.crossfader = value.clamp(0.0, 1.0);
                }
                ParameterUpdate::MasterGain(value) => {
                    self.master_gain = value.max(0.0);
                }
            }
        }
    }

    /// Calculate equal-power crossfader gains for decks A and B.
    fn crossfader_gains(&self) -> (f32, f32) {
        // Map [0, 1] -> [0, PI/2] for equal-power sine/cosine curve.
        let theta = self.crossfader * std::f32::consts::FRAC_PI_2;
        (theta.cos(), theta.sin())
    }

    /// Mix two interleaved stereo buffers into the provided output buffer.
    ///
    /// The method drains pending parameter updates, applies per-deck gains,
    /// crossfader scaling, and a master gain to each frame. All buffers must
    /// share the same length and contain interleaved stereo samples.
    pub fn mix_stereo(&mut self, deck_a: &[f32], deck_b: &[f32], output: &mut [f32]) {
        assert_eq!(
            deck_a.len(),
            deck_b.len(),
            "Deck buffers must have equal length"
        );
        assert_eq!(
            deck_a.len(),
            output.len(),
            "Output buffer must match deck length"
        );
        assert!(
            deck_a.len() % 2 == 0,
            "Buffers must contain interleaved stereo frames"
        );

        self.drain_updates();
        let (xf_a, xf_b) = self.crossfader_gains();
        let deck_a_gain = self.deck_gains[0] * xf_a * self.master_gain;
        let deck_b_gain = self.deck_gains[1] * xf_b * self.master_gain;

        for (((out_l, out_r), a_frame), b_frame) in output
            .chunks_exact_mut(2)
            .zip(deck_a.chunks_exact(2))
            .zip(deck_b.chunks_exact(2))
        {
            *out_l = a_frame[0] * deck_a_gain + b_frame[0] * deck_b_gain;
            *out_r = a_frame[1] * deck_a_gain + b_frame[1] * deck_b_gain;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    fn approx_eq(a: f32, b: f32) {
        assert!((a - b).abs() < 1e-6, "{a} != {b}");
    }

    #[test]
    fn equal_power_crossfader() {
        let (_, rx) = parameter_channel(4);
        let mut bus = SummingBus::new(rx);

        bus.crossfader = 0.0;
        let (a, b) = bus.crossfader_gains();
        approx_eq(a, 1.0);
        approx_eq(b, 0.0);

        bus.crossfader = 0.5;
        let (a, b) = bus.crossfader_gains();
        approx_eq(a, std::f32::consts::FRAC_1_SQRT_2);
        approx_eq(b, std::f32::consts::FRAC_1_SQRT_2);

        bus.crossfader = 1.0;
        let (a, b) = bus.crossfader_gains();
        approx_eq(a, 0.0);
        approx_eq(b, 1.0);
    }

    #[test]
    fn mixes_with_all_gain_stages() {
        let (tx, rx) = parameter_channel(8);
        let mut bus = SummingBus::new(rx);

        // Push parameter updates from a simulated control thread.
        thread::spawn(move || {
            tx.send(ParameterUpdate::DeckGain {
                deck: DeckId::A,
                gain: 0.5,
            })
            .unwrap();
            tx.send(ParameterUpdate::DeckGain {
                deck: DeckId::B,
                gain: 1.5,
            })
            .unwrap();
            tx.send(ParameterUpdate::Crossfader(0.25)).unwrap();
            tx.send(ParameterUpdate::MasterGain(0.8)).unwrap();
        })
        .join()
        .unwrap();

        // Prepare simple stereo frames.
        let deck_a = [1.0, 1.0, 1.0, 1.0];
        let deck_b = [0.5, 0.5, 0.5, 0.5];
        let mut out = [0.0; 4];

        bus.mix_stereo(&deck_a, &deck_b, &mut out);

        // crossfader 0.25 -> gains cos(pi/8) ~0.9238795, sin(pi/8) ~0.3826834
        let xf_a = 0.923_879_5;
        let xf_b = 0.382_683_4;
        let expected_l = 1.0 * 0.5 * xf_a * 0.8 + 0.5 * 1.5 * xf_b * 0.8;
        let expected_r = expected_l;

        approx_eq(out[0], expected_l);
        approx_eq(out[1], expected_r);
        approx_eq(out[2], expected_l);
        approx_eq(out[3], expected_r);
    }
}
