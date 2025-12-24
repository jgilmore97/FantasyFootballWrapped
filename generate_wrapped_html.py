"""Build a shareable "Amateur Hardcore Fantasy Wrapped" HTML page.

This script starts from the existing `fantasy_wrapped_report.txt` and
`fantasy_wrapped_data.json` artifacts and renders a single, mobile-friendly HTML
page with inline CSS and base64-embedded charts. It is intentionally PDF-free so
it can be dropped into a group chat, opened in a browser, or screenshotted
without worrying about font glyphs.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt

REPORT_PATH = Path("fantasy_wrapped_report.txt")
DATA_PATH = Path("fantasy_wrapped_data.json")
OUTPUT_HTML = Path("amateur_hardcore_fantasy_wrapped.html")

# Spotify-ish palette with a holiday pop
NIGHT_BG = "#0b0b0f"
PRIMARY_GREEN = "#1DB954"
CANDY_RED = "#e63946"
MINT = "#7bdff2"
GOLD = "#ffce00"


@dataclass
class HeadToHeadCell:
    wins: int
    losses: int
    ties: int

    def label(self) -> str:
        return f"{self.wins}-{self.losses}-{self.ties}" if self.ties else f"{self.wins}-{self.losses}"


@dataclass
class HeadToHead:
    legend: Dict[int, str]
    matrix: Dict[Tuple[str, str], HeadToHeadCell]

    def record(self, owner: str, opponent: str) -> HeadToHeadCell | None:
        return self.matrix.get((owner, opponent))


@dataclass
class ParsedReport:
    scoring: List[Tuple[str, float]]
    win_pct: List[Tuple[str, float]]
    luck: List[Tuple[str, float]]
    awards: Dict[str, str]
    h2h: HeadToHead
    generated_at: datetime
    streaks: Dict[str, str]


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
        chunk.append(ln.rstrip("\n"))
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

    legend_start = next((i for i, ln in enumerate(lines) if ln.strip() == "LEGEND:"), -1)
    if legend_start != -1:
        i = legend_start + 1
        while i < len(lines):
            ln = lines[i].strip()
            legend_match = re.match(r"(\d+)\.\s+(.*)", ln)
            if legend_match:
                legend[int(legend_match.group(1))] = legend_match.group(2).strip()
                i += 1
                continue
            if not ln:
                break
            i += 1

    table_start = next((j for j, ln in enumerate(lines) if ln.startswith("  1 |")), -1)
    if table_start != -1 and legend:
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
        raise FileNotFoundError("fantasy_wrapped_report.txt is required to build the HTML")

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
    streaks: Dict[str, str] = {}
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
        if ln.startswith("🔥 LONGEST WIN STREAK"):
            streaks["longest_win"] = ln.split(":", 1)[1].strip()
        if ln.startswith("😭 LONGEST LOSING STREAK"):
            streaks["longest_loss"] = ln.split(":", 1)[1].strip()

    h2h = _parse_head_to_head(lines)

    generated_at = datetime.now()
    stamp_line = next((ln for ln in lines if ln.startswith("Generated on")), None)
    if stamp_line:
        try:
            generated_at = datetime.strptime(
                stamp_line.split("on", 1)[1].strip(), "%Y-%m-%d %H:%M:%S"
            )
        except Exception:
            pass

    return ParsedReport(
        scoring=scoring,
        win_pct=win_pct,
        luck=luck,
        awards=awards,
        h2h=h2h,
        generated_at=generated_at,
        streaks=streaks,
    )


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def _bar_chart(
    pairs: List[Tuple[str, float]],
    title: str,
    color: str,
    xlabel: str,
) -> str:
    names = [p[0] for p in pairs]
    values = [p[1] for p in pairs]

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor(NIGHT_BG)
    ax.set_facecolor(NIGHT_BG)
    bars = ax.barh(names, values, color=color, alpha=0.85)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444")
    ax.spines["bottom"].set_color("#444")
    ax.tick_params(colors="#cbd5e1", labelsize=10)
    ax.set_title(title, color="white", fontsize=16, pad=12, loc="left")
    ax.set_xlabel(xlabel, color="#cbd5e1")

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + (max(values) * 0.01),
            bar.get_y() + bar.get_height() / 2,
            f"{val:,.2f}",
            va="center",
            ha="left",
            color="white",
            fontsize=9,
        )

    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=240, bbox_inches="tight", facecolor=NIGHT_BG)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------


def rivalry_callouts(h2h: HeadToHead) -> List[str]:
    callouts: List[str] = []
    derek_vs_kilian = h2h.record("Derek Topper", "Kilian Nelson")
    if derek_vs_kilian:
        callouts.append(
            f"Derek is 0-{derek_vs_kilian.wins} lifetime vs Kilian (who is undefeated at {derek_vs_kilian.wins}-0)."
        )

    jack_vs_veronica = h2h.record("Jack Gilmore", "Veronica Agne")
    if jack_vs_veronica and jack_vs_veronica.losses > jack_vs_veronica.wins:
        callouts.append(
            f"Jack's only losing matchup is fiancé Veronica: {jack_vs_veronica.label()} (call it pulled punches)."
        )

    kilian_vs_jack = h2h.record("Kilian Nelson", "Jack Gilmore")
    if kilian_vs_jack:
        callouts.append(
            f"Kilian has eaten {kilian_vs_jack.losses} losses to Jack, but hands Derek the sweep every time."
        )

    return callouts


# ---------------------------------------------------------------------------
# Best pick data
# ---------------------------------------------------------------------------


def load_best_pick_data(path: Path = DATA_PATH) -> List[Tuple[str, float, str]]:
    """Return top picks as (label, value_score, owner)."""
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    picks = data.get("best_picks", [])
    results: List[Tuple[str, float, str]] = []
    for pick in picks[:8]:
        label = f"{pick['player']} ({pick['year']}, Rd {pick['round']})"
        results.append((label, float(pick["value_score"]), pick.get("team", "")))
    return results


# ---------------------------------------------------------------------------
# HTML Assembly
# ---------------------------------------------------------------------------


def _html_chart_block(title: str, subtitle: str, image_b64: str) -> str:
    return f"""
    <section class="card">
      <header>
        <p class="eyebrow">{subtitle}</p>
        <h2>{title}</h2>
      </header>
      <img class="chart" src="data:image/png;base64,{image_b64}" alt="{title}">
    </section>
    """


def render_html(report: ParsedReport, output: Path = OUTPUT_HTML) -> Path:
    charts: List[str] = []
    if report.scoring:
        charts.append(
            _html_chart_block(
                "All-Time Points Stack",
                "Jack leads, Derek lurks, Kilian keeps pace",
                _bar_chart(report.scoring, "All-Time Points", PRIMARY_GREEN, "Total points"),
            )
        )
    if report.win_pct:
        charts.append(
            _html_chart_block(
                "Win% Since 2021",
                "Regular season only",
                _bar_chart(report.win_pct, "Win percentage", MINT, "Win %"),
            )
        )
    if report.luck:
        charts.append(
            _html_chart_block(
                "Luck-O-Meter",
                "Lower points against = luckier",
                _bar_chart(report.luck, "Points against", CANDY_RED, "Points against"),
            )
        )

    best_pick_chart = load_best_pick_data()
    if best_pick_chart:
        charts.append(
            _html_chart_block(
                "Draft Heists",
                "Top delta vs round average",
                _bar_chart(best_pick_chart, "Draft value over round mates", GOLD, "Value score"),
            )
        )

    callouts = rivalry_callouts(report.h2h)
    streak_notes = []
    if report.streaks.get("longest_win"):
        streak_notes.append(f"Longest heater: {report.streaks['longest_win']}.")
    if report.streaks.get("longest_loss"):
        streak_notes.append(f"Most painful slide: {report.streaks['longest_loss']}.")

    awards_cards = """
      <div class="pillbox">
        <div class="pill">Scoring Leader: {scoring_leader}</div>
        <div class="pill">Best Record: {best_record}</div>
        <div class="pill">Luckiest: {luckiest}</div>
        <div class="pill">Unluckiest: {unluckiest}</div>
        <div class="pill">Most Injured: {most_injured}</div>
        <div class="pill">MVP Season: {mvp_single}</div>
        <div class="pill">5-Year MVP: {mvp_total}</div>
      </div>
    """.format(
        scoring_leader=report.awards.get("scoring_leader", "?"),
        best_record=report.awards.get("best_record", "?"),
        luckiest=report.awards.get("luckiest", "?"),
        unluckiest=report.awards.get("unluckiest", "?"),
        most_injured=report.awards.get("most_injured", "?"),
        mvp_single=report.awards.get("mvp_single", "?"),
        mvp_total=report.awards.get("mvp_total", "?"),
    )

    insights_html = "".join(f"<li>{item}</li>" for item in callouts + streak_notes)
    charts_html = "".join(charts)

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Amateur Hardcore Fantasy Wrapped</title>
      <style>
        body {{
          margin: 0;
          font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
          background: radial-gradient(circle at 20% 20%, #12202d, #09090f 45%);
          color: #f8fafc;
          padding: 32px 18px 56px;
        }}
        .page {{
          max-width: 1100px;
          margin: 0 auto;
        }}
        header.hero {{
          text-align: left;
          margin-bottom: 28px;
        }}
        header.hero h1 {{
          font-size: 44px;
          margin: 0 0 8px;
          color: {PRIMARY_GREEN};
        }}
        header.hero p {{
          margin: 4px 0;
          color: #cbd5e1;
        }}
        .pillbox {{
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin: 18px 0 24px;
        }}
        .pill {{
          background: rgba(255,255,255,0.06);
          color: #f8fafc;
          padding: 10px 14px;
          border-radius: 999px;
          border: 1px solid rgba(255,255,255,0.12);
          font-size: 14px;
          letter-spacing: 0.3px;
        }}
        .grid {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 18px;
        }}
        .card {{
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 14px;
          padding: 16px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.45);
        }}
        .card h2 {{
          margin: 4px 0 10px;
          font-size: 22px;
          color: #f8fafc;
        }}
        .eyebrow {{
          text-transform: uppercase;
          letter-spacing: 1.1px;
          font-size: 11px;
          color: #94a3b8;
          margin: 0;
        }}
        .chart {{
          width: 100%;
          border-radius: 10px;
          margin-top: 8px;
          background: #0b0b0f;
        }}
        .insights {{
          list-style: disc;
          padding-left: 20px;
          color: #e2e8f0;
          line-height: 1.5;
        }}
        footer {{
          margin-top: 24px;
          color: #94a3b8;
          font-size: 13px;
        }}
      </style>
    </head>
    <body>
      <div class="page">
        <header class="hero">
          <p class="eyebrow">Holiday Finals Edition</p>
          <h1>Amateur Hardcore Fantasy Wrapped</h1>
          <p>Updated {report.generated_at.strftime('%b %d, %Y at %I:%M %p')}. Built for texting, screenshots, and celebratory trash talk.</p>
        </header>

        {awards_cards}

        <section class="card">
          <header>
            <p class="eyebrow">Rivalries & Vibes</p>
            <h2>What the league is actually talking about</h2>
          </header>
          <ul class="insights">{insights_html}</ul>
        </section>

        <div class="grid">{charts_html}</div>

        <footer>Need more? Re-run the generator after the championship and drop the HTML straight into the chat.</footer>
      </div>
    </body>
    </html>
    """

    output.write_text(html, encoding="utf-8")
    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    report = parse_report()
    output = render_html(report)
    print(f"Saved: {output.resolve()}")


if __name__ == "__main__":
    main()
