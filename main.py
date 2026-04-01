from __future__ import annotations

import time
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pygame

from config import (
    APP_TITLE,
    DEFAULT_REPORTS_DIR,
    DEFAULT_RESULTS_DIR,
    PROTOCOL_VERSION,
    load_config,
)
from devices import DeviceManager
from protocol import TEST_PHASES, EXPECTED_RESPONSE_BY_STIMULUS, build_balanced_sequence
from scoring import classify_trial, trial_error_rate_percent, compute_by_rhythm
from report import generate_pdf_report
from utils import compute_age_on_date, ensure_dirs, parse_birth_date, save_json, save_trials_csv, timestamp_for_filename

WIDTH, HEIGHT = 1000, 620
WHITE, BLACK = (245, 245, 245), (40, 40, 40)
BLUE, RED = (20, 90, 220), (220, 60, 60)


@dataclass
class Candidate:
    nom: str
    prenom: str
    date_naissance: str
    age: int


class App:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(APP_TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 24)
        self.small = pygame.font.SysFont("arial", 18)

        self.cfg = load_config()
        self.devices = DeviceManager(self.cfg)
        ensure_dirs(DEFAULT_RESULTS_DIR, DEFAULT_REPORTS_DIR)

        self.state = "welcome"
        self.running = True
        self.fields = {"nom": "", "prenom": "", "dob": "1990-01-01"}
        self.active_field = "nom"
        self.candidate: Candidate | None = None
        self.validation_attempts = 0
        self.validation_passed = False
        self.validation_last_error = 100.0
        self.main_rows: list[dict] = []
        self.test_start = None
        self.summary = None

    def run(self):
        while self.running:
            if self.state == "welcome":
                self._screen_welcome()
            elif self.state == "learning":
                self._screen_learning()
            elif self.state == "validation":
                self._run_validation()
            elif self.state == "main_test":
                self._run_main_test()
            elif self.state == "results":
                self._screen_results()
            self.clock.tick(60)

    def _draw_text(self, txt, x, y, color=BLACK, small=False):
        f = self.small if small else self.font
        self.screen.blit(f.render(txt, True, color), (x, y))

    def _screen_welcome(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_TAB:
                    self.active_field = {"nom": "prenom", "prenom": "dob", "dob": "nom"}[self.active_field]
                elif ev.key == pygame.K_RETURN:
                    self._start_candidate()
                elif ev.key == pygame.K_BACKSPACE:
                    self.fields[self.active_field] = self.fields[self.active_field][:-1]
                else:
                    ch = ev.unicode
                    if ch.isprintable():
                        self.fields[self.active_field] += ch

        self.screen.fill(WHITE)
        self._draw_text("Écran 1 - Informations candidat", 30, 20)
        self._draw_text("Nom:", 30, 100)
        self._draw_text(self.fields["nom"] + ("_" if self.active_field == "nom" else ""), 250, 100)
        self._draw_text("Prénom:", 30, 150)
        self._draw_text(self.fields["prenom"] + ("_" if self.active_field == "prenom" else ""), 250, 150)
        self._draw_text("Date naissance (YYYY-MM-DD):", 30, 200)
        self._draw_text(self.fields["dob"] + ("_" if self.active_field == "dob" else ""), 380, 200)
        self._draw_text("Entrée: démarrer", 30, 260, small=True)
        self._draw_text("TAB: champ suivant", 30, 290, small=True)
        pygame.display.flip()

    def _start_candidate(self):
        try:
            birth = parse_birth_date(self.fields["dob"])
        except ValueError:
            return
        now = datetime.now()
        age = compute_age_on_date(birth, now.date())
        self.candidate = Candidate(self.fields["nom"].strip(), self.fields["prenom"].strip(), self.fields["dob"], age)
        self.state = "learning"

    def _screen_learning(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                self.state = "validation"

        actions = self.devices.poll_actions()
        self.screen.fill(WHITE)
        self._draw_text("Écran 2 - Apprentissage libre", 30, 20)
        self._draw_text("A=manette gauche->rond bleu | L=manette droite->rond rouge", 30, 70, small=True)
        self._draw_text("Q=pédale gauche->son grave | P=pédale droite->son aigu", 30, 100, small=True)
        self._draw_text("Appuyez librement, puis Entrée pour passer à l'essai", 30, 140, small=True)

        for a in actions:
            if a.action == "manette_gauche":
                pygame.draw.circle(self.screen, BLUE, (250, 320), 70)
            elif a.action == "manette_droite":
                pygame.draw.circle(self.screen, RED, (740, 320), 70)
            elif a.action == "pedale_gauche":
                self.devices.play_audio_stimulus("grave")
            elif a.action == "pedale_droite":
                self.devices.play_audio_stimulus("aigu")
        pygame.display.flip()

    def _present_stimulus(self, stim: str):
        self.screen.fill(WHITE)
        self._draw_text("Réagissez au stimulus", 30, 20)
        if stim == "bleu":
            pygame.draw.circle(self.screen, BLUE, (WIDTH // 2, HEIGHT // 2), 90)
        elif stim == "rouge":
            pygame.draw.circle(self.screen, RED, (WIDTH // 2, HEIGHT // 2), 90)
        else:
            self._draw_text("Stimulus audio en cours...", 370, 280)
            self.devices.play_audio_stimulus(stim)
        pygame.display.flip()

    def _collect_for_stimulus(self, stim: str, duration_s: float, phase: str, rhythm: str | None, trial_id_start: int):
        expected = EXPECTED_RESPONSE_BY_STIMULUS[stim]
        self._present_stimulus(stim)
        start_ms = pygame.time.get_ticks()
        response, rt = None, None

        while (pygame.time.get_ticks() - start_ms) < int(duration_s * 1000):
            for ev in pygame.event.get([pygame.QUIT]):
                if ev.type == pygame.QUIT:
                    self.running = False
                    return None
            acts = self.devices.poll_actions()
            if acts and response is None:
                response = acts[0].action
                rt = acts[0].timestamp_ms - start_ms
            self.clock.tick(120)

        status = classify_trial(expected, response, rt)
        return {
            "trial_id": trial_id_start,
            "phase": phase,
            "rhythm": rhythm,
            "stimulus": stim,
            "expected_response": expected,
            "response": response,
            "status": status,
            "reaction_time_ms": rt,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    def _run_validation(self):
        self.validation_attempts += 1
        rng = random.Random(time.time_ns())
        start = time.time()
        rows = []
        trial_id = 1
        while time.time() - start < 30 and self.running:
            stim = rng.choice(["bleu", "rouge", "grave", "aigu"])
            row = self._collect_for_stimulus(stim, 1.2, "essai", None, trial_id)
            if row:
                rows.append(row)
            trial_id += 1

        err_pct = trial_error_rate_percent(rows)
        self.validation_last_error = err_pct
        self.validation_passed = err_pct <= 50.0

        self.screen.fill(WHITE)
        self._draw_text("Écran 3 - Résultat essai", 30, 20)
        self._draw_text(f"Bonnes: {sum(r['status']=='correct' for r in rows)}", 30, 120)
        self._draw_text(f"Erreurs: {sum(r['status']=='erreur' for r in rows)}", 30, 160)
        self._draw_text(f"Omissions: {sum(r['status']=='omission' for r in rows)}", 30, 200)
        self._draw_text(f"Taux d'erreurs: {err_pct:.2f}%", 30, 240)
        if self.validation_passed:
            self._draw_text("Essai validé (<=50%). Entrée pour test principal.", 30, 300, color=(0, 130, 0))
        else:
            self._draw_text("Essai échoué (>50%). Entrée pour retour apprentissage.", 30, 300, color=(160, 0, 0))
        pygame.display.flip()

        waiting = True
        while waiting and self.running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                    return
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                    self.state = "main_test" if self.validation_passed else "learning"
                    waiting = False
            self.clock.tick(30)

    def _run_main_test(self):
        rng = random.Random(time.time_ns())
        rows = []
        trial_id = 1
        self.test_start = time.time()

        for p in TEST_PHASES:
            seq = build_balanced_sequence(p.signal_count, rng)
            for stim in seq:
                if not self.running:
                    return
                row = self._collect_for_stimulus(stim, p.duration_s, "test", p.name, trial_id)
                if row:
                    rows.append(row)
                trial_id += 1
                if self.cfg.neutral_interval_seconds > 0:
                    t_end = time.time() + self.cfg.neutral_interval_seconds
                    while time.time() < t_end:
                        for ev in pygame.event.get([pygame.QUIT]):
                            if ev.type == pygame.QUIT:
                                self.running = False
                                return
                        self.screen.fill(WHITE)
                        self._draw_text(f"Rythme en cours: {p.name}", 30, 20)
                        pygame.display.flip()

        self.main_rows = rows
        self._finalize()
        self.state = "results"

    def _finalize(self):
        assert self.candidate
        metrics = compute_by_rhythm(self.main_rows)
        actual_duration = time.time() - self.test_start
        test_dt = datetime.now()
        token = timestamp_for_filename(test_dt)

        summary = {
            "candidate": {
                "nom": self.candidate.nom,
                "prenom": self.candidate.prenom,
                "date_naissance": self.candidate.date_naissance,
                "age": self.candidate.age,
            },
            "test_datetime": test_dt.isoformat(timespec="seconds"),
            "protocol_version": PROTOCOL_VERSION,
            "validation_trial": {
                "attempts": self.validation_attempts,
                "final_error_pct": self.validation_last_error,
                "validated": self.validation_passed,
            },
            "main_test_params": {
                "total_signals": 108,
                "actual_duration_s": actual_duration,
            },
            "metrics": metrics,
        }
        self.summary = summary

        json_path = DEFAULT_RESULTS_DIR / f"result_{token}.json"
        csv_path = DEFAULT_RESULTS_DIR / f"trials_{token}.csv"
        pdf_path = DEFAULT_REPORTS_DIR / f"report_{token}.pdf"

        save_json(json_path, summary)
        save_trials_csv(csv_path, self.main_rows)
        generate_pdf_report(pdf_path, summary, metrics, self.main_rows)

    def _screen_results(self):
        m = self.summary["metrics"]["global"] if self.summary else {}
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_n:
                    self.__init__()
                elif ev.key == pygame.K_ESCAPE:
                    self.running = False

        self.screen.fill(WHITE)
        self._draw_text("Écran 5 - Résultats", 30, 20)
        self._draw_text(f"Performance globale: {m.get('performance_pct', 0):.2f}%", 30, 110)
        self._draw_text(f"Br={m.get('br', 0)} Er={m.get('er', 0)} Om={m.get('om', 0)}", 30, 150)
        self._draw_text("Rapport PDF et fichiers résultats générés automatiquement.", 30, 200, small=True)
        self._draw_text("N: nouveau test | ESC: quitter", 30, 230, small=True)
        pygame.display.flip()


if __name__ == "__main__":
    App().run()
    pygame.quit()
