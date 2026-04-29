// Optional ML snore detection using YAMNet (TensorFlow.js).
// Loads lazily on first use. Feeds 0.975s mono 16kHz audio frames and
// classifies them across 521 AudioSet classes; we sum the probabilities
// of the snoring-related class indices.
//
// Class index 38 is "Snoring" in the YAMNet class map. We also include
// 36 ("Snort"), 37 ("Snore"-related variants depending on map version),
// to be tolerant of different label files.

const MODEL_URL = 'https://tfhub.dev/google/tfjs-model/yamnet/tfjs/1/model.json?tfjs-format=file';
const TFJS_URL = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.20.0/dist/tf.min.js';
const TARGET_SR = 16000;
const FRAME_SAMPLES = 15600; // 0.975 s @ 16kHz
const SNORE_CLASSES = [36, 38];
const SNORE_THRESHOLD_DEFAULT = 0.35;

export class YamnetDetector {
  constructor({ threshold = SNORE_THRESHOLD_DEFAULT, onStatus = () => {} } = {}) {
    this.threshold = threshold;
    this.onStatus = onStatus;
    this.model = null;
    this.tf = null;
    this.buffer = new Float32Array(0);
    this._lastScore = 0;
  }

  setThreshold(v) { this.threshold = v; }

  async load() {
    if (this.model) return;
    this.onStatus('Cargando TensorFlow.js…');
    if (!window.tf) await injectScript(TFJS_URL);
    this.tf = window.tf;
    this.onStatus('Descargando modelo YAMNet (~4MB)…');
    this.model = await this.tf.loadGraphModel(MODEL_URL, { fromTFHub: true });
    this.onStatus('Modelo listo.');
  }

  /** Feed mono float32 audio @ TARGET_SR; runs inference when a frame is full. */
  async feed(audio) {
    if (!this.model) return null;
    const merged = new Float32Array(this.buffer.length + audio.length);
    merged.set(this.buffer, 0);
    merged.set(audio, this.buffer.length);
    if (merged.length < FRAME_SAMPLES) {
      this.buffer = merged;
      return null;
    }
    const frame = merged.subarray(0, FRAME_SAMPLES);
    this.buffer = merged.subarray(FRAME_SAMPLES);

    const tf = this.tf;
    const input = tf.tensor1d(frame);
    const out = this.model.predict(input);
    // YAMNet returns [scores, embeddings, spectrogram]. scores is [N,521].
    const scores = Array.isArray(out) ? out[0] : out;
    const arr = await scores.array();
    if (Array.isArray(out)) out.forEach(t => t.dispose && t.dispose());
    else scores.dispose && scores.dispose();
    input.dispose();

    // Mean across time, then sum snore-class probabilities.
    const mean = meanCols(arr);
    let snore = 0;
    for (const idx of SNORE_CLASSES) snore += mean[idx] || 0;
    this._lastScore = snore;
    return { snoring: snore >= this.threshold, score: snore };
  }

  lastScore() { return this._lastScore; }
}

function meanCols(matrix) {
  const rows = matrix.length;
  const cols = matrix[0].length;
  const out = new Array(cols).fill(0);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) out[c] += matrix[r][c];
  }
  for (let c = 0; c < cols; c++) out[c] /= rows;
  return out;
}

function injectScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('No se pudo cargar ' + src));
    document.head.appendChild(s);
  });
}
