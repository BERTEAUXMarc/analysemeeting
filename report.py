"""PDF report generation for reaction test."""
from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image


def _make_chart(rows: list[dict], chart_path: Path) -> None:
    xs = list(range(1, len(rows) + 1))
    ys = [r["reaction_time_ms"] if r["reaction_time_ms"] is not None else 0 for r in rows]
    colors_map = ["green" if r["status"] == "correct" else "red" if r["status"] == "erreur" else "gray" for r in rows]

    plt.figure(figsize=(8, 2.2))
    plt.scatter(xs, ys, c=colors_map, s=14)
    plt.title("Temps de réaction essai par essai")
    plt.xlabel("Essai")
    plt.ylabel("ms")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=130)
    plt.close()


def generate_pdf_report(output_path: Path, summary: dict, metrics_by_rhythm: dict, rows: list[dict]) -> None:
    chart_path = output_path.with_suffix(".png")
    _make_chart(rows, chart_path)

    doc = SimpleDocTemplate(str(output_path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("<b>Bilan Test de réactions complexes</b>", styles["Title"]))
    identity = summary["candidate"]
    header_lines = [
        f"Nom: {identity['nom']} {identity['prenom']}",
        f"Date de naissance: {identity['date_naissance']} | Âge: {identity['age']}",
        f"Date/heure du test: {summary['test_datetime']} | Version protocole: {summary['protocol_version']}",
    ]
    for line in header_lines:
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 8))

    trial = summary["validation_trial"]
    story.append(Paragraph(
        f"Essais de validation: tentatives={trial['attempts']} | taux erreurs final={trial['final_error_pct']:.2f}% | validé={trial['validated']}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 8))

    p = summary["main_test_params"]
    story.append(Paragraph(
        f"Signaux: {p['total_signals']} (Lent 36@2.0s, Modéré 36@1.5s, Rapide 36@1.0s) | durée exécutée={p['actual_duration_s']:.2f}s",
        styles["Normal"],
    ))
    story.append(Spacer(1, 8))

    table_data = [["Série", "Nb signaux", "Performance (%)", "Br", "Er", "Om", "Moy.", "Méd.", "E.T."]]
    labels = [("global", "Global"), ("lent", "Rythme Lent"), ("modere", "Rythme Modéré"), ("rapide", "Rythme Rapide")]
    for key, label in labels:
        m = metrics_by_rhythm[key]
        table_data.append([
            label,
            m["nb_signaux"],
            f"{m['performance_pct']:.2f}",
            m["br"],
            m["er"],
            m["om"],
            "-" if m["mean_ms"] is None else f"{m['mean_ms']:.1f}",
            "-" if m["median_ms"] is None else f"{m['median_ms']:.1f}",
            "-" if m["std_ms"] is None else f"{m['std_ms']:.1f}",
        ])

    tbl = Table(table_data)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 8))
    story.append(Image(str(chart_path), width=500, height=150))
    doc.build(story)
