"""Stimulus protocol generation and models."""
from __future__ import annotations

from dataclasses import dataclass
import random

STIMULI = ["bleu", "rouge", "grave", "aigu"]
EXPECTED_RESPONSE_BY_STIMULUS = {
    "bleu": "manette_gauche",
    "rouge": "manette_droite",
    "grave": "pedale_gauche",
    "aigu": "pedale_droite",
}


@dataclass
class PhaseDefinition:
    name: str
    signal_count: int
    duration_s: float


TEST_PHASES = [
    PhaseDefinition("lent", 36, 2.0),
    PhaseDefinition("modere", 36, 1.5),
    PhaseDefinition("rapide", 36, 1.0),
]


def build_balanced_sequence(length: int, rng: random.Random) -> list[str]:
    base_count = length // len(STIMULI)
    rem = length % len(STIMULI)
    seq = []
    for s in STIMULI:
        seq.extend([s] * base_count)
    seq.extend(rng.sample(STIMULI, k=rem))

    for _ in range(2000):
        rng.shuffle(seq)
        if _is_valid_run(seq):
            return seq
    return _repair_sequence(seq, rng)


def _is_valid_run(seq: list[str]) -> bool:
    run = 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            run += 1
            if run > 2:
                return False
        else:
            run = 1
    return True


def _repair_sequence(seq: list[str], rng: random.Random) -> list[str]:
    seq = seq[:]
    for i in range(2, len(seq)):
        if seq[i] == seq[i - 1] == seq[i - 2]:
            for j in range(i + 1, len(seq)):
                if seq[j] != seq[i - 1]:
                    seq[i], seq[j] = seq[j], seq[i]
                    break
            else:
                options = [x for x in STIMULI if x != seq[i - 1]]
                seq[i] = rng.choice(options)
    return seq
