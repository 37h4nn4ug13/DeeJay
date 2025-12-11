declare global {
  interface Window {
    audio: {
      sendParameter: (target: string, value: number | string) => void;
      triggerSampler: (slot: number) => void;
      toggleRecorder: () => void;
      getWaveformCache: () => { deckA: number[]; deckB: number[] };
    };
  }
}

export {};
