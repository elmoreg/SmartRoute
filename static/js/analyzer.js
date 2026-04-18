// Client-side mirror of app/services/analyzer.py for live phase estimation.
// Used to show an instantaneous "phase" hint during recording.

export function classifyPhase(sample) {
  if (sample.motion > 0.45 || sample.noise_db > 65) return 'awake';
  if (sample.motion < 0.08 && !sample.snoring) return 'deep';
  return 'light';
}

export const PHASE_LABEL = {
  awake: 'Despierto',
  light: 'Ligero',
  deep: 'Profundo',
};

export const PHASE_COLOR = {
  awake: '#f59e0b',
  light: '#60a5fa',
  deep: '#5b21b6',
};

export function phaseToY(phase) {
  return phase === 'awake' ? 2 : phase === 'light' ? 1 : 0;
}
