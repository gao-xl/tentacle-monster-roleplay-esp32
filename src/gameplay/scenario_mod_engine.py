"""
Declarative YAML/JSON Scenario & Behavior Tree Engine for OpenHaptic-Roleplay (v4.0)
Allows modders and players to create custom interactive roleplay campaigns without touching Python code.
Features:
- Event Triggers (toe_curl, core_covered, struggle_level, sanity_level, timer)
- Physical & Audio Actions (shock_pulse, flow_wave, play_voice, preemption_say)
- Multi-Branch Choices and Transitions
"""

import os
import yaml
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.kokoro_engine import InterruptibleVoiceEngine, VoicePriority

logger = logging.getLogger("ScenarioModEngine")


@dataclass
class ScenarioRule:
    rule_id: str
    condition_type: str      # "toe_curl_above", "core_covered", "struggle_above", "sanity_below"
    threshold: float
    action_type: str         # "shock_burst", "flow_wave", "preemption_voice", "vibrate"
    action_payload: Dict[str, Any]
    cooldown_sec: float = 3.0
    _last_triggered: float = 0.0


@dataclass
class CustomScenarioNode:
    node_id: str
    title: str
    narrative_lore: str
    entry_voice: str
    rules: List[ScenarioRule]
    next_node_auto: Optional[str] = None
    target_overload_advance: float = 100.0


class ScenarioModEngine:
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.sequencer = sequencer
        self.voice_engine = voice_engine
        self.on_event_broadcast = on_event_broadcast
        self.nodes: Dict[str, CustomScenarioNode] = {}
        self.current_node_id: Optional[str] = None
        self.scenario_name: str = "Default Campaign"

    def load_from_yaml(self, yaml_path: str) -> bool:
        """Loads a declarative scenario from a YAML file."""
        if not os.path.exists(yaml_path):
            logger.error(f"[ModEngine] Scenario file not found: {yaml_path}")
            return False

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            self.scenario_name = data.get("name", "Custom Scenario")
            self.nodes.clear()

            for n in data.get("nodes", []):
                rules = []
                for r in n.get("rules", []):
                    rules.append(ScenarioRule(
                        rule_id=r.get("id", "rule_default"),
                        condition_type=r.get("trigger", "struggle_above"),
                        threshold=float(r.get("threshold", 0.0)),
                        action_type=r.get("action", "vibrate"),
                        action_payload=r.get("payload", {}),
                        cooldown_sec=float(r.get("cooldown", 3.0))
                    ))

                node = CustomScenarioNode(
                    node_id=n["id"],
                    title=n.get("title", n["id"]),
                    narrative_lore=n.get("lore", ""),
                    entry_voice=n.get("entry_voice", ""),
                    rules=rules,
                    next_node_auto=n.get("next_node", None),
                    target_overload_advance=float(n.get("advance_overload", 100.0))
                )
                self.nodes[node.node_id] = node

            start_node = data.get("start_node", list(self.nodes.keys())[0] if self.nodes else None)
            if start_node and start_node in self.nodes:
                self.switch_to_node(start_node)

            logger.info(f"🎉 [ModEngine] Successfully loaded scenario '{self.scenario_name}' with {len(self.nodes)} acts!")
            return True
        except Exception as e:
            logger.error(f"[ModEngine] Failed to parse scenario YAML: {e}")
            return False

    def switch_to_node(self, node_id: str):
        if node_id in self.nodes:
            self.current_node_id = node_id
            node = self.nodes[node_id]
            logger.info(f"[Scenario Act Switch] -> {node.title}")
            
            # Play entry speech (can be interrupted)
            if node.entry_voice:
                self.voice_engine.speak(node.entry_voice, priority=VoicePriority.MEDIUM_STATE)

            if self.on_event_broadcast:
                self.on_event_broadcast({"type": "SCENARIO_NODE", "node": node.node_id, "title": node.title})

    def update(self, pose: Pose26AnalysisResult, current_overload: float):
        if not self.current_node_id or self.current_node_id not in self.nodes:
            return

        now = time.time()
        node = self.nodes[self.current_node_id]

        # 1. Evaluate Rule Triggers in real time
        for rule in node.rules:
            if now - rule._last_triggered < rule.cooldown_sec:
                continue

            matched = False
            if rule.condition_type == "toe_curl_above" and pose.toe_curl_index > rule.threshold:
                matched = True
            elif rule.condition_type == "core_covered" and pose.hands_covering_core:
                matched = True
            elif rule.condition_type == "struggle_above" and pose.struggle_score > rule.threshold:
                matched = True

            if matched:
                rule._last_triggered = now
                self._execute_action(rule.action_type, rule.action_payload)

        # 2. Check Stage Progression
        if current_overload >= node.target_overload_advance and node.next_node_auto:
            self.switch_to_node(node.next_node_auto)

    def _execute_action(self, action_type: str, payload: Dict[str, Any]):
        logger.info(f"[Scenario Action] Executing {action_type}: {payload}")

        if action_type == "shock_burst":
            # Instant electric hit
            pwr = float(payload.get("power", 50.0))
            ch = int(payload.get("channel", 0))
            self.sequencer.driver.hit(channel=ch, power=pwr, decay_ms=300)

        elif action_type == "flow_wave":
            self.sequencer.trigger_pattern(QuadHapticPattern.TRAVELING_ASCEND, duration_sec=2.0)

        elif action_type == "preemption_voice":
            # HIGH PRIORITY INTERRUPTING SPEECH!
            text = payload.get("text", "抓到你了！")
            self.voice_engine.speak(text, priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
