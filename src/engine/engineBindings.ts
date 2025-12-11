import { ParameterQueue, ParameterValue } from './parameterQueue';

type EngineQueues = {
  deckAQueue: ParameterQueue;
  deckBQueue: ParameterQueue;
  transportQueue: ParameterQueue;
};

interface WaveformCache {
  deckA: number[];
  deckB: number[];
}

export class EngineBindings {
  private readonly queues: EngineQueues;
  private readonly waveformCache: WaveformCache;
  private recorderEnabled: boolean;

  constructor(queues: EngineQueues) {
    this.queues = queues;
    this.recorderEnabled = false;
    // In lieu of a real engine, generate placeholder waveform values.
    this.waveformCache = {
      deckA: this.generateSineWave(2048, 1),
      deckB: this.generateSineWave(2048, 0.5, Math.PI / 3),
    };
  }

  enqueueParameter(target: string, value: ParameterValue): void {
    const queue = this.routeQueue(target);
    if (!queue.enqueue(target, value)) {
      // eslint-disable-next-line no-console
      console.warn(`Dropped parameter ${target} for ${queue.getChannel()} due to full queue.`);
    }
  }

  triggerSampler(slot: number): void {
    this.queues.transportQueue.enqueue('samplerSlot', slot);
  }

  toggleRecorder(): void {
    this.recorderEnabled = !this.recorderEnabled;
    this.queues.transportQueue.enqueue('recorder', this.recorderEnabled ? 1 : 0);
  }

  getWaveformCache(): WaveformCache {
    return this.waveformCache;
  }

  /**
   * In a production build this would call out to the native audio engine bindings.
   */
  private routeQueue(target: string): ParameterQueue {
    if (target.startsWith('deckA')) {
      return this.queues.deckAQueue;
    }
    if (target.startsWith('deckB')) {
      return this.queues.deckBQueue;
    }
    return this.queues.transportQueue;
  }

  private generateSineWave(size: number, amplitude: number, phase = 0): number[] {
    return Array.from({ length: size }).map((_, i) => {
      const t = (i / size) * Math.PI * 2;
      return Math.sin(t + phase) * amplitude;
    });
  }
}
