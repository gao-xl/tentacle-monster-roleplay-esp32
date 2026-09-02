/**
 * Web Bluetooth API (WebBLE) Driver for DG-Lab Coyote / Yokonex
 * Bypasses Python backend for direct, ultra-low latency browser-to-device control.
 * Integrated with offline wake-word failsafe.
 */

class WebBLEDriver {
    constructor() {
        this.device = null;
        this.server = null;
        this.characteristic = null;
        this.serviceUuid = "0000ffe0-0000-1000-8000-00805f9b34fb";
        this.charUuid = "0000ffe1-0000-1000-8000-00805f9b34fb";
        this.isConnected = false;
    }

    async connect() {
        try {
            console.log("[WebBLE] Requesting Bluetooth Device...");
            this.device = await navigator.bluetooth.requestDevice({
                filters: [{ namePrefix: "DGLAB" }, { namePrefix: "YOKONEX" }],
                optionalServices: [this.serviceUuid]
            });
            
            this.device.addEventListener('gattserverdisconnected', this.onDisconnected.bind(this));
            
            this.server = await this.device.gatt.connect();
            const service = await this.server.getPrimaryService(this.serviceUuid);
            this.characteristic = await service.getCharacteristic(this.charUuid);
            
            this.isConnected = true;
            console.log("[WebBLE] Successfully connected to Hardware!");
            return true;
        } catch (error) {
            console.error("[WebBLE] Connection failed: ", error);
            return false;
        }
    }

    onDisconnected() {
        console.log("[WebBLE] Device Disconnected.");
        this.isConnected = false;
    }

    async sendPulse(channel, powerLevel) {
        if (!this.isConnected || !this.characteristic) return;
        
        // Example DG-Lab Command: A/B + Intensity (0-200 mapped from 0-100%)
        const dglabLevel = Math.min(200, Math.floor(powerLevel * 2.0));
        const channelStr = channel === 0 ? "A" : "B";
        const cmd = new TextEncoder().encode(`${channelStr}${dglabLevel}\r\n`);
        
        try {
            await this.characteristic.writeValueWithoutResponse(cmd);
        } catch (e) {
            console.error("[WebBLE] Write failed", e);
        }
    }

    async emergencyStop() {
        if (!this.isConnected) return;
        console.warn("🚨 [WebBLE] EMERGENCY STOP TRIGGERED!");
        try {
            await this.characteristic.writeValueWithoutResponse(new TextEncoder().encode("A0\r\nB0\r\n"));
            if (this.device && this.device.gatt.connected) {
                this.device.gatt.disconnect();
            }
        } catch(e) {}
        this.isConnected = false;
    }
}

window.hwDriver = new WebBLEDriver();

// Local Offline Safety: Web Speech API Hook directly to WebBLE (No Network Required)
function initLocalFailsafe() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const safetyRec = new SpeechRecognition();
    safetyRec.continuous = true;
    safetyRec.lang = "zh-CN";
    
    safetyRec.onresult = (e) => {
        const txt = e.results[e.results.length - 1][0].transcript.trim();
        if (txt.includes("停止") || txt.includes("安全词") || txt.includes("pineapple")) {
            console.error("🚨 OFFLINE WAKE-WORD DETECTED! KILLING HARWARE.");
            window.hwDriver.emergencyStop();
            document.body.style.border = "10px solid red"; // Visual warning
        }
    };
    
    safetyRec.start();
}
window.addEventListener('load', initLocalFailsafe);
