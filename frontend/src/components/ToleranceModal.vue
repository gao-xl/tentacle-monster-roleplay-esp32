<template>
  <div v-if="isOpen" class="modal-backdrop">
    <div class="tolerance-card">
      <div class="card-header">
        <div class="title">⚡ 生理耐受极限校准 (PHASE 0: PRE-GAME ENDURANCE CALIBRATION)</div>
      </div>

      <div class="card-body">
        <div class="step-indicator">
          <div class="step" :class="{ active: currentStep === 1, done: currentStep > 1 }">
            1. 回路 A (传导器核心区) 校准
          </div>
          <div class="step" :class="{ active: currentStep === 2, done: currentStep > 2 }">
            2. 回路 B (双侧小腿足弓) 校准
          </div>
          <div class="step" :class="{ active: currentStep === 3 }">
            3. 校准报告与确认
          </div>
        </div>

        <!-- Testing Step 1 & 2 -->
        <div v-if="currentStep === 1 || currentStep === 2" class="test-view">
          <div class="channel-badge">
            当前测试回路: {{ currentStep === 1 ? '回路 A (Pads 1-2: 魔法传导器核心区)' : '回路 B (Pads 3-4: 双侧小腿与足弓)' }}
          </div>

          <div class="power-meter">
            <div class="meter-val">{{ currentPower }}%</div>
            <div class="meter-desc">{{ getFeelingDescription(currentPower) }}</div>
          </div>

          <div class="meter-bar-bg">
            <div class="meter-fill" :style="{ width: currentPower + '%' }"></div>
          </div>

          <div class="control-actions">
            <button class="btn-step" @click="stepUp(2)">+2% 微调增加</button>
            <button class="btn-step" @click="stepUp(5)">+5% 增加强度</button>
            <button class="btn-hold" @mousedown="startAutoRamp" @mouseup="stopAutoRamp" @mouseleave="stopAutoRamp">
              按住持续爬升
            </button>
          </div>

          <div class="warning-text">
            ⚠️ 提示：慢慢增加强度，当感到【这是我能承受的极限/再高就要受不了了】时，请立刻点击下方【设定为我的最大耐受极限】！
          </div>

          <button class="btn-confirm-limit" @click="confirmLimit">
            🛑 锁定该数值为我的最高耐受极限 (Tmax)
          </button>
        </div>

        <!-- Step 3: Complete Report -->
        <div v-if="currentStep === 3" class="summary-view">
          <div class="summary-grid">
            <div class="summary-card">
              <div class="s-title">回路 A (核心区) 极限</div>
              <div class="s-val">{{ resultTmaxA }}%</div>
              <div class="s-desc">禁断边缘爬升上限: {{ Math.round(resultTmaxA * 0.92) }}%</div>
              <div class="s-desc">破防惩罚打击: {{ Math.round(resultTmaxA * 0.88) }}%</div>
            </div>
            <div class="summary-card">
              <div class="s-title">回路 B (小腿足弓) 极限</div>
              <div class="s-val">{{ resultTmaxB }}%</div>
              <div class="s-desc">禁断边缘爬升上限: {{ Math.round(resultTmaxB * 0.92) }}%</div>
              <div class="s-desc">破防惩罚打击: {{ Math.round(resultTmaxB * 0.88) }}%</div>
            </div>
          </div>

          <div class="report-desc">
            🎉 生理耐受极限校准完成！所有后续游戏中的【破防电击】、【红绿灯惩罚】与【禁止高潮边缘】将严格以此基准自适应缩放，绝不会超过你的生理极限。
          </div>

          <button class="btn-enter-game" @click="finishCalibration">
            🎮 进入游戏 (ENTER ROLEPLAY)
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits(['completed'])

const currentStep = ref(1)
const currentPower = ref(10)
const resultTmaxA = ref(60)
const resultTmaxB = ref(70)
let rampInterval: any = null

function getFeelingDescription(p: number) {
  if (p < 20) return '轻微酥麻微弱感 (Perceptible Tingling)'
  if (p < 40) return '明显收缩与轻抚波 (Teasing Muscle Contraction)'
  if (p < 60) return '强烈收缩与穿透电浆 (Strong Punchy Sensation)'
  if (p < 80) return '极限濒临破防区 (Near Pain Threshold)'
  return '超高压极限承载区 (Maximum Tolerable Overload)'
}

function sendPower(p: number) {
  const ch = currentStep.value === 1 ? 0 : 1
  fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'set', channel: ch, power: p, decay_ms: 0 })
  })
}

function stepUp(step: number) {
  currentPower.value = Math.min(90, currentPower.value + step)
  sendPower(currentPower.value)
}

function startAutoRamp() {
  rampInterval = setInterval(() => {
    if (currentPower.value < 90) {
      currentPower.value += 1
      sendPower(currentPower.value)
    }
  }, 120)
}

function stopAutoRamp() {
  if (rampInterval) clearInterval(rampInterval)
}

function confirmLimit() {
  stopAutoRamp()
  // Cut off current channel
  const ch = currentStep.value === 1 ? 0 : 1
  fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'stop', channel: ch, power: 0, decay_ms: 0 })
  })

  if (currentStep.value === 1) {
    resultTmaxA.value = currentPower.value
    currentStep.value = 2
    currentPower.value = 10
  } else if (currentStep.value === 2) {
    resultTmaxB.value = currentPower.value
    currentStep.value = 3
  }
}

function finishCalibration() {
  // Post calibration limits to backend settings
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      safety_power_ceiling: Math.max(resultTmaxA.value, resultTmaxB.value),
      calibrated_tmax_a: resultTmaxA.value,
      calibrated_tmax_b: resultTmaxB.value
    })
  })
  emit('completed', { tmaxA: resultTmaxA.value, tmaxB: resultTmaxB.value })
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(0, 0, 0, 0.88); backdrop-filter: blur(10px);
  display: flex; justify-content: center; align-items: center; z-index: 10000;
}
.tolerance-card {
  background: rgba(12, 17, 28, 0.98); border: 2px solid #00f0ff;
  box-shadow: 0 0 50px rgba(0, 240, 255, 0.4); border-radius: 10px;
  width: 720px; max-width: 95vw; color: #e0f4ff; font-family: 'Rajdhani', sans-serif;
}
.card-header { padding: 16px 24px; border-bottom: 1px solid rgba(0, 240, 255, 0.3); }
.title { font-size: 16px; font-weight: 900; color: #00f0ff; letter-spacing: 1px; font-family: 'Orbitron'; }
.card-body { padding: 24px; display: flex; flex-direction: column; gap: 20px; }

.step-indicator { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.step { background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 4px; font-size: 12px; text-align: center; color: #8faec9; }
.step.active { background: rgba(0,240,255,0.2); color: #00f0ff; border: 1px solid #00f0ff; font-weight: bold; }
.step.done { color: #00ff88; border-color: #00ff88; }

.channel-badge { background: rgba(176,0,255,0.2); border: 1px solid #b000ff; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; }
.power-meter { text-align: center; margin: 10px 0; }
.meter-val { font-size: 54px; font-weight: 900; font-family: 'Orbitron'; color: #00f0ff; text-shadow: 0 0 20px rgba(0,240,255,0.6); }
.meter-desc { font-size: 13px; color: #ffcc00; margin-top: 4px; }
.meter-bar-bg { height: 12px; background: rgba(255,255,255,0.1); border-radius: 6px; overflow: hidden; margin-bottom: 15px; }
.meter-fill { height: 100%; background: linear-gradient(90deg, #00f0ff, #ff0055); transition: width 0.15s ease; }

.control-actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.btn-step, .btn-hold { background: rgba(0,240,255,0.15); border: 1px solid #00f0ff; color: #00f0ff; padding: 12px; border-radius: 6px; font-weight: bold; cursor: pointer; }
.btn-step:hover, .btn-hold:hover { background: #00f0ff; color: #000; box-shadow: 0 0 15px #00f0ff; }

.warning-text { font-size: 12px; color: #a0c0d8; line-height: 1.5; background: rgba(0,0,0,0.4); padding: 12px; border-radius: 6px; border-left: 3px solid #ffcc00; }
.btn-confirm-limit { background: linear-gradient(135deg, #ff0055, #b000ff); border: none; color: #fff; padding: 14px; border-radius: 6px; font-weight: 900; font-size: 15px; cursor: pointer; box-shadow: 0 0 25px rgba(255,0,85,0.5); }

.summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.summary-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(0,240,255,0.3); padding: 16px; border-radius: 8px; text-align: center; }
.s-title { font-size: 13px; color: #8faec9; margin-bottom: 6px; }
.s-val { font-size: 36px; font-weight: bold; font-family: 'Orbitron'; color: #00ff88; margin-bottom: 10px; }
.s-desc { font-size: 12px; color: #a0c0d8; margin-top: 4px; }
.report-desc { font-size: 13px; color: #00f0ff; line-height: 1.5; background: rgba(0,240,255,0.08); padding: 14px; border-radius: 6px; }
.btn-enter-game { background: #00ff88; border: none; color: #000; padding: 14px; border-radius: 6px; font-weight: 900; font-size: 16px; cursor: pointer; box-shadow: 0 0 25px rgba(0,255,136,0.6); }
</style>
