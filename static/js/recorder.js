// Sleep recorder: captures audio (for noise/snore detection) and motion.
// Emits one aggregated sample per minute.

export class SleepRecorder extends EventTarget {
  constructor({ snoreThreshold = 0.55 } = {}) {
    super();
    this.snoreThreshold = snoreThreshold;
    this.running = false;
    this.startedAt = null;
    this.samples = [];
    this._motionBuf = [];
    this._noiseBuf = [];
    this._snoreBuf = [];
    this._lastMinute = -1;
    this._motionHandler = null;
    this._audioCtx = null;
    this._analyser = null;
    this._micStream = null;
    this._rafId = null;
  }

  setSnoreThreshold(v) { this.snoreThreshold = v; }

  async start() {
    if (this.running) return;
    this.running = true;
    this.startedAt = new Date();
    this.samples = [];
    this._resetBuffers();
    this._lastMinute = -1;

    await this._startAudio();
    this._startMotion();
    this._loop();
    this.dispatchEvent(new Event('started'));
  }

  async stop() {
    if (!this.running) return;
    this.running = false;
    if (this._rafId) cancelAnimationFrame(this._rafId);
    if (this._motionHandler) {
      window.removeEventListener('devicemotion', this._motionHandler);
      this._motionHandler = null;
    }
    if (this._micStream) {
      this._micStream.getTracks().forEach(t => t.stop());
      this._micStream = null;
    }
    if (this._audioCtx) {
      await this._audioCtx.close();
      this._audioCtx = null;
    }
    // Flush last partial minute as a sample so short sessions produce data.
    this._flushMinute(this._currentMinute(), { force: true });
    const endedAt = new Date();
    this.dispatchEvent(new CustomEvent('stopped', {
      detail: { startedAt: this.startedAt, endedAt, samples: this.samples.slice() },
    }));
  }

  async _startAudio() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    this._micStream = stream;
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    this._audioCtx = ctx;
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.6;
    source.connect(analyser);
    this._analyser = analyser;
  }

  _startMotion() {
    let lastMag = null;
    this._motionHandler = (e) => {
      const a = e.accelerationIncludingGravity || e.acceleration;
      if (!a) return;
      const mag = Math.sqrt((a.x||0)**2 + (a.y||0)**2 + (a.z||0)**2);
      if (lastMag != null) {
        this._motionBuf.push(Math.abs(mag - lastMag));
      }
      lastMag = mag;
    };
    window.addEventListener('devicemotion', this._motionHandler);
  }

  _loop = () => {
    if (!this.running) return;
    this._sampleAudio();
    this._maybeFlushMinute();
    this.dispatchEvent(new CustomEvent('tick', { detail: this._liveSnapshot() }));
    this._rafId = requestAnimationFrame(() => setTimeout(this._loop, 200));
  };

  _sampleAudio() {
    if (!this._analyser) return;
    const bins = this._analyser.frequencyBinCount;
    const freq = new Uint8Array(bins);
    this._analyser.getByteFrequencyData(freq);

    // Full-band energy → dB proxy. Map 0..255 average to 0..100 dB-ish.
    let sum = 0;
    for (let i = 0; i < bins; i++) sum += freq[i];
    const avg = sum / bins;
    const db = Math.min(100, Math.max(0, (avg / 255) * 100));
    this._noiseBuf.push(db);

    // Snore detection: ratio of low-band (80-500 Hz) energy to total.
    const sr = this._audioCtx.sampleRate;
    const nyq = sr / 2;
    const binHz = nyq / bins;
    const lo = Math.max(1, Math.floor(80 / binHz));
    const hi = Math.min(bins, Math.ceil(500 / binHz));
    let lowSum = 0, total = 0;
    for (let i = 0; i < bins; i++) {
      total += freq[i];
      if (i >= lo && i < hi) lowSum += freq[i];
    }
    const ratio = total > 0 ? lowSum / total : 0;
    const loud = avg > 25;   // need at least some amplitude
    const snoring = loud && ratio > this.snoreThreshold;
    this._snoreBuf.push(snoring ? 1 : 0);
  }

  _currentMinute() {
    if (!this.startedAt) return 0;
    return Math.floor((Date.now() - this.startedAt.getTime()) / 60000);
  }

  _maybeFlushMinute() {
    const m = this._currentMinute();
    if (m > this._lastMinute && this._lastMinute >= 0) {
      this._flushMinute(this._lastMinute);
    }
    this._lastMinute = m;
  }

  _flushMinute(minute, opts = {}) {
    if (this._motionBuf.length === 0 && this._noiseBuf.length === 0 && !opts.force) return;
    const motionAvg = this._motionBuf.length
      ? this._motionBuf.reduce((a,b) => a+b, 0) / this._motionBuf.length
      : 0;
    // Normalize motion: 0.1 m/s² of variance ≈ 0.5 score (rough, tuned empirically).
    const motion = Math.min(1, motionAvg / 0.5);
    const noise = this._noiseBuf.length
      ? this._noiseBuf.reduce((a,b) => a+b, 0) / this._noiseBuf.length
      : 0;
    const snoringFrac = this._snoreBuf.length
      ? this._snoreBuf.reduce((a,b) => a+b, 0) / this._snoreBuf.length
      : 0;
    this.samples.push({
      minute,
      motion: +motion.toFixed(3),
      noise_db: +noise.toFixed(1),
      snoring: snoringFrac > 0.25,
    });
    this._resetBuffers();
    this.dispatchEvent(new CustomEvent('sample', { detail: this.samples[this.samples.length - 1] }));
  }

  _resetBuffers() {
    this._motionBuf = [];
    this._noiseBuf = [];
    this._snoreBuf = [];
  }

  _liveSnapshot() {
    const noise = this._noiseBuf.length
      ? this._noiseBuf[this._noiseBuf.length - 1]
      : 0;
    const motion = this._motionBuf.length
      ? Math.min(1, this._motionBuf[this._motionBuf.length - 1] / 0.5)
      : 0;
    const snoring = this._snoreBuf.length ? !!this._snoreBuf[this._snoreBuf.length - 1] : false;
    return { noise, motion, snoring, minute: this._currentMinute() };
  }
}
