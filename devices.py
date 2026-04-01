"""Input and output device management for keyboard + joystick + sound."""
from __future__ import annotations

from dataclasses import dataclass
import math
import array
import pygame
from config import HardwareConfig, InputBinding


@dataclass
class ActionEvent:
    action: str
    timestamp_ms: int


class DeviceManager:
    def __init__(self, cfg: HardwareConfig):
        self.cfg = cfg
        self.joysticks: dict[int, pygame.joystick.Joystick] = {}
        self._axis_prev: dict[tuple[int, int], float] = {}
        self.key_to_action = {}
        self._prepare_inputs()
        self.low_sound = self._generate_tone(220)
        self.high_sound = self._generate_tone(880)

    def _prepare_inputs(self) -> None:
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            js = pygame.joystick.Joystick(i)
            js.init()
            self.joysticks[i] = js

        for action_name in ("manette_gauche", "manette_droite", "pedale_gauche", "pedale_droite"):
            bind: InputBinding = getattr(self.cfg, action_name)
            if bind.mode == "keyboard" and bind.keyboard_key:
                key = pygame.key.key_code(bind.keyboard_key)
                self.key_to_action[key] = action_name

    def _generate_tone(self, freq: float, duration_s: float = 0.2, volume: float = 0.4) -> pygame.mixer.Sound:
        sample_rate, bits, channels = pygame.mixer.get_init() or (44100, -16, 1)
        amplitude = int((2 ** 15 - 1) * volume)
        n_samples = int(sample_rate * duration_s)
        buf = array.array("h")
        for i in range(n_samples):
            t = i / sample_rate
            buf.append(int(amplitude * math.sin(2 * math.pi * freq * t)))
        if channels == 2:
            stereo = array.array("h")
            for s in buf:
                stereo.append(s)
                stereo.append(s)
            buf = stereo
        return pygame.mixer.Sound(buffer=buf)

    def play_audio_stimulus(self, name: str) -> None:
        if name == "grave":
            self.low_sound.play()
        elif name == "aigu":
            self.high_sound.play()

    def poll_actions(self) -> list[ActionEvent]:
        actions: list[ActionEvent] = []
        now = pygame.time.get_ticks()
        for ev in pygame.event.get([pygame.KEYDOWN, pygame.JOYBUTTONDOWN, pygame.JOYAXISMOTION]):
            if ev.type == pygame.KEYDOWN and ev.key in self.key_to_action:
                actions.append(ActionEvent(self.key_to_action[ev.key], now))
            elif ev.type == pygame.JOYBUTTONDOWN:
                action = self._match_joy_button(ev.joy, ev.button)
                if action:
                    actions.append(ActionEvent(action, now))
            elif ev.type == pygame.JOYAXISMOTION:
                action = self._match_joy_axis(ev.joy, ev.axis, ev.value)
                if action:
                    actions.append(ActionEvent(action, now))
        return actions

    def _match_joy_button(self, joy_id: int, button: int) -> str | None:
        for action_name in ("manette_gauche", "manette_droite", "pedale_gauche", "pedale_droite"):
            bind: InputBinding = getattr(self.cfg, action_name)
            if bind.mode == "button" and bind.joystick_id == joy_id and bind.control == button:
                return action_name
        return None

    def _match_joy_axis(self, joy_id: int, axis: int, value: float) -> str | None:
        for action_name in ("manette_gauche", "manette_droite", "pedale_gauche", "pedale_droite"):
            bind: InputBinding = getattr(self.cfg, action_name)
            if bind.mode != "axis" or bind.joystick_id != joy_id or bind.control != axis:
                continue
            key = (joy_id, axis)
            prev = self._axis_prev.get(key, 0.0)
            self._axis_prev[key] = value
            if prev < bind.threshold <= value:
                return action_name
        return None
