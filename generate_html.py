#!/usr/bin/env python3
"""
Generate beautiful HTML page for Fantasy Football Wrapped
Inspired by Spotify Wrapped with a Christmas theme
"""

import json
import base64
from pathlib import Path
from datetime import datetime


def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string for embedding."""
    try:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        return None


def generate_html_wrapped(json_path: str = 'fantasy_wrapped_data.json',
                         output_path: str = 'fantasy_wrapped.html'):
    """Generate a beautiful HTML page from the JSON data."""

    # Load JSON data
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_path} not found!")
        return

    # Embed images as base64
    images = {}
    image_files = [
        'total_points.png',
        'win_percentage.png',
        'mvp_panel.png',
        'mvp_5year.png',
        'luck_analysis.png',
        'hall_of_fame.png'
    ]

    for img_file in image_files:
        img_data = image_to_base64(img_file)
        if img_data:
            images[img_file] = img_data

    # Christmas color palette
    colors = {
        'dark_red': '#8B0000',
        'red': '#DC143C',
        'orange': '#FF8C00',
        'green': '#228B22',
        'dark_green': '#0B4F0B',
        'gold': '#FFD700',
        'dark_gold': '#B8860B',
        'white': '#FFFFFF',
        'off_white': '#F5F5DC',
        'silver': '#C0C0C0',
        'dark_bg': '#1a1a1a',
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fantasy Football Wrapped {data.get('league_years', [2021, 2025])[0]}-{data.get('league_years', [2021, 2025])[-1]}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, {colors['dark_bg']} 0%, {colors['dark_red']} 100%);
            color: {colors['white']};
            overflow-x: hidden;
            scroll-behavior: smooth;
        }}

        .section {{
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 60px 20px;
            position: relative;
            opacity: 0;
            animation: fadeInUp 0.8s ease-out forwards;
        }}

        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(40px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .section:nth-child(even) {{
            background: linear-gradient(135deg, {colors['dark_green']} 0%, {colors['green']} 100%);
        }}

        .section:nth-child(odd) {{
            background: linear-gradient(135deg, {colors['dark_red']} 0%, {colors['red']} 100%);
        }}

        .hero {{
            background: linear-gradient(135deg, {colors['dark_bg']} 0%, {colors['dark_red']} 50%, {colors['dark_green']} 100%) !important;
            text-align: center;
        }}

        .hero h1 {{
            font-size: 5rem;
            font-weight: 900;
            margin-bottom: 20px;
            background: linear-gradient(45deg, {colors['gold']}, {colors['white']}, {colors['silver']});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: shimmer 3s ease-in-out infinite;
        }}

        @keyframes shimmer {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}

        .hero h2 {{
            font-size: 2rem;
            color: {colors['off_white']};
            font-weight: 300;
            margin-top: 10px;
        }}

        .container {{
            max-width: 1200px;
            width: 100%;
            margin: 0 auto;
        }}

        .section-title {{
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 40px;
            text-align: center;
            color: {colors['gold']};
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        }}

        .award-card {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            margin: 20px 0;
            border: 2px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .award-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5);
        }}

        .award-title {{
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 15px;
            color: {colors['gold']};
        }}

        .award-winner {{
            font-size: 2.5rem;
            font-weight: 900;
            margin: 20px 0;
            color: {colors['white']};
        }}

        .award-stats {{
            font-size: 1.3rem;
            color: {colors['off_white']};
            line-height: 1.8;
        }}

        .image-container {{
            width: 100%;
            max-width: 1000px;
            margin: 40px auto;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            border: 3px solid {colors['gold']};
        }}

        .image-container img {{
            width: 100%;
            height: auto;
            display: block;
        }}

        .mvp-showcase {{
            display: flex;
            gap: 40px;
            flex-wrap: wrap;
            justify-content: center;
            margin: 40px 0;
        }}

        .mvp-card {{
            flex: 1;
            min-width: 400px;
            max-width: 500px;
            background: linear-gradient(135deg, rgba(255, 215, 0, 0.2) 0%, rgba(255, 255, 255, 0.1) 100%);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            border: 3px solid {colors['gold']};
            text-align: center;
        }}

        .mvp-card.platinum {{
            background: linear-gradient(135deg, rgba(192, 192, 192, 0.3) 0%, rgba(255, 255, 255, 0.1) 100%);
            border-color: {colors['silver']};
        }}

        .rankings-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            overflow: hidden;
        }}

        .rankings-table th {{
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            text-align: left;
            font-weight: 700;
            color: {colors['gold']};
            font-size: 1.1rem;
        }}

        .rankings-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 1rem;
        }}

        .rankings-table tr:hover {{
            background: rgba(255, 255, 255, 0.1);
        }}

        .rank-badge {{
            display: inline-block;
            width: 35px;
            height: 35px;
            line-height: 35px;
            border-radius: 50%;
            background: {colors['white']};
            color: {colors['dark_bg']};
            font-weight: 900;
            text-align: center;
            margin-right: 10px;
        }}

        .rank-badge.gold {{ background: {colors['gold']}; }}
        .rank-badge.silver {{ background: {colors['silver']}; }}
        .rank-badge.bronze {{ background: #CD7F32; }}

        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}

        .stat-box {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            border: 2px solid rgba(255, 255, 255, 0.2);
        }}

        .stat-value {{
            font-size: 2.5rem;
            font-weight: 900;
            color: {colors['gold']};
            margin: 10px 0;
        }}

        .stat-label {{
            font-size: 1rem;
            color: {colors['off_white']};
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .emoji {{
            font-size: 3rem;
            margin-bottom: 15px;
        }}

        .scroll-indicator {{
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 2rem;
            animation: bounce 2s ease-in-out infinite;
            color: {colors['gold']};
        }}

        @keyframes bounce {{
            0%, 100% {{ transform: translateX(-50%) translateY(0); }}
            50% {{ transform: translateX(-50%) translateY(-10px); }}
        }}

        .footer {{
            text-align: center;
            padding: 40px 20px;
            background: {colors['dark_bg']};
            color: {colors['off_white']};
            font-size: 1rem;
        }}

        @media (max-width: 768px) {{
            .hero h1 {{ font-size: 3rem; }}
            .hero h2 {{ font-size: 1.5rem; }}
            .section-title {{ font-size: 2rem; }}
            .award-winner {{ font-size: 1.8rem; }}
            .mvp-card {{ min-width: 100%; }}
        }}
    </style>
</head>
<body>
"""

    # Hero Section
    years = data.get('league_years', [2021, 2025])
    html += f"""
    <section class="section hero">
        <div class="container">
            <h1>🎄 AMATEUR HARD CORE FANTASY WRAPPED 🎄</h1>
            <h2>{years[0]}-{years[-1]} Season</h2>
        </div>
        <div class="scroll-indicator">↓</div>
    </section>
"""

    # Core Awards Section
    core_awards = data.get('core_awards', {})
    if core_awards:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🏆 CORE AWARDS</h2>

            <div class="award-card">
                <div class="emoji">📈</div>
                <div class="award-title">ALL-TIME SCORING LEADER</div>
                <div class="award-winner">{core_awards.get('scoring_leader', {}).get('team', 'N/A')}</div>
                <div class="award-stats">
                    {core_awards.get('scoring_leader', {}).get('total_points', 0):.2f} total points
                </div>
            </div>

            <div class="award-card">
                <div class="emoji">😬</div>
                <div class="award-title">UNLUCKIEST MANAGER</div>
                <div class="award-winner">{core_awards.get('unluckiest_manager', {}).get('team', 'N/A')}</div>
                <div class="award-stats">
                    {core_awards.get('unluckiest_manager', {}).get('points_against', 0):.2f} points against
                </div>
            </div>

            <div class="award-card">
                <div class="emoji">🍀</div>
                <div class="award-title">LUCKIEST MANAGER</div>
                <div class="award-winner">{core_awards.get('luckiest_manager', {}).get('team', 'N/A')}</div>
                <div class="award-stats">
                    {core_awards.get('luckiest_manager', {}).get('points_against', 0):.2f} points against
                </div>
            </div>

            <div class="award-card">
                <div class="emoji">🥇</div>
                <div class="award-title">BEST ALL-TIME RECORD</div>
                <div class="award-winner">{core_awards.get('best_record', {}).get('team', 'N/A')}</div>
                <div class="award-stats">
                    {core_awards.get('best_record', {}).get('wins', 0)}-{core_awards.get('best_record', {}).get('losses', 0)}-{core_awards.get('best_record', {}).get('ties', 0)}
                    ({core_awards.get('best_record', {}).get('win_percentage', 0):.1f}%)
                </div>
            </div>
        </div>
    </section>
"""

    # Total Points Visualization
    if 'total_points.png' in images:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">📊 ALL-TIME SCORING RANKINGS</h2>
            <div class="image-container">
                <img src="data:image/png;base64,{images['total_points.png']}" alt="Total Points">
            </div>
        </div>
    </section>
"""

    # Win Percentage Visualization
    if 'win_percentage.png' in images:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🏅 WIN PERCENTAGE RANKINGS</h2>
            <div class="image-container">
                <img src="data:image/png;base64,{images['win_percentage.png']}" alt="Win Percentage">
            </div>
        </div>
    </section>
"""

    # MVP Showcases
    player_analysis = data.get('player_analysis', {})
    mvp_single = player_analysis.get('mvp_single_season', {})
    mvp_5year = player_analysis.get('mvp_5year_total_vor', {})

    html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🌟 MOST VALUABLE PLAYERS</h2>
            <div class="mvp-showcase">
"""

    # Single Season MVP
    if mvp_single and 'mvp_panel.png' in images:
        html += f"""
                <div class="mvp-card">
                    <div class="emoji">🏅</div>
                    <h3 style="color: {colors['gold']}; font-size: 1.5rem; margin-bottom: 20px;">SINGLE-SEASON MVP</h3>
                    <div class="image-container" style="max-width: 400px;">
                        <img src="data:image/png;base64,{images['mvp_panel.png']}" alt="Single Season MVP">
                    </div>
                    <div style="margin-top: 20px;">
                        <div class="award-winner">{mvp_single.get('player', 'N/A')}</div>
                        <div class="award-stats">
                            {mvp_single.get('year', 'N/A')} • {mvp_single.get('position', 'N/A')}<br>
                            VOR: {mvp_single.get('vor', 0):.1f} • Points: {mvp_single.get('points', 0):.1f}
                        </div>
                    </div>
                </div>
"""

    # 5-Year MVP
    if mvp_5year and 'mvp_5year.png' in images:
        years_str = ', '.join(str(y) for y in mvp_5year.get('years', []))
        html += f"""
                <div class="mvp-card platinum">
                    <div class="emoji">🏆</div>
                    <h3 style="color: {colors['silver']}; font-size: 1.5rem; margin-bottom: 20px;">5-YEAR TOTAL VOR MVP</h3>
                    <div class="image-container" style="max-width: 400px;">
                        <img src="data:image/png;base64,{images['mvp_5year.png']}" alt="5-Year MVP">
                    </div>
                    <div style="margin-top: 20px;">
                        <div class="award-winner">{mvp_5year.get('player', 'N/A')}</div>
                        <div class="award-stats">
                            {mvp_5year.get('seasons_played', 0)} Seasons ({years_str})<br>
                            Total VOR: {mvp_5year.get('total_vor', 0):.1f} • Avg: {mvp_5year.get('avg_vor', 0):.1f}
                        </div>
                    </div>
                </div>
"""

    html += """
            </div>
        </div>
    </section>
"""

    # Hall of Fame
    if 'hall_of_fame.png' in images:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🏛️ HALL OF FAME</h2>
            <p style="text-align: center; font-size: 1.3rem; margin-bottom: 30px; color: {colors['off_white']};">
                Top 10 Most Valuable Player Seasons
            </p>
            <div class="image-container">
                <img src="data:image/png;base64,{images['hall_of_fame.png']}" alt="Hall of Fame">
            </div>
        </div>
    </section>
"""

    # Weekly Awards
    weekly_awards = data.get('weekly_awards', {})
    if weekly_awards:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">⚡ WEEKLY AWARDS</h2>
"""

        explosion = weekly_awards.get('offensive_explosion', {})
        if explosion:
            html += f"""
            <div class="award-card">
                <div class="emoji">💥</div>
                <div class="award-title">OFFENSIVE EXPLOSION</div>
                <div class="award-winner">{explosion.get('manager', 'N/A')}</div>
                <div class="award-stats">
                    {explosion.get('score', 0):.2f} points in {explosion.get('year', 'N/A')} Week {explosion.get('week', 'N/A')}<br>
                    vs {explosion.get('opponent', 'N/A')} ({explosion.get('opponent_score', 0):.2f})
                </div>
            </div>
"""

        dud = weekly_awards.get('offensive_dud', {})
        if dud:
            html += f"""
            <div class="award-card">
                <div class="emoji">💀</div>
                <div class="award-title">OFFENSIVE DUD</div>
                <div class="award-winner">{dud.get('manager', 'N/A')}</div>
                <div class="award-stats">
                    {dud.get('score', 0):.2f} points in {dud.get('year', 'N/A')} Week {dud.get('week', 'N/A')}<br>
                    vs {dud.get('opponent', 'N/A')} ({dud.get('opponent_score', 0):.2f})
                </div>
            </div>
"""

        heartbreaker = weekly_awards.get('heartbreaker', {})
        if heartbreaker:
            html += f"""
            <div class="award-card">
                <div class="emoji">💔</div>
                <div class="award-title">HEARTBREAKER</div>
                <div class="award-winner">{heartbreaker.get('manager', 'N/A')}</div>
                <div class="award-stats">
                    {heartbreaker.get('count', 0)} losses by less than 5 points
                </div>
            </div>
"""

        bad_beat = weekly_awards.get('bad_beat', {})
        if bad_beat:
            html += f"""
            <div class="award-card">
                <div class="emoji">🎰</div>
                <div class="award-title">BAD BEAT</div>
                <div class="award-winner">{bad_beat.get('manager', 'N/A')}</div>
                <div class="award-stats">
                    2nd highest score ({bad_beat.get('score', 0):.2f}) but still lost<br>
                    {bad_beat.get('year', 'N/A')} Week {bad_beat.get('week', 'N/A')} vs {bad_beat.get('opponent', 'N/A')}
                </div>
            </div>
"""

        html += """
        </div>
    </section>
"""

    # Streaks
    streaks = data.get('streaks', {})
    if streaks:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🔥 STREAKS</h2>
"""

        win_streak = streaks.get('longest_win_streak', {})
        if win_streak:
            html += f"""
            <div class="award-card">
                <div class="emoji">🔥</div>
                <div class="award-title">LONGEST WIN STREAK</div>
                <div class="award-winner">{win_streak.get('manager', 'N/A')}</div>
                <div class="award-stats">
                    {win_streak.get('count', 0)} wins in a row<br>
                    {win_streak.get('start_year', 'N/A')} Week {win_streak.get('start_week', 'N/A')} -
                    {win_streak.get('end_year', 'N/A')} Week {win_streak.get('end_week', 'N/A')}
                </div>
            </div>
"""

        loss_streak = streaks.get('longest_loss_streak', {})
        if loss_streak:
            html += f"""
            <div class="award-card">
                <div class="emoji">😭</div>
                <div class="award-title">LONGEST LOSING STREAK</div>
                <div class="award-winner">{loss_streak.get('manager', 'N/A')}</div>
                <div class="award-stats">
                    {loss_streak.get('count', 0)} losses in a row<br>
                    {loss_streak.get('start_year', 'N/A')} Week {loss_streak.get('start_week', 'N/A')} -
                    {loss_streak.get('end_year', 'N/A')} Week {loss_streak.get('end_week', 'N/A')}
                </div>
            </div>
"""

        html += """
        </div>
    </section>
"""

    # Special Awards
    special_awards = data.get('special_awards', {})
    if special_awards:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">💎 SPECIAL AWARDS</h2>
"""

        late_legend = special_awards.get('late_round_legend', {})
        if late_legend:
            html += f"""
            <div class="award-card">
                <div class="emoji">💎</div>
                <div class="award-title">LATE ROUND LEGEND</div>
                <div class="award-winner">{late_legend.get('player', 'N/A')}</div>
                <div class="award-stats">
                    Drafted by {late_legend.get('manager', 'N/A')} in {late_legend.get('year', 'N/A')}<br>
                    Round {late_legend.get('round', 0)}, Pick {late_legend.get('pick', 0)}<br>
                    VOR: {late_legend.get('vor', 0):.2f}
                </div>
            </div>
"""

        punt_god = special_awards.get('punt_god', {})
        if punt_god:
            breakdown = punt_god.get('breakdown', {})
            html += f"""
            <div class="award-card">
                <div class="emoji">🦵</div>
                <div class="award-title">PUNT GOD</div>
                <div class="award-winner">{punt_god.get('team', 'N/A')}</div>
                <div class="award-stats">
                    {punt_god.get('total_points', 0):.2f} total special teams points<br>
                    D/ST: {breakdown.get('D/ST', 0):.2f} •
                    K: {breakdown.get('K', 0):.2f} •
                    P: {breakdown.get('P', 0):.2f}
                </div>
            </div>
"""

        html += """
        </div>
    </section>
"""

    # Luck Analysis
    if 'luck_analysis.png' in images:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🎲 LUCK ANALYSIS</h2>
            <p style="text-align: center; font-size: 1.3rem; margin-bottom: 30px; color: {colors['off_white']};">
                Points For vs Points Against
            </p>
            <div class="image-container">
                <img src="data:image/png;base64,{images['luck_analysis.png']}" alt="Luck Analysis">
            </div>
        </div>
    </section>
"""

    # Injury Analysis
    injury_analysis = data.get('injury_analysis', {})
    if injury_analysis:
        most_injured = injury_analysis.get('most_injured_team', {})
        if most_injured:
            html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🩺 INJURY ANALYSIS</h2>

            <div class="award-card">
                <div class="emoji">🤒</div>
                <div class="award-title">MOST INJURED TEAM</div>
                <div class="award-winner">{most_injured.get('team', 'N/A')}</div>
                <div class="award-stats">
                    {most_injured.get('total_injury_weeks', 0)} total injury-weeks<br>
                    Worst single week: {most_injured.get('max_injuries_single_week', 0)} injuries
"""
            frequent_flyer = most_injured.get('frequent_flyer')
            if frequent_flyer:
                html += f"""<br>
                    Frequent Flyer: {frequent_flyer.get('player', 'N/A')} ({frequent_flyer.get('injury_weeks', 0)} injury-weeks)
"""
            html += """
                </div>
            </div>
        </div>
    </section>
"""

    # Draft Analysis
    draft_analysis = data.get('draft_analysis', {})
    if draft_analysis:
        best_picks = draft_analysis.get('best_picks_all_time', [])
        if best_picks:
            html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🎯 BEST DRAFT PICKS</h2>
            <p style="text-align: center; font-size: 1.2rem; margin-bottom: 30px; color: {colors['off_white']};">
                Top 10 All-Time (by Δ vs Round Average)
            </p>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Player</th>
                        <th>Year</th>
                        <th>Round</th>
                        <th>VOR</th>
                        <th>Δ vs Round</th>
                        <th>Team</th>
                    </tr>
                </thead>
                <tbody>
"""
            for i, pick in enumerate(best_picks[:10], 1):
                badge_class = 'gold' if i == 1 else ('silver' if i == 2 else ('bronze' if i == 3 else ''))
                html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{i}</span></td>
                        <td style="font-weight: 700;">{pick.get('player', 'N/A')}</td>
                        <td>{pick.get('year', 'N/A')}</td>
                        <td>Rd {pick.get('round', 0)}</td>
                        <td>{pick.get('vor', 0):.1f}</td>
                        <td style="color: {colors['gold']}; font-weight: 700;">+{pick.get('value_score', 0):.1f}</td>
                        <td>{pick.get('team', 'N/A')}</td>
                    </tr>
"""
            html += """
                </tbody>
            </table>
        </div>
    </section>
"""

    # Full Rankings Section
    rankings = data.get('rankings', {})

    # Scoring Rankings
    scoring_rankings = rankings.get('scoring', [])
    if scoring_rankings:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">📊 COMPLETE SCORING RANKINGS</h2>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Total Points</th>
                    </tr>
                </thead>
                <tbody>
"""
        for entry in scoring_rankings:
            badge_class = 'gold' if entry['rank'] == 1 else ('silver' if entry['rank'] == 2 else ('bronze' if entry['rank'] == 3 else ''))
            html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{entry['rank']}</span></td>
                        <td style="font-weight: 700;">{entry['team']}</td>
                        <td>{entry['total_points']:.2f}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
    </section>
"""

    # Win Percentage Rankings
    win_pct_rankings = rankings.get('win_percentage', [])
    if win_pct_rankings:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🏅 COMPLETE WIN PERCENTAGE RANKINGS</h2>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Record</th>
                        <th>Win %</th>
                    </tr>
                </thead>
                <tbody>
"""
        for entry in win_pct_rankings:
            badge_class = 'gold' if entry['rank'] == 1 else ('silver' if entry['rank'] == 2 else ('bronze' if entry['rank'] == 3 else ''))
            html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{entry['rank']}</span></td>
                        <td style="font-weight: 700;">{entry['team']}</td>
                        <td>{entry['wins']}-{entry['losses']}-{entry['ties']}</td>
                        <td style="color: {colors['gold']}; font-weight: 700;">{entry['win_percentage']:.1f}%</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
    </section>
"""

    # Luck Rankings
    luck_rankings = rankings.get('luck', [])
    if luck_rankings:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🍀 COMPLETE LUCK RANKINGS</h2>
            <p style="text-align: center; font-size: 1.2rem; margin-bottom: 30px; color: {colors['off_white']};">
                Points Against (Lower = Luckier)
            </p>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Points Against</th>
                    </tr>
                </thead>
                <tbody>
"""
        for entry in luck_rankings:
            badge_class = 'gold' if entry['rank'] == 1 else ('silver' if entry['rank'] == 2 else ('bronze' if entry['rank'] == 3 else ''))
            html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{entry['rank']}</span></td>
                        <td style="font-weight: 700;">{entry['team']}</td>
                        <td>{entry['points_against']:.2f}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
    </section>
"""

    # Top 10 5-Year Total VOR
    player_analysis = data.get('player_analysis', {})
    top_5year_vor = player_analysis.get('top_5_year_total_vor', [])
    if top_5year_vor:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">⭐ TOP 10 PLAYERS (5-Year Total VOR)</h2>
            <p style="text-align: center; font-size: 1.2rem; margin-bottom: 30px; color: {colors['off_white']};">
                Most Valuable Players Across All Seasons
            </p>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Player</th>
                        <th>Position</th>
                        <th>Total VOR</th>
                        <th>Avg VOR</th>
                        <th>Seasons</th>
                    </tr>
                </thead>
                <tbody>
"""
        for i, player in enumerate(top_5year_vor, 1):
            badge_class = 'gold' if i == 1 else ('silver' if i == 2 else ('bronze' if i == 3 else ''))
            html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{i}</span></td>
                        <td style="font-weight: 700;">{player.get('player', 'N/A')}</td>
                        <td>{player.get('position', 'N/A')}</td>
                        <td style="color: {colors['gold']}; font-weight: 700;">{player.get('total_vor', 0):.1f}</td>
                        <td>{player.get('avg_vor', 0):.1f}</td>
                        <td>{player.get('seasons_played', 0)}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
    </section>
"""

    # Top 10 5-Year Average VOR
    top_5year_avg_vor = player_analysis.get('top_5_year_avg_vor', [])
    if top_5year_avg_vor:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">💫 TOP 10 PLAYERS (5-Year Average VOR)</h2>
            <p style="text-align: center; font-size: 1.2rem; margin-bottom: 30px; color: {colors['off_white']};">
                Most Consistent Elite Performers (Min. 2 Seasons)
            </p>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Player</th>
                        <th>Position</th>
                        <th>Avg VOR</th>
                        <th>Total VOR</th>
                        <th>Seasons</th>
                    </tr>
                </thead>
                <tbody>
"""
        for i, player in enumerate(top_5year_avg_vor, 1):
            badge_class = 'gold' if i == 1 else ('silver' if i == 2 else ('bronze' if i == 3 else ''))
            html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{i}</span></td>
                        <td style="font-weight: 700;">{player.get('player', 'N/A')}</td>
                        <td>{player.get('position', 'N/A')}</td>
                        <td style="color: {colors['gold']}; font-weight: 700;">{player.get('avg_vor', 0):.1f}</td>
                        <td>{player.get('total_vor', 0):.1f}</td>
                        <td>{player.get('seasons_played', 0)}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
    </section>
"""

    # Nemesis and Victims
    h2h_data = data.get('head_to_head', {})
    nemesis_and_victims = h2h_data.get('nemesis_and_victims', {})
    if nemesis_and_victims:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">⚔️ NEMESIS & VICTIMS</h2>
            <p style="text-align: center; font-size: 1.2rem; margin-bottom: 30px; color: {colors['off_white']};">
                Who owns who in head-to-head matchups?
            </p>
"""
        for manager in sorted(nemesis_and_victims.keys()):
            data_entry = nemesis_and_victims[manager]
            nemesis = data_entry.get('nemesis')
            victim = data_entry.get('victim')

            html += f"""
            <div class="award-card">
                <h3 style="color: {colors['gold']}; font-size: 1.5rem; margin-bottom: 20px;">{manager}</h3>
"""
            if nemesis:
                html += f"""
                <div style="margin-bottom: 15px;">
                    <div style="font-size: 1.2rem; font-weight: 700; color: {colors['orange']};">👿 Nemesis: {nemesis.get('opponent', 'N/A')}</div>
                    <div class="award-stats">
                        They scored {nemesis.get('avg_points_against', 0):.1f} pts/game vs you
                        ({nemesis.get('total_points_against', 0):.1f} total, {nemesis.get('games', 0)} games)<br>
                        Your record: {nemesis.get('record', 'N/A')}
                    </div>
                </div>
"""
            if victim:
                html += f"""
                <div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: {colors['green']};">🏹 Victim: {victim.get('opponent', 'N/A')}</div>
                    <div class="award-stats">
                        You scored {victim.get('avg_points_for', 0):.1f} pts/game vs them
                        ({victim.get('total_points_for', 0):.1f} total, {victim.get('games', 0)} games)<br>
                        Your record: {victim.get('record', 'N/A')}
                    </div>
                </div>
"""
            html += """
            </div>
"""
        html += """
        </div>
    </section>
"""

    # Head-to-Head Matrix
    h2h_stats = h2h_data.get('h2h_stats', {})
    if h2h_stats:
        all_managers = sorted(set(h2h_stats.keys()))
        if all_managers:
            html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">📊 HEAD-TO-HEAD RECORDS MATRIX</h2>
            <p style="text-align: center; font-size: 1.2rem; margin-bottom: 30px; color: {colors['off_white']};">
                All-Time Win-Loss-Tie Records
            </p>
            <div style="overflow-x: auto;">
                <table class="rankings-table" style="min-width: 800px;">
                    <thead>
                        <tr>
                            <th>Team</th>
"""
            for manager in all_managers:
                # Abbreviate manager names for column headers
                parts = manager.split()
                if len(parts) >= 2:
                    abbrev = f"{parts[0][0]}{parts[-1][:2]}"
                else:
                    abbrev = manager[:3]
                html += f"""                            <th style="text-align: center;">{abbrev}</th>
"""
            html += """                        </tr>
                    </thead>
                    <tbody>
"""
            for i, manager_a in enumerate(all_managers):
                html += f"""                        <tr>
                            <td style="font-weight: 700;">{manager_a}</td>
"""
                for j, manager_b in enumerate(all_managers):
                    if manager_a == manager_b:
                        html += """                            <td style="text-align: center; color: #888;">--</td>
"""
                    else:
                        stats = h2h_stats.get(manager_a, {}).get(manager_b, {})
                        wins = stats.get('wins', 0)
                        losses = stats.get('losses', 0)
                        ties = stats.get('ties', 0)
                        record = f"{wins}-{losses}"
                        if ties > 0:
                            record += f"-{ties}"

                        # Color code based on winning record
                        if wins > losses:
                            cell_color = colors['green']
                        elif wins < losses:
                            cell_color = colors['orange']
                        else:
                            cell_color = colors['off_white']

                        html += f"""                            <td style="text-align: center; color: {cell_color}; font-weight: 700;">{record}</td>
"""
                html += """                        </tr>
"""
            html += """                    </tbody>
                </table>
            </div>
            <p style="text-align: center; font-size: 0.9rem; margin-top: 20px; color: {colors['off_white']};">
                Records shown as W-L or W-L-T (Wins-Losses-Ties)
            </p>
        </div>
    </section>
"""

    # Full Injury Rankings
    injury_rankings = injury_analysis.get('rankings', [])
    if injury_rankings:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🤕 COMPLETE INJURY RANKINGS</h2>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Total Injury-Weeks</th>
                        <th>Max in One Week</th>
                    </tr>
                </thead>
                <tbody>
"""
        for entry in injury_rankings:
            badge_class = 'gold' if entry['rank'] == 1 else ('silver' if entry['rank'] == 2 else ('bronze' if entry['rank'] == 3 else ''))
            html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{entry['rank']}</span></td>
                        <td style="font-weight: 700;">{entry['team']}</td>
                        <td>{entry['injury_weeks']}</td>
                        <td>{entry['max_injuries_single_week']}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
    </section>
"""

    # Weighted Injury Impact
    weighted_injury = injury_analysis.get('weighted_impact', [])
    if weighted_injury:
        html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">💸 WEIGHTED INJURY IMPACT</h2>
            <p style="text-align: center; font-size: 1.2rem; margin-bottom: 30px; color: {colors['off_white']};">
                Draft Capital Weighted (Losing a 1st rounder hurts more)
            </p>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Weighted Score</th>
                    </tr>
                </thead>
                <tbody>
"""
        for entry in weighted_injury:
            badge_class = 'gold' if entry['rank'] == 1 else ('silver' if entry['rank'] == 2 else ('bronze' if entry['rank'] == 3 else ''))
            html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{entry['rank']}</span></td>
                        <td style="font-weight: 700;">{entry['team']}</td>
                        <td>{entry['weighted_score']:.0f}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
    </section>
"""

    # Keeper Value Rankings
    if draft_analysis:
        keeper_rankings = draft_analysis.get('keeper_value_rankings', [])
        if keeper_rankings:
            html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">📈 MOST VALUE FROM KEEPERS</h2>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Total Keeper VOR</th>
                    </tr>
                </thead>
                <tbody>
"""
            for entry in keeper_rankings:
                badge_class = 'gold' if entry['rank'] == 1 else ('silver' if entry['rank'] == 2 else ('bronze' if entry['rank'] == 3 else ''))
                html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{entry['rank']}</span></td>
                        <td style="font-weight: 700;">{entry['team']}</td>
                        <td style="color: {colors['gold']}; font-weight: 700;">{entry['total_keeper_vor']:.2f}</td>
                    </tr>
"""
            html += """
                </tbody>
            </table>
        </div>
    </section>
"""

        # Draft Pick Value Rankings
        draft_pick_rankings = draft_analysis.get('draft_pick_value_rankings', [])
        if draft_pick_rankings:
            html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">📊 MOST VALUE FROM DRAFT PICKS</h2>
            <p style="text-align: center; font-size: 1.2rem; margin-bottom: 30px; color: {colors['off_white']};">
                Non-Keepers, 2022-2025
            </p>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Total Draft Pick VOR</th>
                    </tr>
                </thead>
                <tbody>
"""
            for entry in draft_pick_rankings:
                badge_class = 'gold' if entry['rank'] == 1 else ('silver' if entry['rank'] == 2 else ('bronze' if entry['rank'] == 3 else ''))
                html += f"""
                    <tr>
                        <td><span class="rank-badge {badge_class}">{entry['rank']}</span></td>
                        <td style="font-weight: 700;">{entry['team']}</td>
                        <td style="color: {colors['gold']}; font-weight: 700;">{entry['total_draft_pick_vor']:.2f}</td>
                    </tr>
"""
            html += """
                </tbody>
            </table>
        </div>
    </section>
"""

        # Best Draft Pick By Year
        best_pick_by_year = draft_analysis.get('best_pick_by_year', [])
        if best_pick_by_year:
            html += f"""
    <section class="section">
        <div class="container">
            <h2 class="section-title">🎯 BEST DRAFT PICK BY YEAR</h2>
            <table class="rankings-table">
                <thead>
                    <tr>
                        <th>Year</th>
                        <th>Player</th>
                        <th>Round</th>
                        <th>VOR</th>
                        <th>Δ vs Round</th>
                        <th>Seasons</th>
                        <th>Team</th>
                    </tr>
                </thead>
                <tbody>
"""
            for entry in best_pick_by_year:
                html += f"""
                    <tr>
                        <td style="font-weight: 700; color: {colors['gold']};">{entry['year']}</td>
                        <td style="font-weight: 700;">{entry['player']}</td>
                        <td>Rd {entry['round']}</td>
                        <td>{entry['vor']:.1f}</td>
                        <td style="color: {colors['gold']}; font-weight: 700;">+{entry['delta_vs_round']:.1f}</td>
                        <td>{entry['seasons_contributing']}</td>
                        <td>{entry['team']}</td>
                    </tr>
"""
            html += """
                </tbody>
            </table>
        </div>
    </section>
"""

    # Footer
    html += f"""
    <div class="footer">
        <p>🎄 Happy Holidays & Better Luck Next Season! 🎄</p>
    </div>

    <script>
        // Smooth scroll reveal animation
        const sections = document.querySelectorAll('.section');
        const observerOptions = {{
            threshold: 0.2,
            rootMargin: '0px 0px -100px 0px'
        }};

        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.style.animation = 'fadeInUp 0.8s ease-out forwards';
                }}
            }});
        }}, observerOptions);

        sections.forEach(section => {{
            observer.observe(section);
        }});

        // Hide scroll indicator after first scroll
        let scrolled = false;
        window.addEventListener('scroll', () => {{
            if (!scrolled && window.scrollY > 100) {{
                document.querySelector('.scroll-indicator').style.opacity = '0';
                scrolled = true;
            }}
        }});
    </script>
</body>
</html>
"""

    # Write HTML file
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML page generated: {output_path}")


if __name__ == '__main__':
    generate_html_wrapped()
