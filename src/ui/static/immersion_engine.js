/**
 * 5D Immersion Audio & Visual FX Engine for OpenHaptic-Roleplay
 * Provides:
 * - Procedural Dynamic Heartbeat (60 -> 140 BPM based on Overload)
 * - Tinnitus Ear-Ring & Screen Plasma Glitch upon High-Power Shock
 * - Fabric Tension & Tentacle Slime Spatial Audio FX
 * - Voice Input / Begging Listener using Web Speech API
 */

class ImmersionEngine {
    constructor() {
        this.audioCtx = null;
        this.heartbeatTimer = null;
        this.currentBpm = 60;
        this.isEarRinging = false;
        this.speechRecognizer = null;
        this.onVoiceRecognized = null;
    }

    initAudio() {
        if (!this.audioCtx) {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            this.startHeartbeatLoop();
            this.initSpeechRecognition();
        }
    }

    // 1. Procedural Dynamic Heartbeat Synthesizer
    startHeartbeatLoop() {
        const beat = () => {
            if (!this.audioCtx) return;
            const now = this.audioCtx.currentTime;

            // Sub-bass Thump (Double Pulse: lub-dub)
            this._playHeartThump(now, 55, 0.12);
            this._playHeartThump(now + 0.15, 45, 0.10);

            const intervalMs = (60.0 / this.currentBpm) * 1000;
            this.heartbeatTimer = setTimeout(beat, intervalMs);
        };
        beat();
    }

    _playHeartThump(startTime, freq, duration) {
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, startTime);
        osc.frequency.exponentialRampToValueAtTime(25, startTime + duration);

        gain.gain.setValueAtTime(0.6, startTime);
        gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);

        osc.connect(gain);
        gain.connect(this.audioCtx.destination);

        osc.start(startTime);
        osc.stop(startTime + duration);
    }

    setOverloadLevel(overloadPercent) {
        // Map Overload 0-100% to Heartbeat 60-140 BPM
        this.currentBpm = 60 + (overloadPercent / 100.0) * 80;
    }

    // 2. High-Power Shock FX (Ear-Ring + Screen Plasma Flash)
    triggerShockFX(powerPercent) {
        if (!this.audioCtx) return;
        const now = this.audioCtx.currentTime;

        // A. Electric Zap Noise Burst
        const bufferSize = this.audioCtx.sampleRate * 0.3;
        const buffer = this.audioCtx.createBuffer(1, bufferSize, this.audioCtx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.3));
        }
        const noise = this.audioCtx.createBufferSource();
        noise.buffer = buffer;

        const filter = this.audioCtx.createBiquadFilter();
        filter.type = "bandpass";
        filter.frequency.value = 1200;

        const zapGain = this.audioCtx.createGain();
        zapGain.gain.value = Math.min(1.0, powerPercent / 70.0);

        noise.connect(filter);
        filter.connect(zapGain);
        zapGain.connect(this.audioCtx.destination);
        noise.start(now);

        // B. Tinnitus Ear-Ring if power > 50%
        if (powerPercent > 50.0 && !this.isEarRinging) {
            this.isEarRinging = true;
            const osc = this.audioCtx.createOscillator();
            const ringGain = this.audioCtx.createGain();

            osc.type = 'sine';
            osc.frequency.value = 4200; // High pitch ring

            ringGain.gain.setValueAtTime(0.15, now);
            ringGain.gain.exponentialRampToValueAtTime(0.001, now + 2.5);

            osc.connect(ringGain);
            ringGain.connect(this.audioCtx.destination);

            osc.start(now);
            osc.stop(now + 2.5);
            setTimeout(() => { this.isEarRinging = false; }, 2500);
        }

        // C. Visual Plasma Glitch Trigger
        this._triggerVisualGlitch(powerPercent);
    }

    _triggerVisualGlitch(power) {
        const overlay = document.getElementById("immersionOverlay");
        if (overlay) {
            overlay.style.opacity = (power / 100.0).toFixed(2);
            overlay.style.boxShadow = `inset 0 0 80px rgba(180, 0, 255, ${power/80.0})`;
            setTimeout(() => {
                overlay.style.opacity = "0";
            }, 350);
        }
    }

    // 3. Speech Recognition / Begging Listener
    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

        this.speechRecognizer = new SpeechRecognition();
        this.speechRecognizer.continuous = true;
        this.speechRecognizer.interimResults = false;
        this.speechRecognizer.lang = "zh-CN";

        this.speechRecognizer.onresult = (event) => {
            const last = event.results.length - 1;
            const text = event.results[last][0].transcript.trim();
            console.log("[Voice In]", text);
            if (this.onVoiceRecognized) {
                this.onVoiceRecognized(text);
            }
        };

        this.speechRecognizer.onerror = (e) => {
            console.log("[Speech Error]", e);
        };

        try {
            this.speechRecognizer.start();
        } catch(e){}
    }
}

window.immersion = new ImmersionEngine();
