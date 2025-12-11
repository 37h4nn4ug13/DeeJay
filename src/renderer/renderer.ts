type Track = {
  id: string;
  title: string;
  artist: string;
  bpm: number;
  key: string;
  duration: string;
};

const library: Track[] = [
  { id: 'track1', title: 'Midnight Pulse', artist: 'Nova', bpm: 124, key: 'Am', duration: '5:12' },
  { id: 'track2', title: 'Golden Hour', artist: 'Caldera', bpm: 122, key: 'C#m', duration: '4:45' },
  { id: 'track3', title: 'Skyline', artist: 'Juniper', bpm: 128, key: 'Em', duration: '6:03' },
];

const padCount = 8;

const deckMetadata: Record<string, Track | null> = {
  deckA: library[0],
  deckB: library[1],
};

function renderLibrary(): void {
  const container = document.getElementById('library');
  if (!container) return;

  container.innerHTML = '';
  library.forEach((track) => {
    const card = document.createElement('div');
    card.className = 'track-card';
    card.innerHTML = `
      <div class="track-title">${track.title}</div>
      <div class="track-meta">${track.artist} · ${track.bpm} BPM · ${track.key} · ${track.duration}</div>
    `;
    card.addEventListener('click', () => loadTrack('deckA', track));
    card.addEventListener('contextmenu', (event) => {
      event.preventDefault();
      loadTrack('deckB', track);
    });
    container.appendChild(card);
  });
}

function loadTrack(deck: 'deckA' | 'deckB', track: Track): void {
  deckMetadata[deck] = track;
  updateMetadata(deck, track);
  window.audio.sendParameter(`${deck}.load`, track.id);
}

function updateMetadata(deck: 'deckA' | 'deckB', track: Track | null): void {
  const container = document.getElementById(`${deck}-meta`);
  if (!container) return;

  if (!track) {
    container.textContent = 'Empty';
    return;
  }

  container.textContent = `${track.artist} — ${track.title} (${track.bpm} BPM, ${track.key})`;
}

function wireSlider(id: string, target: string): void {
  const element = document.getElementById(id) as HTMLInputElement | null;
  if (!element) return;

  const send = () => window.audio.sendParameter(target, Number(element.value));
  element.addEventListener('input', send);
  send();
}

function wireCrossfader(): void {
  const crossfader = document.getElementById('crossfade') as HTMLInputElement | null;
  if (!crossfader) return;
  crossfader.addEventListener('input', () => {
    window.audio.sendParameter('transport.crossfade', Number(crossfader.value));
  });
}

function wirePads(): void {
  const pads = document.getElementById('pads');
  if (!pads) return;

  pads.innerHTML = '';
  for (let i = 0; i < padCount; i += 1) {
    const pad = document.createElement('button');
    pad.className = 'pad';
    pad.textContent = `Pad ${i + 1}`;
    pad.addEventListener('click', () => window.audio.triggerSampler(i));
    pads.appendChild(pad);
  }
}

function wireRecorder(): void {
  const recorder = document.getElementById('recorder');
  if (!recorder) return;

  recorder.addEventListener('click', () => {
    recorder.classList.toggle('armed');
    window.audio.toggleRecorder();
  });
}

function drawWaveform(canvasId: string, samples: number[]): void {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement | null;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.beginPath();
  ctx.strokeStyle = '#4fd1c5';
  ctx.lineWidth = 2;

  const step = Math.ceil(samples.length / canvas.width);
  const mid = canvas.height / 2;
  ctx.moveTo(0, mid);

  for (let x = 0; x < canvas.width; x += 1) {
    const start = x * step;
    const slice = samples.slice(start, start + step);
    const peak = Math.max(...slice);
    const trough = Math.min(...slice);
    ctx.lineTo(x, mid - peak * mid);
    ctx.lineTo(x, mid - trough * mid);
  }
  ctx.stroke();
}

function renderWaveforms(): void {
  const cache = window.audio.getWaveformCache();
  drawWaveform('waveformA', cache.deckA);
  drawWaveform('waveformB', cache.deckB);
}

function boot(): void {
  renderLibrary();
  updateMetadata('deckA', deckMetadata.deckA);
  updateMetadata('deckB', deckMetadata.deckB);
  wireSlider('tempoA', 'deckA.tempo');
  wireSlider('tempoB', 'deckB.tempo');
  wireSlider('pitchA', 'deckA.pitch');
  wireSlider('pitchB', 'deckB.pitch');
  wireCrossfader();
  wirePads();
  wireRecorder();
  renderWaveforms();
}

document.addEventListener('DOMContentLoaded', boot);
