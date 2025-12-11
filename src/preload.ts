import { contextBridge } from 'electron';
import { ParameterQueue } from './engine/parameterQueue';
import { EngineBindings } from './engine/engineBindings';

const deckAQueue = new ParameterQueue('deckA');
const deckBQueue = new ParameterQueue('deckB');
const transportQueue = new ParameterQueue('transport');

const engine = new EngineBindings({
  deckAQueue,
  deckBQueue,
  transportQueue,
});

contextBridge.exposeInMainWorld('audio', {
  sendParameter: (target: string, value: number | string) => {
    engine.enqueueParameter(target, value);
  },
  triggerSampler: (slot: number) => {
    engine.triggerSampler(slot);
  },
  toggleRecorder: () => {
    engine.toggleRecorder();
  },
  getWaveformCache: () => engine.getWaveformCache(),
});
