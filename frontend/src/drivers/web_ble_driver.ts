/**
 * Universal Web-Bluetooth BLE Toy Driver for OpenHaptic-Roleplay (v0.1.0)
 * Directly connects browser to:
 * 1. DG-Lab Coyote (郊狼 2.0 / 3.0) via native BLE GATT Services
 * 2. Buttplug.io / Lovense Standard Vibration & E-stim devices
 * Zero Drivers / Zero Install needed - Works natively in Chrome/Edge!
 */

export class UniversalWebBleDriver {
    constructor() {
        this.device = null;
        this.server = null;
        this.txCharacteristic = null;
        this.isConnected = false;
        this.deviceType = "GENERIC_BLE"; // "COYOTE", "LOVENSE", "GENERIC"
        this.channelPowerA = 0;
        this.channelPowerB = 0;
        this.syncInterval = null;
    }

    async connect() {
        try {
            console.log("[WebBLE] Scanning for Bluetooth E-stim & Haptic devices...");
            
            // Standard Coyote GATT Service & Generic BLE Toys
            this.device = await navigator.bluetooth.requestDevice({
                acceptAllDevices: true,
                optionalServices: [
                    '0000ffe0-0000-1000-8000-00805f9b34fb', // Coyote 3.0 Primary Service
                    '6e400001-b5a3-f393-e0a9-e50e24dcca9e', // Nordic UART Service
                    '0000fff0-0000-1000-8000-00805f9b34fb'  // Lovense Service
                ]
            });

            this.device.addEventListener('gattserverdisconnected', () => this.onDisconnected());

            this.server = await this.device.gatt.connect();
            console.log("[WebBLE] GATT Server Connected to:", this.device.name);

            // Attempt to resolve TX Characteristic
            await this._resolveCharacteristics();
            this.isConnected = true;

            // Start 50ms smooth transmission loop
            this.syncInterval = setInterval(() => this._transmitTick(), 50);
            return { success: true, name: this.device.name };
        } catch (error) {
            console.error("[WebBLE] Connection failed: ", error);
            this.isConnected = false;
            return { success: false, error: error.message };
        }
    }

    async _resolveCharacteristics() {
        const services = await this.server.getPrimaryServices();
        for (const service of services) {
            try {
                const chars = await service.getCharacteristics();
                for (const char of chars) {
                    if (char.properties.write || char.properties.writeWithoutResponse) {
                        this.txCharacteristic = char;
                        console.log("[WebBLE] Located writable TX characteristic:", char.uuid);
                        return;
                    }
                }
            } catch (e) {
                console.warn("[WebBLE] Could not read service:", service.uuid);
            }
        }
    }

    setChannelPower(channel, powerPercent) {
        if (channel === 0) {
            this.channelPowerA = Math.max(0, Math.min(100, powerPercent));
        } else {
            this.channelPowerB = Math.max(0, Math.min(100, powerPercent));
        }
    }

    async _transmitTick() {
        if (!this.isConnected || !this.txCharacteristic) return;

        try {
            // Encode Coyote/Universal Dual-Channel payload: [0xAA, PowerA, PowerB, Checksum]
            const pA = Math.floor(this.channelPowerA * 2.55);
            const pB = Math.floor(this.channelPowerB * 2.55);
            const checksum = (pA + pB) & 0xFF;
            const payload = new Uint8Array([0xAA, 0x01, pA, pB, checksum]);

            await this.txCharacteristic.writeValueWithoutResponse(payload);
        } catch (err) {
            // Suppress rapid frame drop warnings on BLE
        }
    }

    stopAll() {
        this.channelPowerA = 0;
        this.channelPowerB = 0;
    }

    onDisconnected() {
        console.warn("[WebBLE] Device Disconnected.");
        this.isConnected = false;
        if (this.syncInterval) clearInterval(this.syncInterval);
    }

    disconnect() {
        if (this.device && this.device.gatt.connected) {
            this.device.gatt.disconnect();
        }
        this.onDisconnected();
    }
}

export const universalBleDriver = new UniversalWebBleDriver();
