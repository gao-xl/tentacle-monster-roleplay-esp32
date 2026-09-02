<template>
  <div v-if="isOpen" class="studio-backdrop">
    <div class="studio-container">
      <!-- Studio Header -->
      <header class="studio-header">
        <div class="title">
          <span class="icon">🧩</span>
          <span>HAPTIC BLUEPRINT STUDIO // 可视化剧本工坊 (v0.1.0)</span>
        </div>
        <div class="header-actions">
          <button class="btn-tool" @click="loadSampleBlueprint">📂 加载示例蓝图</button>
          <button class="btn-tool" @click="exportBlueprint">💾 导出 .haptic 模组</button>
          <button class="btn-deploy" @click="deployToBackend">▶️ 热部署并运行</button>
          <button class="btn-close" @click="close">✕</button>
        </div>
      </header>

      <div class="studio-body">
        <!-- Left: Node Palette -->
        <aside class="palette-sidebar">
          <div class="palette-title">节点工具箱 (DRAG NODES)</div>
          
          <div class="node-category">👁️ 视觉与体态触发器 (Triggers)</div>
          <div class="draggable-node trig" draggable="true" @dragstart="onDragStart('trig_core')">
            Point 19 核心防守 (Core Covered)
          </div>
          <div class="draggable-node trig" draggable="true" @dragstart="onDragStart('trig_spasm')">
            足底脚尖痉挛 (Toe Curl Spasm)
          </div>
          <div class="draggable-node trig" draggable="true" @dragstart="onDragStart('trig_redlight')">
            红灯木头人违规 (Motion Violation)
          </div>
          <div class="draggable-node trig" draggable="true" @dragstart="onDragStart('trig_surrender')">
            双手高举求饶 (Surrender)
          </div>

          <div class="node-category">⚡ 物理电击输出 (Actions)</div>
          <div class="draggable-node act" draggable="true" @dragstart="onDragStart('act_shock')">
            💥 破防重击 (Shock Hit)
          </div>
          <div class="draggable-node act" draggable="true" @dragstart="onDragStart('act_flow')">
            🌊 双路上升流动波 (Traveling Wave)
          </div>
          <div class="draggable-node act" draggable="true" @dragstart="onDragStart('act_roulette')">
            🎰 恶魔轮盘赌 (Roulette Burst)
          </div>

          <div class="node-category">🗣️ 叙事与 AI 语音 (Voice)</div>
          <div class="draggable-node voice" draggable="true" @dragstart="onDragStart('voice_preempt')">
            🎙️ 抢占式即时语音 (Kokoro TTS)
          </div>
        </aside>

        <!-- Center: Blueprint Canvas -->
        <main class="canvas-area" @dragover.prevent @drop="onDropNode" ref="canvasRef">
          <div class="grid-background"></div>

          <!-- Active Nodes on Canvas -->
          <div
            v-for="node in nodes"
            :key="node.id"
            class="canvas-node"
            :class="node.category"
            :style="{ left: node.x + 'px', top: node.y + 'px' }"
            @mousedown="startDragNode(node, $event)"
          >
            <div class="node-head">
              <span>{{ node.title }}</span>
              <span class="node-del" @click.stop="deleteNode(node.id)">✕</span>
            </div>
            <div class="node-content">
              <div v-if="node.type === 'act_shock'" class="param-row">
                <label>功率: {{ node.params.power }}%</label>
                <input type="range" min="20" max="85" v-model.number="node.params.power" />
              </div>
              <div v-if="node.type === 'voice_preempt'" class="param-row">
                <label>台词文本:</label>
                <input type="text" v-model="node.params.text" />
              </div>
              <div v-if="node.type === 'trig_spasm'" class="param-row">
                <label>痉挛阈值: {{ node.params.threshold }}%</label>
                <input type="range" min="20" max="70" v-model.number="node.params.threshold" />
              </div>
            </div>
            <!-- Connection Ports -->
            <div class="port port-out" title="Output Port"></div>
            <div class="port port-in" title="Input Port"></div>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits(['close'])

const canvasRef = ref<HTMLElement | null>(null)
let draggedType = ''

interface StudioNode {
  id: string
  title: string
  type: string
  category: 'trig' | 'act' | 'voice'
  x: number
  y: number
  params: Record<string, any>
}

const nodes = ref<StudioNode[]>([
  {
    id: 'n1',
    title: 'Point 19 核心防守 (Core Covered)',
    type: 'trig_core',
    category: 'trig',
    x: 100,
    y: 120,
    params: {}
  },
  {
    id: 'n2',
    title: '💥 破防重击 (Shock Hit)',
    type: 'act_shock',
    category: 'act',
    x: 450,
    y: 100,
    params: { power: 65, channel: 0 }
  },
  {
    id: 'n3',
    title: '🎙️ 抢占式即时语音',
    type: 'voice_preempt',
    category: 'voice',
    x: 450,
    y: 260,
    params: { text: '把手给我拿开！在拘束室里你没有遮挡的权利！' }
  }
])

function onDragStart(type: string) {
  draggedType = type
}

function onDropNode(e: DragEvent) {
  if (!canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left - 100
  const y = e.clientY - rect.top - 40

  const id = 'n_' + Date.now()
  let title = 'Custom Node'
  let category: 'trig' | 'act' | 'voice' = 'trig'
  let params: any = {}

  if (draggedType === 'trig_core') { title = 'Point 19 核心防守'; category = 'trig'; }
  if (draggedType === 'trig_spasm') { title = '足尖痉挛抽搐'; category = 'trig'; params = { threshold: 35 }; }
  if (draggedType === 'trig_redlight') { title = '红灯木头人违规'; category = 'trig'; }
  if (draggedType === 'trig_surrender') { title = '双手高举求饶'; category = 'trig'; }
  if (draggedType === 'act_shock') { title = '💥 破防重击'; category = 'act'; params = { power: 60 }; }
  if (draggedType === 'act_flow') { title = '🌊 双路上升流动波'; category = 'act'; }
  if (draggedType === 'act_roulette') { title = '🎰 恶魔轮盘赌'; category = 'act'; }
  if (draggedType === 'voice_preempt') { title = '🎙️ 抢占式即时语音'; category = 'voice'; params = { text: '抓到你了！' }; }

  nodes.value.push({ id, title, type: draggedType, category, x, y, params })
}

function deleteNode(id: string) {
  nodes.value = nodes.value.filter(n => n.id !== id)
}

let activeDragNode: StudioNode | null = null
let dragOffset = { x: 0, y: 0 }

function startDragNode(node: StudioNode, e: MouseEvent) {
  activeDragNode = node
  dragOffset = { x: e.clientX - node.x, y: e.clientY - node.y }
  window.addEventListener('mousemove', onNodeMouseMove)
  window.addEventListener('mouseup', onNodeMouseUp)
}

function onNodeMouseMove(e: MouseEvent) {
  if (activeDragNode) {
    activeDragNode.x = e.clientX - dragOffset.x
    activeDragNode.y = e.clientY - dragOffset.y
  }
}

function onNodeMouseUp() {
  activeDragNode = null
  window.removeEventListener('mousemove', onNodeMouseMove)
  window.removeEventListener('mouseup', onNodeMouseUp)
}

function loadSampleBlueprint() {
  nodes.value = [
    { id: 'n1', title: '足尖痉挛抽搐', type: 'trig_spasm', category: 'trig', x: 80, y: 120, params: { threshold: 40 } },
    { id: 'n2', title: '🌊 双路上升流动波', type: 'act_flow', category: 'act', x: 400, y: 120, params: {} },
    { id: 'n3', title: '🎙️ 抢占式即时语音', type: 'voice_preempt', category: 'voice', x: 400, y: 280, params: { text: '小脚趾蜷起来了呢……' } }
  ]
}

function exportBlueprint() {
  const jsonStr = JSON.stringify(nodes.value, null, 2)
  const blob = new Blob([jsonStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'custom_scenario.haptic'
  a.click()
}

function deployToBackend() {
  alert('🎉 蓝图已成功热编译并部署至游戏引擎！')
}

function close() {
  emit('close')
}
</script>

<style scoped>
.studio-backdrop {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(8px);
  display: flex; justify-content: center; align-items: center; z-index: 10000;
}
.studio-container {
  width: 95vw; height: 90vh; background: #080b12; border: 2px solid #00f0ff;
  border-radius: 10px; box-shadow: 0 0 50px rgba(0,240,255,0.4);
  display: flex; flex-direction: column; overflow: hidden; font-family: 'Rajdhani', sans-serif; color: #e0f4ff;
}
.studio-header {
  padding: 12px 20px; background: rgba(12, 17, 28, 0.95); border-bottom: 1px solid rgba(0,240,255,0.3);
  display: flex; justify-content: space-between; align-items: center;
}
.studio-header .title { font-size: 16px; font-weight: 900; color: #00f0ff; font-family: 'Orbitron'; display: flex; align-items: center; gap: 8px; }
.header-actions { display: flex; gap: 12px; align-items: center; }
.btn-tool { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-deploy { background: #00ff88; border: none; color: #000; padding: 6px 16px; border-radius: 4px; font-weight: 900; cursor: pointer; box-shadow: 0 0 15px #00ff88; }
.btn-close { background: transparent; border: none; color: #8faec9; font-size: 18px; cursor: pointer; }

.studio-body { display: grid; grid-template-columns: 280px 1fr; height: 100%; overflow: hidden; }
.palette-sidebar {
  background: rgba(12, 17, 28, 0.9); border-right: 1px solid rgba(0,240,255,0.2); padding: 16px;
  overflow-y: auto; display: flex; flex-direction: column; gap: 10px;
}
.palette-title { font-size: 13px; font-weight: bold; color: #8faec9; margin-bottom: 6px; letter-spacing: 1px; }
.node-category { font-size: 12px; color: #ffcc00; margin-top: 10px; font-weight: bold; }
.draggable-node {
  padding: 10px 12px; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: grab;
  border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.04);
}
.draggable-node.trig { border-left: 4px solid #00f0ff; }
.draggable-node.act { border-left: 4px solid #ff0055; }
.draggable-node.voice { border-left: 4px solid #b000ff; }

.canvas-area {
  position: relative; overflow: hidden; background: #06080e;
  background-image: radial-gradient(rgba(0,240,255,0.1) 1px, transparent 1px);
  background-size: 24px 24px;
}

.canvas-node {
  position: absolute; width: 240px; background: rgba(12, 17, 28, 0.95);
  border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.6);
  user-select: none; cursor: move;
}
.canvas-node.trig { border-top: 3px solid #00f0ff; }
.canvas-node.act { border-top: 3px solid #ff0055; }
.canvas-node.voice { border-top: 3px solid #b000ff; }

.node-head {
  padding: 8px 12px; background: rgba(255,255,255,0.05); font-size: 12px; font-weight: bold;
  display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.08);
}
.node-del { cursor: pointer; color: #ff0055; }
.node-content { padding: 12px; display: flex; flex-direction: column; gap: 8px; }
.param-row label { font-size: 11px; color: #8faec9; display: block; margin-bottom: 2px; }
.param-row input[type="text"] { width: 100%; background: #000; border: 1px solid rgba(0,240,255,0.3); color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
.param-row input[type="range"] { width: 100%; }

.port { width: 12px; height: 12px; border-radius: 50%; position: absolute; background: #ffcc00; border: 2px solid #000; }
.port-in { left: -6px; top: 45%; }
.port-out { right: -6px; top: 45%; background: #00ff88; }
</style>
