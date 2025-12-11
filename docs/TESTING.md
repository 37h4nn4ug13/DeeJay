# DeeJay Testing Plan

This document outlines manual and automated test coverage for DeeJay's playback and performance behaviors.

## Latency and Device Compatibility

- **Buffer-size sweep:** Test with typical audio buffer sizes (32, 64, 128, 256, 512 samples) on each supported device/driver pair.
- **Round-trip latency measurement:**
  - Use a loopback harness (physical cable or virtual routing) to measure end-to-end latency with tools such as `jack_iodelay`, `rtl_fm`, or DAW round-trip tests.
  - Record input/output time stamps per buffer size to track variance and drift.
- **Transport verification:** Confirm the engine maintains tempo accuracy within ±0.1 BPM while adjusting buffer sizes.
- **Result logging:** Capture device name, driver, sample rate, buffer size, measured latency, and jitter into a CSV report for each run.

## Glitch-Free Playback Under Load

- **Beat-sync trigger stress:** Continuously fire hot-cues/beat markers at musically dense sections while both decks play.
- **Recording enabled:** Run the stress scenario with simultaneous capture to disk to ensure the recording path does not starve playback.
- **Artefact detection:** Monitor for buffer underruns/overruns, dropouts, or audible glitches; collect engine metrics (XRuns, CPU load, disk throughput).
- **Recovery behavior:** Intentionally introduce short CPU spikes to confirm playback recovers without desync.

## Automated Smoke Tests

Automate core user flows to catch regressions quickly.

1. **Startup and track load**
   - Launch the application and wait for audio engine ready state.
   - Load reference tracks onto Deck A and Deck B from the fixtures directory.
2. **Transport control**
   - Start and stop each deck; verify playhead progress and timecode continuity.
   - Adjust tempo/pitch (±8% and ±16% ranges) and confirm BPM/beatgrid lock.
3. **Performance triggers**
   - Fire a bank of samples/one-shots while playback runs; confirm no audio dropouts.
   - Execute beat-sync triggers/hot-cues on both decks.
4. **Recording**
   - Start a new recording, perform a 60-second mix with the above actions, then stop and save.
   - Validate the recorded file duration, header metadata (sample rate/bit depth), and absence of clipping.

## Instrumentation and Reporting

- **Metrics hooks:** Expose counters for XRuns, buffer fill level, CPU/DSP usage, and disk write latency; emit structured logs per test.
- **Artifacts:** Store latency CSVs, glitch metrics, and rendered recordings in `artifacts/` with timestamped subfolders.
- **CI integration:** Wire smoke tests into the default CI workflow and gate merges on pass/fail status.

## Environment Matrix

| OS           | Driver/Backend | Sample Rates | Buffer Sizes |
|--------------|----------------|--------------|--------------|
| macOS        | CoreAudio      | 44.1, 48 kHz | 32–512       |
| Windows      | WASAPI/ASIO    | 44.1, 48 kHz | 64–512       |
| Linux        | JACK/ALSA      | 44.1, 48 kHz | 64–512       |

## Future Enhancements

- Automate round-trip latency measurement via loopback detection where hardware permits.
- Add spectral comparison of output vs. reference to spot sample-rate or phase issues.
- Introduce long-run soak tests (≥4 hours) to catch cumulative drift or leak regressions.
