// Smart alarm: triggers when current minute is within `windowMin` minutes
// before the target time AND the live phase is "light" (or "awake").
// Falls back to firing exactly at target time if no light phase was caught.

import { classifyPhase } from './analyzer.js';

export class SmartAlarm {
  constructor({ targetTime = null, windowMin = 30 } = {}) {
    this.targetTime = targetTime; // "HH:MM" string or null
    this.windowMin = windowMin;
    this.fired = false;
    this._toneCtx = null;
    this._toneOsc = null;
  }

  set(targetTime) {
    this.targetTime = targetTime || null;
    this.fired = false;
  }

  shouldFire(snap) {
    if (!this.targetTime || this.fired) return false;
    const now = new Date();
    const [h, m] = this.targetTime.split(':').map(Number);
    const target = new Date(now);
    target.setHours(h, m, 0, 0);
    if (target < now) target.setDate(target.getDate() + 1);
    const minsUntil = (target - now) / 60000;

    if (minsUntil <= 0) return true; // hard fallback at the exact target
    if (minsUntil > this.windowMin) return false;
    const phase = classifyPhase({ motion: snap.motion, noise_db: snap.noise, snoring: snap.snoring });
    return phase !== 'deep';
  }

  fire(onAcknowledge) {
    if (this.fired) return;
    this.fired = true;
    this._playTone();
    showBanner(() => {
      this._stopTone();
      onAcknowledge && onAcknowledge();
    });
  }

  _playTone() {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      const ctx = new Ctx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = 880;
      gain.gain.value = 0.15;
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      // Beep on/off pattern.
      this._toneInterval = setInterval(() => {
        gain.gain.value = gain.gain.value > 0 ? 0 : 0.15;
      }, 400);
      this._toneCtx = ctx;
      this._toneOsc = osc;
    } catch {}
  }

  _stopTone() {
    clearInterval(this._toneInterval);
    try { this._toneOsc && this._toneOsc.stop(); } catch {}
    try { this._toneCtx && this._toneCtx.close(); } catch {}
    this._toneCtx = null;
    this._toneOsc = null;
  }
}

function showBanner(onDismiss) {
  const div = document.createElement('div');
  div.className = 'alarm-banner';
  div.innerHTML = '<h2>⏰ Hora de despertar</h2><button>Detener</button>';
  div.querySelector('button').addEventListener('click', () => {
    div.remove();
    onDismiss();
  });
  document.body.appendChild(div);
}
