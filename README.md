# Application de test de réactions complexes (Python)

## Arborescence

```text
analysemeeting/
├─ main.py
├─ config.py
├─ devices.py
├─ protocol.py
├─ scoring.py
├─ report.py
├─ utils.py
├─ requirements.txt
├─ hardware_config.example.json
├─ sample_output.json
├─ reports/                  # généré à l'exécution
└─ results/                  # généré à l'exécution
```

## Installation

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
```

## Exécution

```bash
python main.py
```

## Configuration matérielle

- Au premier démarrage, `hardware_config.json` est créé automatiquement (mode clavier debug par défaut):
  - manette gauche = `A`
  - manette droite = `L`
  - pédale gauche = `Q`
  - pédale droite = `P`
- Pour le matériel réel, copier `hardware_config.example.json` vers `hardware_config.json`, puis ajuster :
  - `mode`: `button` ou `axis`
  - `joystick_id`
  - `control` (index bouton/axe)
  - `threshold` (si axe analogique)

## Protocole implémenté

1. **Écran accueil**: nom, prénom, date de naissance (`YYYY-MM-DD`), âge calculé automatiquement.
2. **Apprentissage libre**: test des 4 commandes, passage via Entrée.
3. **Essai de validation (30s)**: stimuli aléatoires, calcul bonnes/erreurs/omissions et taux d'erreur.
   - Si taux erreur `> 50%`: retour apprentissage obligatoire.
   - Si taux erreur `<= 50%`: accès test principal.
4. **Test principal**:
   - Lent: 36 signaux à 2.0s
   - Modéré: 36 signaux à 1.5s
   - Rapide: 36 signaux à 1.0s
   - Total: 108 signaux
5. **Résultats**: résumé + export automatique JSON/CSV/PDF.

## Données enregistrées

- `results/result_YYYYMMDD_HHMMSS.json`: résumé, métriques globales + par rythme
- `results/trials_YYYYMMDD_HHMMSS.csv`: données essai par essai
- `reports/report_YYYYMMDD_HHMMSS.pdf`: rapport PDF (table + graphique RT)

## Limites connues

- Interface volontairement simple (pygame) pour robustesse terrain, sans éditeur graphique avancé.
- Mapping matériel se fait par fichier JSON (pas encore d'assistant UI de calibration).
- Sons générés synthétiquement (sinusoïdes), personnalisables dans `devices.py`.

## Pistes d'amélioration

- Assistant de calibration des périphériques intégré dans l'UI.
- Boutons UI souris (actuellement navigation majoritairement clavier).
- Multi-langue FR/EN.
- Export brut enrichi (événements périphériques, logs techniques).
