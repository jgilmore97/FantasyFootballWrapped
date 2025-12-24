"""Generate a holiday/Spotify-styled PDF from the existing wrapped report.

This script avoids hitting the ESPN API by parsing the already-generated
``fantasy_wrapped_report.txt`` and turning the highlights into a multi-page PDF
with playful copy. It leans into a "Wrapped" vibe (dark background + neon
accents) with some holiday touches for the Christmas-week championship.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

REPORT_PATH = Path("fantasy_wrapped_report.txt")
OUTPUT_PDF = Path("amateur_hardcore_fantasy_wrapped.pdf")

PRIMARY_GREEN = "#1DB954"  # Spotify green
NIGHT_BG = "#0b0b0f"
CANDY_RED = "#e63946"
GOLD = "#ffce00"
WINTER_BLUE = "#7bdff2"


@dataclass
class HeadToHeadCell:
    wins: int
    losses: int
    ties: int


@dataclass
class HeadToHead:
    legend: Dict[int, str]
    matrix: Dict[Tuple[str, str], HeadToHeadCell]


@dataclass
class ParsedReport:
    scoring: List[Tuple[str, float]]
    win_pct: List[Tuple[str, float]]
    luck: List[Tuple[str, float]]
    awards: Dict[str, str]
    h2h: HeadToHead
    generated_at: datetime


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_section(lines: List[str], header: str) -> List[str]:
    idx = next((i for i, ln in enumerate(lines) if ln.strip().startswith(header)), -1)
    if idx == -1:
        return []
    chunk: List[str] = []
    for ln in lines[idx + 1 :]:
        if not ln.strip():
            break
        chunk.append(ln)
    return chunk


def _parse_rankings(lines: List[str], pattern: str) -> List[Tuple[str, float]]:
    results: List[Tuple[str, float]] = []
    regex = re.compile(pattern)
    for ln in lines:
        match = regex.match(ln)
        if match:
            name = match.group(1).strip()
            value = float(match.group(2))
            results.append((name, value))
    return results


def _parse_head_to_head(lines: List[str]) -> HeadToHead:
    legend: Dict[int, str] = {}
    matrix: Dict[Tuple[str, str], HeadToHeadCell] = {}

    # Find legend block
    legend_start = next((i for i, ln in enumerate(lines) if ln.strip() == "LEGEND:"), -1)
    if legend_start == -1:
        return HeadToHead(legend=legend, matrix=matrix)

    i = legend_start + 1
    while i < len(lines):
        ln = lines[i].strip()
        legend_match = re.match(r"(\d+)\.\s+(.*)", ln)
        if legend_match:
            legend[int(legend_match.group(1))] = legend_match.group(2).strip()
            if ln.startswith("10."):
                break
            i += 1
            continue
        # Stop when legend entries end
        if not ln:
            break
        i += 1

    # Find table rows after separator
    table_start = next((j for j, ln in enumerate(lines) if ln.startswith("  1 |")), -1)
    if table_start == -1:
        return HeadToHead(legend=legend, matrix=matrix)

    table_lines = lines[table_start : table_start + len(legend)]
    for row in table_lines:
        parts = [p.strip() for p in row.split("|") if p.strip()]
        if not parts:
            continue
        row_idx = int(parts[0])
        row_name = legend.get(row_idx, str(row_idx))
        opponents = parts[1:]
        for col_idx, record in enumerate(opponents, start=1):
            if record == "--":
                continue
            col_name = legend.get(col_idx, str(col_idx))
            wins, losses, *maybe_ties = record.replace(" ", "").split("-")
            ties = int(maybe_ties[0]) if maybe_ties else 0
            matrix[(row_name, col_name)] = HeadToHeadCell(
                wins=int(wins), losses=int(losses), ties=ties
            )

    return HeadToHead(legend=legend, matrix=matrix)


def parse_report(path: Path = REPORT_PATH) -> ParsedReport:
    if not path.exists():
        raise FileNotFoundError("fantasy_wrapped_report.txt is required to build the PDF")

    lines = [ln.rstrip("\n") for ln in path.read_text(encoding="utf-8").splitlines()]

    scoring = _parse_rankings(
        _parse_section(lines, "ALL-TIME SCORING RANKINGS:"),
        r"\s*\d+\.\s+(.+?)\s+([0-9.]+) pts",
    )
    win_pct = _parse_rankings(
        _parse_section(lines, "ALL-TIME WIN PERCENTAGE RANKINGS:"),
        r"\s*\d+\.\s+(.+?)\s+\d+-\d+-\s*\d+\s+\(\s*([0-9.]+)%\)",
    )
    luck = _parse_rankings(
        _parse_section(lines, "LUCK RANKINGS"),
        r"\s*\d+\.\s+(.+?)\s+([0-9.]+) pts against",
    )

    awards: Dict[str, str] = {}
    for ln in lines:
        if ln.startswith("📈 ALL-TIME SCORING LEADER"):
            awards["scoring_leader"] = ln.split(":", 1)[1].strip()
        if ln.startswith("🥇 BEST ALL-TIME RECORD"):
            awards["best_record"] = ln.split(":", 1)[1].strip()
        if ln.startswith("😬 UNLUCKIEST MANAGER"):
            awards["unluckiest"] = ln.split(":", 1)[1].strip()
        if ln.startswith("🍀 LUCKIEST MANAGER"):
            awards["luckiest"] = ln.split(":", 1)[1].strip()
        if ln.startswith("🤒 MOST INJURED TEAM"):
            awards["most_injured"] = ln.split(":", 1)[1].strip()
        if ln.startswith("🏅 MOST VALUABLE PLAYER (Single Season)"):
            awards["mvp_single"] = ln.split(":", 1)[1].strip()
        if ln.startswith("🏆 MOST VALUABLE PLAYER (5-Year Total VOR)"):
            awards["mvp_total"] = ln.split(":", 1)[1].strip()

    h2h = _parse_head_to_head(lines)

    generated_at = datetime.now()
    stamp_line = next((ln for ln in lines if ln.startswith("Generated on")), None)
    if stamp_line:
        try:
            generated_at = datetime.strptime(stamp_line.split("on", 1)[1].strip(), "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    return ParsedReport(
        scoring=scoring,
        win_pct=win_pct,
        luck=luck,
        awards=awards,
        h2h=h2h,
        generated_at=generated_at,
    )


# ---------------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------------

def _holiday_spotify_axes(fig, title: str, subtitle: str | None = None):
    ax = fig.add_subplot(111)
    ax.set_facecolor(NIGHT_BG)
    fig.patch.set_facecolor(NIGHT_BG)
    ax.axis("off")
    ax.text(
        0.02,
        0.92,
        title,
        transform=ax.transAxes,
        fontsize=26,
        fontweight="bold",
        color=PRIMARY_GREEN,
        ha="left",
        va="top",
    )
    if subtitle:
        ax.text(
            0.02,
            0.82,
            subtitle,
            transform=ax.transAxes,
            fontsize=13,
            color=WINTER_BLUE,
            ha="left",
            va="top",
        )
    return ax


def _barh(ax, labels: List[str], values: List[float], color: str, title: str):
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=color, edgecolor="white")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color="white", fontsize=10)
    ax.invert_yaxis()
    ax.set_facecolor(NIGHT_BG)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="x", colors=WINTER_BLUE)
    ax.set_title(title, color=PRIMARY_GREEN, pad=12, fontsize=16, fontweight="bold")
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}", va="center", color=GOLD, fontsize=10, fontweight="bold")


def _section_footer(fig, timestamp: datetime):
    fig.text(0.98, 0.02, f"Generated {timestamp:%Y-%m-%d}", color=WINTER_BLUE,
             ha="right", va="bottom", fontsize=8)


def _title_page(pdf: PdfPages, parsed: ParsedReport):
    fig = plt.figure(figsize=(8.5, 11))
    ax = _holiday_spotify_axes(
        fig,
        "Amateur Hardcore Fantasy Wrapped",
        "Christmas Championship Edition",
    )
    ax.text(
        0.02,
        0.68,
        "Like Spotify Wrapped, but for managers who set lineups in between holiday pies.\n"
        "We kept the neon vibes and sprinkled in some tinsel for the final showdown.",
        transform=ax.transAxes,
        color="white",
        fontsize=12,
        ha="left",
    )
    ax.text(
        0.02,
        0.52,
        f"League MVP so far: {parsed.awards.get('mvp_single', 'TBD')}\n"
        f"All-time points boss: {parsed.awards.get('scoring_leader', 'Unknown')}\n"
        f"Win% leader: {parsed.awards.get('best_record', 'Unknown')}",
        transform=ax.transAxes,
        color=GOLD,
        fontsize=14,
        ha="left",
        fontweight="bold",
    )
    ax.text(
        0.02,
        0.38,
        "Scroll (or sleigh) through for charts, rivalries, and some festive chirps.",
        transform=ax.transAxes,
        color=WINTER_BLUE,
        fontsize=11,
    )
    _section_footer(fig, parsed.generated_at)
    pdf.savefig(fig, facecolor=NIGHT_BG)
    plt.close(fig)


def _awards_page(pdf: PdfPages, parsed: ParsedReport):
    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
    for ax in axes:
        ax.axis("off")
        ax.set_facecolor(NIGHT_BG)
    fig.patch.set_facecolor(NIGHT_BG)

    awards_left = [
        ("📈 Scoring Leader", parsed.awards.get("scoring_leader", "?")),
        ("🥇 Best Record", parsed.awards.get("best_record", "?")),
        ("🍀 Luckiest", parsed.awards.get("luckiest", "?")),
        ("😬 Unluckiest", parsed.awards.get("unluckiest", "?")),
    ]
    awards_right = [
        ("🏅 MVP Season", parsed.awards.get("mvp_single", "?")),
        ("🏆 MVP (5yr Total)", parsed.awards.get("mvp_total", "?")),
        ("🤒 Most Injured", parsed.awards.get("most_injured", "?")),
    ]

    for ax, col, title in zip(axes, [awards_left, awards_right], ["Core Awards", "Player Buzz"]):
        ax.text(0.02, 0.92, title, transform=ax.transAxes, color=PRIMARY_GREEN,
                fontsize=18, fontweight="bold", ha="left")
        y = 0.8
        for label, value in col:
            ax.text(0.02, y, f"{label}:", transform=ax.transAxes, color=WINTER_BLUE,
                    fontsize=12, fontweight="bold", ha="left")
            ax.text(0.02, y - 0.07, value, transform=ax.transAxes, color="white",
                    fontsize=16, fontweight="bold", ha="left")
            y -= 0.18

    fig.suptitle("Awards with Holiday Shine", color=GOLD, fontsize=22, fontweight="bold")
    _section_footer(fig, parsed.generated_at)
    fig.tight_layout(rect=[0, 0.05, 1, 0.9])
    pdf.savefig(fig, facecolor=NIGHT_BG)
    plt.close(fig)


def _rankings_page(pdf: PdfPages, parsed: ParsedReport):
    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
    fig.patch.set_facecolor(NIGHT_BG)
    _barh(axes[0], [n for n, _ in parsed.scoring], [v for _, v in parsed.scoring], GOLD,
          "All-Time Points (Festive Glow)")
    _barh(axes[1], [n for n, _ in parsed.win_pct], [v for _, v in parsed.win_pct], PRIMARY_GREEN,
          "Win% Snowdrift")
    for ax in axes:
        ax.set_xlabel("", color="white")
    fig.suptitle("Who Carries the Aux Cord & The League", color=WINTER_BLUE, fontsize=20,
                 fontweight="bold")
    _section_footer(fig, parsed.generated_at)
    fig.tight_layout(rect=[0, 0.05, 1, 0.92])
    pdf.savefig(fig, facecolor=NIGHT_BG)
    plt.close(fig)


def _luck_page(pdf: PdfPages, parsed: ParsedReport):
    fig, ax = plt.subplots(figsize=(11, 8.5))
    _holiday_spotify_axes(fig, "Luck-o-Meter", "Lower points against = more holiday cheer")
    labels = [n for n, _ in parsed.luck]
    values = [v for _, v in parsed.luck]
    colors = [PRIMARY_GREEN if i < len(labels) / 2 else CANDY_RED for i in range(len(labels))]
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=colors, edgecolor="white")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color="white")
    ax.invert_yaxis()
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="x", colors=WINTER_BLUE)
    ax.set_facecolor(NIGHT_BG)
    for bar, val in zip(bars, values):
        ax.text(val + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:,.0f} pts", va="center", color="white", fontsize=10)
    _section_footer(fig, parsed.generated_at)
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    pdf.savefig(fig, facecolor=NIGHT_BG)
    plt.close(fig)


def _rivalry_page(pdf: PdfPages, parsed: ParsedReport):
    fig = plt.figure(figsize=(11, 8.5))
    ax = _holiday_spotify_axes(fig, "Rivalries & Drama", "Because Wrapped needs a villain arc")

    derek_vs_kilian = parsed.h2h.matrix.get(("Derek Topper", "Kilian Nelson"))
    jack_vs_veronica = parsed.h2h.matrix.get(("Jack Gilmore", "Veronica Agne"))

    bullet_y = 0.72
    bullets = [
        "Derek is 0-9 against Kilian despite big points — absolute Grinch curse.",
        "Jack's only losing matchup is fiancée Veronica (2-5). Engagement treaty confirmed.",
        "Peter's 8-game heater in 2023 was hotter than mulled wine on the stove.",
    ]

    for blt in bullets:
        ax.text(0.04, bullet_y, f"• {blt}", transform=ax.transAxes, color="white",
                fontsize=12, ha="left")
        bullet_y -= 0.1

    table_ax = fig.add_axes([0.05, 0.05, 0.9, 0.45])
    table_ax.axis("off")
    table_ax.set_facecolor(NIGHT_BG)

    legend = parsed.h2h.legend
    headers = [legend[i] for i in sorted(legend.keys())]
    data = []
    for row_idx in sorted(legend.keys()):
        row_name = legend[row_idx]
        row_vals = []
        for col_idx in sorted(legend.keys()):
            if row_idx == col_idx:
                row_vals.append("—")
                continue
            cell = parsed.h2h.matrix.get((row_name, legend[col_idx]))
            row_vals.append(f"{cell.wins}-{cell.losses}" if cell else "?")
        data.append(row_vals)

    table = table_ax.table(
        cellText=data,
        rowLabels=headers,
        colLabels=headers,
        cellLoc="center",
        loc="center",
    )
    table.scale(1, 1.2)
    table_ax.set_title("Head-to-Head Record Snowglobe", color=GOLD, fontsize=14, pad=14)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(NIGHT_BG)
        cell.set_facecolor("#1f1f2e")
        cell.set_text_props(color="white", fontsize=8)
    _section_footer(fig, parsed.generated_at)
    pdf.savefig(fig, facecolor=NIGHT_BG)
    plt.close(fig)


def _final_page(pdf: PdfPages, parsed: ParsedReport):
    fig = plt.figure(figsize=(8.5, 11))
    ax = _holiday_spotify_axes(fig, "Final Sleigh Bells", "Championship on Christmas weekend")
    ax.text(
        0.02,
        0.7,
        "Jack may be leading, but the tree isn't lit until the final score hits.\n"
        "Everyone else: spike the eggnog, set your lineup, and hope Kilian keeps his Derek hex running.",
        transform=ax.transAxes,
        color="white",
        fontsize=12,
        ha="left",
    )
    ax.text(
        0.02,
        0.52,
        "Next year wish list: fewer injuries, more waiver miracles, and better screenshot angles for your victory posts.",
        transform=ax.transAxes,
        color=WINTER_BLUE,
        fontsize=11,
        ha="left",
    )
    ax.text(
        0.02,
        0.34,
        "Amateur Hardcore Fantasy loves you. Now go win the thing.",
        transform=ax.transAxes,
        color=GOLD,
        fontsize=13,
        ha="left",
        fontweight="bold",
    )
    _section_footer(fig, parsed.generated_at)
    pdf.savefig(fig, facecolor=NIGHT_BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def build_pdf():
    parsed = parse_report()
    with PdfPages(OUTPUT_PDF) as pdf:
        _title_page(pdf, parsed)
        _awards_page(pdf, parsed)
        _rankings_page(pdf, parsed)
        _luck_page(pdf, parsed)
        _rivalry_page(pdf, parsed)
        _final_page(pdf, parsed)
    print(f"Saved: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
