<template>
  <div class="haptic-app" :class="{ 'glitch-active': isGlitching }">
    <!-- Top Navigation Header -->
    <header class="app-header">
      <div class="logo">
        <span class="pulse-icon">⚡</span>
        <span class="title">OPENHAPTIC // v0.1.0 HUD</span>
      </div>
      <div class="header-status">
        <span class="badge" :class="isConnected ? 'badge-online' : 'badge-offline'">
          {{ isConnected ? 'BACKEND CONNECTED' : 'DISCONNECTED' }}
        </span>
        <button class="btn-settings" @click="isSettingsOpen = true">⚙️ 全局设置</button>
        <button class="btn-emergency" @click="sendEmergencyStop">🛑 EMERGENCY STOP (SPACE)</button>
      </div>
    </header>

    <!-- Main Grid Workspace -->
    <main class="dashboard-grid">
      <!-- Left Column: Video & Telemetry Gauges -->
      <section class="panel video-panel">
        <div class="panel-header">
          <span>👁️ SKELETAL VIDEO STREAM (YOLO-POSE 26)</span>
          <span class="fps-tag">60 FPS // ONE-EURO FILTER</span>
        </div>
        <div class="video-wrapper">
          <img :src="videoUrl" alt="Video Stream" class="stream-img" />
          <div class="overlay-target" v-if="telemetry.player?.hands_core">
            <span class="lock-tag">POINT 19 // CORE LOCKED [!]</span>
          </div>
        </div>

        <!-- Biometric Gauges -->
        <div class="gauges-container">
          <div class="gauge-row">
            <div class="label-group">
              <span>战衣护甲耐久 (Armor HP)</span>
              <span class="val">{{ Math.round(telemetry.stats?.armor_hp ?? 100) }}%</span>
            </div>
            <div class="bar-bg">
              <div class="bar-fill armor" :style="{ width: (telemetry.stats?.armor_hp ?? 100) + '%' }"></div>
            </div>
          </div>

          <div class="gauge-row">
            <div class="label-group">
              <span>传导器魔力过载 (Magic Overload)</span>
              <span class="val">{{ Math.round(telemetry.stats?.magic_overload ?? 0) }}%</span>
            </div>
            <div class="bar-bg">
              <div class="bar-fill overload" :style="{ width: (telemetry.stats?.magic_overload ?? 0) + '%' }"></div>
            </div>
          </div>
        </div>
      </section>

      <!-- Right Column: Dual-Loop Waveforms & Story Dialogue -->
      <section class="panel control-panel">
        <div class="panel-header">
          <span>⚡ 4-PAD DUAL-LOOP HAPTIC OUTPUT</span>
          <span class="mode-tag">{{ telemetry.stats?.stage_title || 'STORY ACTIVE' }}</span>
        </div>

        <!-- Dual Channel Gauges -->
        <div class="dual-channel-box">
          <div class="channel-card">
            <div class="ch-title">LOOP A (Pads 1-2: Core)</div>
            <div class="ch-power">{{ Math.round(telemetry.device?.powers?.[0] ?? 0) }}%</div>
            <div class="bar-bg">
              <div class="bar-fill ch-a" :style="{ width: (telemetry.device?.powers?.[0] ?? 0) + '%' }"></div>
            </div>
          </div>
          <div class="channel-card">
            <div class="ch-title">LOOP B (Pads 3-4: Legs)</div>
            <div class="ch-power">{{ Math.round(telemetry.device?.powers?.[1] ?? 0) }}%</div>
            <div class="bar-bg">
              <div class="bar-fill ch-b" :style="{ width: (telemetry.device?.powers?.[1] ?? 0) + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- AI Dialogue Log with Preemptive Voice Indicators -->
        <div class="panel-header" style="margin-top: 15px;">
          <span>🧠 KOKORO AI NARRATIVE (PREEMPTIVE TTS)</span>
        </div>
        <div class="dialogue-box" ref="dialogueBox">
          <div v-for="(msg, idx) in dialogues" :key="idx" class="dialogue-item">
            <div class="time">{{ msg.time }}</div>
            <div class="text">{{ msg.text }}</div>
          </div>
        </div>

        <!-- Action Command Buttons -->
        <div class="actions-grid">
          <button class="btn-action" @click="sendAction('flow', 50)">🌊 上升流动波</button>
          <button class="btn-action" @click="sendAction('hit', 65)">💥 破防重击</button>
          <button class="btn-action" @click="sendAction('dual', 40)">⚡ 双路全开</button>
        </div>
      </section>
    </main>

    <!-- Global Settings Modal -->
    <SettingsModal :isOpen="isSettingsOpen" @close="isSettingsOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import SettingsModal from './components/SettingsModal.vue'

const isConnected = ref(false)
const isGlitching = ref(false)
const isSettingsOpen = ref(false)
const videoUrl = ref('/video_feed')
const telemetry = ref<any>({})
const dialogues = ref<{ time: string; text: string }[]>([
  { time: 'SYSTEM', text: 'OpenHaptic Frontend v0.1.0 Vue3 HUD initialized.' }
])

let ws: WebSocket | null = null

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${location.host}/ws`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    isConnected.value = true
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'telemetry') {
        telemetry.value = data
        if (data.dialogues) {
          dialogues.value = data.dialogues
        }
        // Glitch on high power strike
        if ((data.device?.powers?.[0] > 55) || (data.device?.powers?.[1] > 55)) {
          triggerGlitch()
        }
      }
    } catch (e) {}
  }

  ws.onclose = () => {
    isConnected.value = false
    setTimeout(connectWebSocket, 1500)
  }
}

function triggerGlitch() {
  isGlitching.value = true
  setTimeout(() => { isGlitching.value = false }, 300)
}

function sendAction(action: string, power: number) {
  fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, channel: 0, power, decay_ms: 400 })
  })
}

function sendEmergencyStop() {
  sendAction('stop', 0)
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.code === 'Space') {
    e.preventDefault()
    sendEmergencyStop()
  }
}

onMounted(() => {
  connectWebSocket()
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  if (ws) ws.close()
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.haptic-app {
  min-height: 100vh;
  background-color: #06080e;
  color: #e0f4ff;
  font-family: 'Rajdhani', sans-serif;
  display: flex;
  flex-direction: column;
}

.glitch-active {
  box-shadow: inset 0 0 100px rgba(255, 0, 85, 0.6);
  filter: contrast(120%) saturate(150%);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: rgba(10, 14, 24, 0.95);
  border-bottom: 2px solid #b000ff;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 900;
  font-size: 18px;
  color: #00f0ff;
  letter-spacing: 2px;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 16px;
}

.badge {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
}
.badge-online { border: 1px solid #00ff88; color: #00ff88; }
.badge-offline { border: 1px solid #ff0055; color: #ff0055; }

.btn-settings {
  background: rgba(0, 240, 255, 0.12);
  border: 1px solid #00f0ff;
  color: #00f0ff;
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-settings:hover {
  background: #00f0ff;
  color: #000;
  box-shadow: 0 0 15px #00f0ff;
}

.btn-emergency {
  background: rgba(255, 0, 85, 0.2);
  border: 1px solid #ff0055;
  color: #ff0055;
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 20px;
  padding: 20px;
  max-width: 1700px;
  margin: 0 auto;
  width: 100%;
}

.panel {
  background: rgba(12, 17, 28, 0.88);
  border: 1px solid rgba(0, 240, 255, 0.25);
  border-radius: 8px;
  padding: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  color: #00f0ff;
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 12px;
}

.video-wrapper {
  position: relative;
  border-radius: 6px;
  overflow: hidden;
  background: #000;
}
.stream-img { width: 100%; display: block; }

.overlay-target {
  position: absolute;
  top: 15px; right: 15px;
  background: rgba(255, 0, 85, 0.8);
  color: #fff;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 4px;
  font-weight: bold;
}

.gauges-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 15px;
}
.label-group { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }
.bar-bg { height: 10px; background: rgba(255, 255, 255, 0.1); border-radius: 5px; overflow: hidden; }
.bar-fill { height: 100%; transition: width 0.2s ease; }
.bar-fill.armor { background: #00f0ff; }
.bar-fill.overload { background: #ff0055; }

.dual-channel-box {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.channel-card {
  background: rgba(255, 255, 255, 0.03);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.ch-title { font-size: 12px; color: #8faec9; }
.ch-power { font-size: 22px; font-weight: bold; margin: 4px 0; font-family: 'Orbitron'; }
.ch-a { background: #00f0ff; }
.ch-b { background: #b000ff; }

.dialogue-box {
  height: 200px;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.3);
  padding: 10px;
  border-radius: 6px;
  border: 1px solid rgba(176, 0, 255, 0.2);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dialogue-item {
  background: rgba(176, 0, 255, 0.1);
  padding: 8px;
  border-radius: 4px;
  border-left: 3px solid #b000ff;
  font-size: 13px;
}
.dialogue-item .time { font-size: 10px; color: #b080ff; }

.actions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 15px;
}
.btn-action {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid #00f0ff;
  color: #00f0ff;
  padding: 10px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
}
.btn-action:hover {
  background: #00f0ff;
  color: #000;
}
</style>