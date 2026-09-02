/**
 * Real-time Web Audio Decibel Meter & Strict Silent Trap Listener
 * Continuously measures player microphone volume and sends violations over WebSocket.
 */

class DecibelNoiseListener {
    constructor(thresholdDb = 45.0, onViolationCallback = null) {
        this.thresholdDb = thresholdDb;
        this.onViolationCallback = onViolationCallback;
        this.audioCtx = null;
        this.analyser = null;
        this.micStream = null;
        this.isRunning = false;
        this.currentDb = 0;
    }

    async start() {
        try {
            this.micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const source = this.audioCtx.createMediaStreamSource(this.micStream);
            this.analyser = this.audioCtx.createAnalyser();
            this.analyser.fftSize = 512;
            source.connect(this.analyser);

            this.isRunning = true;
            this._processAudio();
            console.log("[NoiseListener] Microphone decibel monitoring activated (Threshold:", this.thresholdDb, "dB)");
        } catch (e) {
            console.warn("[NoiseListener] Mic permission denied or unavailable:", e);
        }
    }

    _processAudio() {
        if (!this.isRunning) return;

        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        // Approximate dB mapping from 0-100
        this.currentDb = Math.min(100, Math.floor(average * 1.5));

        if (this.currentDb > this.thresholdDb && this.onViolationCallback) {
            this.onViolationCallback(this.currentDb);
        }

        requestAnimationFrame(() => this._processAudio());
    }

    stop() {
        this.isRunning = false;
        if (this.micStream) {
            this.micStream.getTracks().forEach(t => t.stop());
        }
    }
}

window.noiseListener = new DecibelNoiseListener();
