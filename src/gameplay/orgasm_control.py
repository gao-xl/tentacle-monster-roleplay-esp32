"""
Orgasm Control & Edge/Forced Climax Gameplay Engine (Mode 4: 边缘控制与强制高潮)
Features:
- Edge & Orgasm Denial: Detects physiological threshold (Toe Curl > 50, Thigh Clamp > 0.85),
  instantly zeroing power to deny orgasm and teasing the player.
- Forced Orgasm Overload: Locks out mercy, drives continuous spatial FLOW waves until
  sustained foot spasm (>5s) confirms forced climax collapse.
- Ruined Orgasm Penalty: Punishes premature motion with sharp disruptive pulses.
"""

import time
import logging
from enum import Enum
from typing import Optional, Callable, Dict, Any
from .game_mode_base import BaseGameMode, PlayerCombatStats
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.gender_tuning import GenderTuningProfile

logger = logging.getLogger("OrgasmControlMode")


class OrgasmSubMode(str, Enum):
    DENIAL_EDGE = "DENIAL_EDGE"       # 禁止高潮 (边缘调教 / 绝不许去)
    FORCED_CLIMAX = "FORCED_CLIMAX"   # 强制高潮 (魔力过载 / 强制击溃)


class EdgePhase(str, Enum):
    CLIMBING = "CLIMBING"             # 缓慢爬升刺激阶段
    DENIED_COOLDOWN = "DENIED_COOLDOWN" # 边缘拦截与强行冷却阶段
    FORCED_SURGE = "FORCED_SURGE"     # 强制过载冲刺阶段
    AFTERGLOW = "AFTERGLOW"           # 高潮后余韵轻抚阶段


class OrgasmControlMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        sub_mode: OrgasmSubMode = OrgasmSubMode.DENIAL_EDGE,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.sub_mode = sub_mode
        self.current_phase = EdgePhase.CLIMBING
        self.edge_count = 0
        self.current_intensity = 20.0
        self.phase_start_time = time.time()
        self.sustained_spasm_seconds = 0.0

    def start(self):
        super().start()
        self.edge_count = 0
        self.current_intensity = 25.0
        self.phase_start_time = time.time()
        self.current_phase = EdgePhase.CLIMBING if self.sub_mode == OrgasmSubMode.DENIAL_EDGE else EdgePhase.FORCED_SURGE
        
        title = "🚫 禁止高潮模式：触手正在缓慢推进边缘，绝不许去！" if self.sub_mode == OrgasmSubMode.DENIAL_EDGE else "⚡ 强制高潮模式：魔力全开，准备迎接被彻底击溃吧！"
        self.stats = PlayerCombatStats(
            armor_hp=100.0,
            magic_overload=0.0,
            sanity_level=100.0,
            stage_title=title
        )
        logger.info(f"[ORGASM CONTROL] Activated Sub-Mode: {self.sub_mode.value}")
        self.broadcast_event("ORGASM_MODE_START", {"sub_mode": self.sub_mode.value, "title": title})

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # ==========================================
        # 1. 玩法 A: 禁止高潮 / 边缘调教 (DENIAL_EDGE)
        # ==========================================
        if self.sub_mode == OrgasmSubMode.DENIAL_EDGE:
            if self.current_phase == EdgePhase.CLIMBING:
                # Slowly climb intensity (+1.5% per second)
                self.current_intensity = min(self.profile.safety_power_ceiling * 0.9, self.current_intensity + dt * 2.0)
                self.stats.magic_overload = min(95.0, self.stats.magic_overload + dt * 3.5)
                self.stats.stage_title = f"📈 边缘攀升中 (已边缘 {self.edge_count} 次)... 强度: {self.current_intensity:.0f}%"

                # Dual Loop smooth creeping stimulation
                self.sequencer.driver.vibrate(channel=0, intensity=self.current_intensity)
                self.sequencer.driver.vibrate(channel=1, intensity=self.current_intensity * 0.7)

                # Edge Detection: Foot Toe Curl > 45 OR High Agitation > 35
                is_edging = (pose.toe_curl_index > 45.0 or pose.struggle_score > 35.0)
                if is_edging and self.stats.magic_overload > 60.0:
                    # 💥 EDGE REACHED -> INSTANT DENIAL SHUTOFF!
                    self.edge_count += 1
                    self.current_phase = EdgePhase.DENIED_COOLDOWN
                    self.phase_start_time = now
                    self.sequencer.driver.stop_all() # INSTANT ZERO!
                    
                    self.stats.stage_title = f"🚫 边缘拦截成功！(第 {self.edge_count} 次禁止) 给我憋回去！强行冷却中..."
                    logger.info(f"[ORGASM DENIAL] Edge {self.edge_count} Triggered! Zeroing power instantly.")
                    self.broadcast_event("EDGE_DENIED", {"edge_count": self.edge_count, "overload": self.stats.magic_overload})

            elif self.current_phase == EdgePhase.DENIED_COOLDOWN:
                # 15s Cooldown. If player moves too much, deliver Ruined Punishment pulse!
                elapsed = now - self.phase_start_time
                self.stats.magic_overload = max(30.0, self.stats.magic_overload - dt * 2.0)
                self.stats.stage_title = f"❄️ 强行冷却中 ({15 - int(elapsed)}s)... 稍有微动直接惩罚！"

                if pose.struggle_score > 25.0:
                    # Ruined penalty pulse
                    self.sequencer.driver.hit(channel=0, power=45.0, decay_ms=200)
                    self.stats.status_prompt = "⚠️ 乱动惩罚！破坏快感脉冲！"
                
                if elapsed > 15.0:
                    # Resume Climbing Phase
                    self.current_phase = EdgePhase.CLIMBING
                    self.current_intensity = max(20.0, self.current_intensity - 15.0)
                    self.broadcast_event("CLIMB_RESUME", {"edge_count": self.edge_count})

        # ==========================================
        # 2. 玩法 B: 强制高潮 / 过载击溃 (FORCED_CLIMAX)
        # ==========================================
        elif self.sub_mode == OrgasmSubMode.FORCED_CLIMAX:
            if self.current_phase == EdgePhase.FORCED_SURGE:
                self.current_intensity = min(self.profile.safety_power_ceiling, self.current_intensity + dt * 4.0)
                self.stats.magic_overload = min(100.0, self.stats.magic_overload + dt * 6.0)
                self.stats.stage_title = f"🌊 强制魔力过载冲刺中！强度: {self.current_intensity:.0f}%"

                # Ascending Traveling Flow across Loop A & B
                self.sequencer.trigger_pattern(QuadHapticPattern.TRAVELING_ASCEND, duration_sec=1.5)

                # Climax Sustain Detection: Toe curl > 40 & struggle > 40
                if pose.toe_curl_index > 35.0 or pose.struggle_score > 40.0:
                    self.sustained_spasm_seconds += dt
                    self.stats.status_prompt = f"⚡ 生理痉挛持续中: {self.sustained_spasm_seconds:.1f}s / 5.0s"
                else:
                    self.sustained_spasm_seconds = max(0.0, self.sustained_spasm_seconds - dt * 0.5)

                # Sustained for 5 seconds -> FORCED CLIMAX ACHIEVED!
                if self.sustained_spasm_seconds >= 5.0 or self.stats.magic_overload >= 99.0:
                    self.current_phase = EdgePhase.AFTERGLOW
                    self.phase_start_time = now
                    self.stats.is_defeated = True
                    self.stats.sanity_level = 0.0
                    self.stats.stage_title = "💖 强制击溃！已完全沦陷在高潮过载之中……进入余韵轻抚"
                    logger.info("[FORCED CLIMAX] Climax Peak Achieved! Entering Afterglow.")
                    self.broadcast_event("CLIMAX_ACHIEVED", {"sustained_sec": self.sustained_spasm_seconds})

            elif self.current_phase == EdgePhase.AFTERGLOW:
                # Gentle alternating afterglow pulse
                self.stats.stage_title = "✨ 高潮后余韵模式：触手正在轻抚战败者"
                self.sequencer.driver.vibrate(channel=0, intensity=15.0)
                self.sequencer.driver.vibrate(channel=1, intensity=10.0)

        return self.stats

    def stop(self):
        super().stop()
        logger.info("[ORGASM CONTROL] Mode Stopped.")
