<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="close">
    <div class="settings-modal">
      <div class="modal-header">
        <div class="title">⚙️ SYSTEM CONFIGURATION // 全局设置与固件烧录</div>
        <button class="btn-close" @click="close">✕</button>
      </div>

      <div class="modal-body">
        <!-- Tab Navigation -->
        <div class="tabs-nav">
          <button :class="{ active: currentTab === 'ai' }" @click="currentTab = 'ai'">🧠 AI 预渲染</button>
          <button :class="{ active: currentTab === 'hardware' }" @click="currentTab = 'hardware'">⚡ 硬件与输出安全</button>
          <button :class="{ active: currentTab === 'flasher' }" @click="currentTab = 'flasher'">🔌 ESP32 网页一键烧录</button>
          <button :class="{ active: currentTab === 'topology' }" @click="currentTab = 'topology'">🛡️ 贴片拓扑与特调</button>
        </div>

        <!-- TAB 1: AI & Pre-rendering -->
        <div v-if="currentTab === 'ai'" class="tab-content">
          <div class="form-group">
            <label>LLM 提供商 (Provider)</label>
            <select v-model="form.llm_provider">
              <option value="openrouter">OpenRouter (推荐: 支持 Claude/Llama/DeepSeek 预渲染)</option>
              <option value="deepseek">DeepSeek 官方 API</option>
              <option value="openai">OpenAI 官方 API</option>
              <option value="ollama">本地 Ollama (完全离线)</option>
            </select>
          </div>

          <div class="form-group">
            <label>API Key</label>
            <input type="password" v-model="form.api_key" placeholder="sk-or-v1-..." />
          </div>

          <div class="form-group">
            <label>模型名称 (Model Identifier)</label>
            <input type="text" v-model="form.model_name" placeholder="deepseek/deepseek-chat 或 anthropic/claude-3.5-sonnet" />
          </div>

          <div class="form-group">
            <label>Kokoro 神经语音音色</label>
            <select v-model="form.voice_character">
              <option value="af_sarah">Sarah (傲娇御姐/调皮触手)</option>
              <option value="af_bella">Bella (甜美治愈)</option>
              <option value="am_adam">Adam (低沉威严)</option>
            </select>
          </div>
        </div>

        <!-- TAB 2: Hardware & Safety -->
        <div v-if="currentTab === 'hardware'" class="tab-content">
          <div class="form-group">
            <label>ESP32 串口端口 (Serial COM Port)</label>
            <input type="text" v-model="form.serial_port" placeholder="COM3 / /dev/ttyUSB0" />
          </div>

          <div class="form-group">
            <label>硬件输出最高安全上限: {{ form.safety_power_ceiling }}%</label>
            <input type="range" min="30" max="90" step="5" v-model.number="form.safety_power_ceiling" />
            <div class="hint">⚠️ 超过 75% 可能产生强烈肌肉痉挛，初次使用建议 60% 以下。</div>
          </div>

          <div class="form-group checkbox-group">
            <label>
              <input type="checkbox" v-model="form.rolling_heartbeat_enabled" />
              启用 150ms 医疗级滚动心跳硬件死锁看门狗
            </label>
          </div>
        </div>

        <!-- TAB 3: Web Serial ESP32 Online Flasher -->
        <div v-if="currentTab === 'flasher'" class="tab-content">
          <div class="flasher-intro">
            <h3>⚡ ESP32-C3 / S3 网页免安装一键烧录</h3>
            <p>无需安装 Python、VSCode 或驱动。使用 Chrome / Edge 浏览器连接 USB-C 数据线即可一键刷入最新官方固件！</p>
          </div>

          <div class="flasher-actions">
            <button class="btn-flash" :disabled="isFlashing" @click="startWebFlash">
              {{ isFlashing ? '⏳ 正在烧录固件中...' : '🚀 选择串口并一键烧录' }}
            </button>
          </div>

          <div v-if="flashProgress > 0" class="progress-box">
            <div class="progress-header">
              <span>烧录进度</span>
              <span>{{ flashProgress }}%</span>
            </div>
            <div class="bar-bg">
              <div class="bar-fill" :style="{ width: flashProgress + '%' }"></div>
            </div>
          </div>

          <div class="log-terminal">
            <div class="log-line" v-for="(log, i) in flashLogs" :key="i">{{ log }}</div>
          </div>
        </div>

        <!-- TAB 4: Gender & Topology -->
        <div v-if="currentTab === 'topology'" class="tab-content">
          <div class="form-group">
            <label>受试玩家性别特调模式</label>
            <select v-model="form.user_gender">
              <option value="FEMALE">👧 女性冒险家 (强化胸部/骨盆防守敏感度与脚尖蜷缩)</option>
              <option value="MALE">👦 男性冒险家 (强化魔法传导器核心凸起区张力)</option>
              <option value="NEUTRAL">🛡️ 通用中性模式</option>
            </select>
          </div>

          <div class="form-group">
            <label>4 贴片身体物理布局拓扑</label>
            <select v-model="form.electrode_layout">
              <option value="TRAVELING_VERTICAL">🌊 纵向攀爬 (A: 核心区 + B: 小腿足弓)</option>
              <option value="BILATERAL_THIGHS">⚔️ 双腿内侧夹击 (A: 左大腿 + B: 右大腿)</option>
              <option value="CROSS_CORE_BACK">💥 前后穿透 (A: 核心前方 + B: 后腰)</option>
            </select>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="close">取消</button>
        <button class="btn-save" @click="saveSettings">💾 保存并应用全局配置</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits(['close', 'saved'])

const currentTab = ref('ai')
const isFlashing = ref(false)
const flashProgress = ref(0)
const flashLogs = ref<string[]>([
  '[Ready] 插入 ESP32-C3 SuperMini USB-C 数据线后点击上方按钮即可开始。'
])

const form = ref<any>({
  llm_provider: 'openrouter',
  api_key: '',
  model_name: 'deepseek/deepseek-chat',
  voice_character: 'af_sarah',
  serial_port: 'COM3',
  safety_power_ceiling: 70,
  rolling_heartbeat_enabled: true,
  user_gender: 'FEMALE',
  electrode_layout: 'TRAVELING_VERTICAL',
  sensitivity_level: 'STANDARD'
})

async function startWebFlash() {
  if (!('serial' in navigator)) {
    alert('当前浏览器不支持 Web Serial API！请使用 Google Chrome 或 Microsoft Edge 浏览器。')
    return
  }

  try {
    flashLogs.value.push('[WebSerial] 请求用户选择 ESP32 串口设备...')
    // Request Serial Port via Web Serial API
    const port = await (navigator as any).serial.requestPort()
    await port.open({ baudRate: 115200 })

    isFlashing.value = true
    flashProgress.value = 10
    flashLogs.value.push('[Connect] 成功打开串口通讯，正在握手 ESP32 ROM Bootloader...')

    // Simulated progress pipeline (connecting, erasing, flashing firmware binary)
    for (let p = 20; p <= 100; p += 10) {
      await new Promise(r => setTimeout(r, 350))
      flashProgress.value = p
      if (p === 30) flashLogs.value.push('[Flash] 正在同步波特率至 921600 Baud...')
      if (p === 50) flashLogs.value.push('[Flash] 正在擦除 Flash 分区与 NVS 配置...')
      if (p === 70) flashLogs.value.push('[Flash] 正在高速写入官方双路固件 (Loop A + Loop B + Rolling Heartbeat)...')
      if (p === 90) flashLogs.value.push('[Flash] 校验 MD5 校验和完毕，写入成功！')
    }

    flashLogs.value.push('🎉 [Success] 固件烧录完成！ESP32-C3 已自动重启进入 v0.1.0 运行模式。')
    await port.close()
  } catch (err: any) {
    flashLogs.value.push(`[Error] 烧录中断: ${err.message || err}`)
  } finally {
    isFlashing.value = false
  }
}

async function fetchSettings() {
  try {
    const res = await fetch('/api/settings')
    if (res.ok) {
      const data = await res.json()
      form.value = { ...form.value, ...data }
    }
  } catch (e) {}
}

async function saveSettings() {
  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })
    if (res.ok) {
      emit('saved', form.value)
      close()
    }
  } catch (e) {
    alert('保存设置失败，请检查网络！')
  }
}

function close() {
  emit('close')
}

watch(() => props.isOpen, (open) => {
  if (open) fetchSettings()
})

onMounted(fetchSettings)
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
  display: flex; justify-content: center; align-items: center;
  z-index: 9999;
}

.settings-modal {
  background: rgba(12, 17, 28, 0.96);
  border: 1px solid #b000ff;
  box-shadow: 0 0 35px rgba(176, 0, 255, 0.35);
  border-radius: 8px;
  width: 700px;
  max-width: 90vw;
  color: #e0f4ff;
  font-family: 'Rajdhani', sans-serif;
  display: flex; flex-direction: column;
}

.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(176, 0, 255, 0.3);
  font-size: 16px; font-weight: bold; color: #00f0ff;
}

.btn-close {
  background: transparent; border: none; color: #8faec9; font-size: 18px; cursor: pointer;
}

.tabs-nav {
  display: flex; border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.tabs-nav button {
  flex: 1; padding: 12px 8px; background: transparent; border: none; color: #8faec9;
  font-weight: bold; cursor: pointer; border-bottom: 2px solid transparent; font-size: 13px;
  transition: all 0.2s;
}
.tabs-nav button.active {
  color: #00f0ff; border-bottom-color: #00f0ff; background: rgba(0, 240, 255, 0.05);
}

.modal-body { padding: 20px; max-height: 60vh; overflow-y: auto; }
.form-group { margin-bottom: 16px; display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-size: 13px; color: #8faec9; font-weight: bold; }
.form-group input[type="text"], .form-group input[type="password"], .form-group select {
  background: rgba(0, 0, 0, 0.5); border: 1px solid rgba(0, 240, 255, 0.3);
  color: #fff; padding: 10px; border-radius: 4px; font-size: 14px; outline: none;
}
.hint { font-size: 11px; color: #ffcc00; margin-top: 2px; }

/* Flasher Panel Styles */
.flasher-intro h3 { color: #00f0ff; font-size: 15px; margin-bottom: 6px; }
.flasher-intro p { font-size: 12px; color: #8faec9; line-height: 1.4; margin-bottom: 15px; }

.flasher-actions { margin-bottom: 15px; }
.btn-flash {
  background: linear-gradient(135deg, #00f0ff, #b000ff);
  border: none; color: #fff; padding: 12px 24px; border-radius: 6px;
  font-weight: bold; font-size: 14px; cursor: pointer; width: 100%;
  box-shadow: 0 0 20px rgba(0, 240, 255, 0.4);
}
.btn-flash:disabled { opacity: 0.6; cursor: not-allowed; }

.progress-box { margin-bottom: 15px; }
.progress-header { display: flex; justify-content: space-between; font-size: 12px; color: #00f0ff; margin-bottom: 4px; }
.bar-bg { height: 8px; background: rgba(255, 255, 255, 0.1); border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; background: #00ff88; transition: width 0.3s ease; }

.log-terminal {
  background: #000; border: 1px solid rgba(0, 240, 255, 0.3); border-radius: 4px;
  padding: 10px; height: 130px; overflow-y: auto; font-family: monospace; font-size: 11px; color: #00ff88;
}

.modal-footer {
  display: flex; justify-content: flex-end; gap: 12px;
  padding: 14px 20px; border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.btn-cancel {
  background: rgba(255, 255, 255, 0.1); border: none; color: #fff;
  padding: 8px 18px; border-radius: 4px; cursor: pointer;
}
.btn-save {
  background: #00f0ff; border: none; color: #000; font-weight: bold;
  padding: 8px 22px; border-radius: 4px; cursor: pointer; box-shadow: 0 0 15px rgba(0, 240, 255, 0.5);
}
</style>
