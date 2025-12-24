#!/usr/bin/env python3
"""
ESPN Fantasy Football Wrapped
A "Spotify Wrapped" style summary tool for ESPN Fantasy Football leagues
"""

from __future__ import annotations

import json
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Tuple, Any
import warnings

warnings.filterwarnings('ignore')

try:
    from espn_api.football import League
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import pandas as pd
    import numpy as np
    from PIL import Image
    import requests
    from io import BytesIO
except ImportError as e:
    print(f"Error: Missing required package. Please run: pip install -r requirements.txt")
    print(f"Details: {e}")
    exit(1)

# ========================================
# CONFIGURATION
# ========================================

LEAGUE_ID = 778135041
YEARS = [2021, 2022, 2023, 2024, 2025]
ESPN_S2 = "AECZk7m5ZiOXfGwzOnbj7p3EoalPIV2RCeA%2BjgMiZfLTu731Pjk1h%2FkbHIVTCJ7QD0vd4XlZ%2FVezppPxysurKT6DFjtS2U6hF5XJUmHcjvHewmCbPaWv1YNI0FpLdBEADn3N1xKN9ert4%2BA9pljrcO3v9zrPV9h0h7u9%2ByCKJDEYxAoZjIWQTHD2qHdY4EOhi%2F0Y8iZYlrMp1BRmI8HDmYcZjtUwXTL%2Bx3H70FZtE1bfXPyqxs1n5zgFc0X7tRu3I2GfdTazuworr3VflODY9fVi8Hsf9ttxlat1slyF5zBGng%3D%3D"
SWID = "{CFD648CA-1223-407F-8E12-A5F773A4C738}"

# Position-specific thresholds for "startable" players (for value over replacement)
STARTABLE_THRESHOLDS = {
    'QB': 25,  # Top 25 QBs
    'RB': 40,  # Top 40 RBs
    'WR': 50,  # Top 50 WRs
    'TE': 15,  # Top 15 TEs
    'D/ST': 15,  # Top 15 Defenses
    'K': 15,   # Top 15 Kickers
}

INJURY_STATUSES = ['OUT', 'IR', 'DOUBTFUL', 'SUSPENDED']

# ========================================
# DATA EXTRACTION
# ========================================

def load_league_data(year: int) -> League:
    """Load league data for a specific year."""
    print(f"Loading {year} season data...")
    try:
        league = League(
            league_id=LEAGUE_ID,
            year=year,
            espn_s2=ESPN_S2,
            swid=SWID
        )
        return league
    except Exception as e:
        print(f"Error loading {year} data: {e}")
        return None


def get_owner_name(team):
    """Safely extract owner name from team object."""
    # Handle both 'owner' (old API) and 'owners' (new API)
    if hasattr(team, 'owner'):
        return team.owner
    elif hasattr(team, 'owners'):
        owners = team.owners
        # owners might be a list or a string
        if isinstance(owners, list):
            return owners[0] if owners else 'Unknown'
        return owners
    return 'Unknown'


def extract_all_data():
    """Extract all relevant data from all seasons."""
    all_data = {
        'leagues': {},
        'team_stats': defaultdict(lambda: {
            'total_points_for': 0,
            'total_points_against': 0,
            'wins': 0,
            'losses': 0,
            'ties': 0,
            'weekly_scores': [],
            'injury_weeks': 0,
            'max_injuries_single_week': 0,
            'injured_players': Counter(),
            'seasons_played': 0,
            'championships': 0,
            'playoff_appearances': 0,
            'keeper_points': defaultdict(float),  # year -> points from keepers
            'draft_points': defaultdict(float),   # year -> points from draft picks
            'keeper_picks': defaultdict(list),    # year -> list of keeper picks
            'draft_picks': defaultdict(list),     # year -> list of draft picks
        }),
        'matchups': [],
        'player_seasons': defaultdict(lambda: defaultdict(float)),  # player -> year -> points
        'draft_data': defaultdict(dict),  # year -> draft info
    }

    for year in YEARS:
        league = load_league_data(year)
        if not league:
            continue

        all_data['leagues'][year] = league

        # Process each team
        for team in league.teams:
            team_name = team.team_name
            owner_name = get_owner_name(team)

            # Use owner name as primary identifier (more stable than team name)
            identifier = f"{owner_name}"

            stats = all_data['team_stats'][identifier]
            stats['seasons_played'] += 1
            stats['wins'] += team.wins
            stats['losses'] += team.losses
            stats['ties'] += team.ties
            stats['total_points_for'] += team.points_for
            stats['total_points_against'] += team.points_against

            # Track team names (they might change)
            if 'team_names' not in stats:
                stats['team_names'] = set()
            stats['team_names'].add(team_name)
            stats['current_team_name'] = team_name

            # Championship tracking
            if hasattr(team, 'final_standing'):
                if team.final_standing == 1:
                    stats['championships'] += 1
                if team.final_standing <= 4:  # Assuming 4 teams make playoffs
                    stats['playoff_appearances'] += 1

        # Process weekly matchups
        try:
            for week in range(1, league.settings.reg_season_count + 1):
                try:
                    box_scores = league.box_scores(week)
                    for matchup in box_scores:
                        if matchup.home_team and matchup.away_team:
                            home_owner = get_owner_name(matchup.home_team)
                            away_owner = get_owner_name(matchup.away_team)

                            # Record matchup
                            all_data['matchups'].append({
                                'year': year,
                                'week': week,
                                'home_team': home_owner,
                                'away_team': away_owner,
                                'home_score': matchup.home_score,
                                'away_score': matchup.away_score,
                            })

                            # Track weekly scores
                            all_data['team_stats'][home_owner]['weekly_scores'].append(matchup.home_score)
                            all_data['team_stats'][away_owner]['weekly_scores'].append(matchup.away_score)

                            # Injury tracking
                            home_injuries = count_injuries(matchup.home_lineup)
                            away_injuries = count_injuries(matchup.away_lineup)

                            all_data['team_stats'][home_owner]['injury_weeks'] += home_injuries['count']
                            all_data['team_stats'][away_owner]['injury_weeks'] += away_injuries['count']

                            if home_injuries['count'] > all_data['team_stats'][home_owner]['max_injuries_single_week']:
                                all_data['team_stats'][home_owner]['max_injuries_single_week'] = home_injuries['count']

                            if away_injuries['count'] > all_data['team_stats'][away_owner]['max_injuries_single_week']:
                                all_data['team_stats'][away_owner]['max_injuries_single_week'] = away_injuries['count']

                            all_data['team_stats'][home_owner]['injured_players'].update(home_injuries['players'])
                            all_data['team_stats'][away_owner]['injured_players'].update(away_injuries['players'])

                except Exception as e:
                    print(f"  Warning: Could not load week {week} for {year}: {e}")
                    continue
        except Exception as e:
            print(f"  Warning: Could not process matchups for {year}: {e}")

        # Process player data and draft info
        try:
            process_player_data(league, year, all_data)
        except Exception as e:
            print(f"  Warning: Could not process player data for {year}: {e}")

    return all_data


def count_injuries(lineup: List) -> Dict:
    """Count injured players in a lineup."""
    injury_count = 0
    injured_players = []

    for player in lineup:
        if hasattr(player, 'injuryStatus') and player.injuryStatus in INJURY_STATUSES:
            injury_count += 1
            if hasattr(player, 'name'):
                player_name = player.name
                # Handle case where name might be a dict or other non-string type
                if isinstance(player_name, dict):
                    # Try to extract a string representation
                    player_name = player_name.get('fullName') or player_name.get('name') or str(player_name)
                elif not isinstance(player_name, str):
                    player_name = str(player_name)
                injured_players.append(player_name)

    return {
        'count': injury_count,
        'players': injured_players
    }


def process_player_data(league: League, year: int, all_data: Dict):
    """Process player scoring data for value calculations."""
    # Collect all player season stats
    for team in league.teams:
        owner = get_owner_name(team)

        # Get roster for the season
        if hasattr(team, 'roster'):
            for player in team.roster:
                if hasattr(player, 'name') and hasattr(player, 'total_points'):
                    player_name = player.name

                    # Handle case where name might be a dict or other non-string type
                    if isinstance(player_name, dict):
                        player_name = player_name.get('fullName') or player_name.get('name') or str(player_name)
                    elif not isinstance(player_name, str):
                        player_name = str(player_name)

                    position = getattr(player, 'position', 'UNKNOWN')
                    points = player.total_points

                    # Store player season stats (including player ID for headshots)
                    player_id = getattr(player, 'playerId', None)
                    all_data['player_seasons'][player_name][year] = {
                        'points': points,
                        'position': position,
                        'team_owner': owner,
                        'player_id': player_id
                    }

    # Process draft data
    try:
        if hasattr(league, 'draft'):
            draft_picks = league.draft
            all_data['draft_data'][year] = {
                'picks': []
            }

            for pick in draft_picks:
                player_name = getattr(pick, 'playerName', None)

                # Handle case where playerName might be a dict or other non-string type
                if isinstance(player_name, dict):
                    player_name = player_name.get('fullName') or player_name.get('name') or str(player_name)
                elif player_name and not isinstance(player_name, str):
                    player_name = str(player_name)

                pick_info = {
                    'round': getattr(pick, 'round_num', None),
                    'pick': getattr(pick, 'round_pick', None),
                    'overall': getattr(pick, 'overall_pick', None),
                    'player_name': player_name,
                    'team': getattr(pick, 'team', None),
                    'is_keeper': getattr(pick, 'keeper_status', False),
                }
                all_data['draft_data'][year]['picks'].append(pick_info)

                # Track keeper vs draft picks for teams
                if pick.team:
                    owner = get_owner_name(pick.team)
                    if pick_info['is_keeper']:
                        all_data['team_stats'][owner]['keeper_picks'][year].append(pick_info)
                    else:
                        all_data['team_stats'][owner]['draft_picks'][year].append(pick_info)
    except Exception as e:
        print(f"  Could not process draft data for {year}: {e}")


# ========================================
# ANALYSIS FUNCTIONS
# ========================================

def calculate_head_to_head_stats(matchups: List) -> Dict:
    """
    Calculate head-to-head stats including points scored.

    Returns dict with structure:
    {
        manager: {
            opponent: {
                'games': int,
                'points_for': float,
                'points_against': float,
                'wins': int,
                'losses': int,
                'ties': int
            }
        }
    }
    """
    h2h = defaultdict(lambda: defaultdict(lambda: {
        'games': 0,
        'points_for': 0,
        'points_against': 0,
        'wins': 0,
        'losses': 0,
        'ties': 0
    }))

    for matchup in matchups:
        home = matchup['home_team']
        away = matchup['away_team']
        home_score = matchup['home_score']
        away_score = matchup['away_score']

        # Track for home team
        h2h[home][away]['games'] += 1
        h2h[home][away]['points_for'] += home_score
        h2h[home][away]['points_against'] += away_score

        # Track for away team
        h2h[away][home]['games'] += 1
        h2h[away][home]['points_for'] += away_score
        h2h[away][home]['points_against'] += home_score

        # Track wins/losses
        if home_score > away_score:
            h2h[home][away]['wins'] += 1
            h2h[away][home]['losses'] += 1
        elif away_score > home_score:
            h2h[away][home]['wins'] += 1
            h2h[home][away]['losses'] += 1
        else:
            h2h[home][away]['ties'] += 1
            h2h[away][home]['ties'] += 1

    return h2h


def calculate_nemesis_and_victims(h2h_stats: Dict) -> Dict:
    """
    Calculate each manager's nemesis (who crushed them) and victim (who they crushed).

    Returns dict with structure:
    {
        manager: {
            'nemesis': {
                'opponent': str,
                'total_points_against': float,
                'avg_points_against': float,
                'games': int,
                'record': str
            },
            'victim': {
                'opponent': str,
                'total_points_for': float,
                'avg_points_for': float,
                'games': int,
                'record': str
            }
        }
    }
    """
    nemesis_data = {}

    for manager, opponents in h2h_stats.items():
        # Find nemesis (who scored most against this manager)
        nemesis = None
        max_avg_against = 0

        # Find victim (who this manager scored most against)
        victim = None
        max_avg_for = 0

        for opponent, stats in opponents.items():
            if stats['games'] == 0:
                continue

            avg_against = stats['points_against'] / stats['games']
            avg_for = stats['points_for'] / stats['games']

            # Check if this is their nemesis
            if avg_against > max_avg_against:
                max_avg_against = avg_against
                nemesis = {
                    'opponent': opponent,
                    'total_points_against': stats['points_against'],
                    'avg_points_against': avg_against,
                    'games': stats['games'],
                    'record': f"{stats['wins']}-{stats['losses']}-{stats['ties']}"
                }

            # Check if this is their victim
            if avg_for > max_avg_for:
                max_avg_for = avg_for
                victim = {
                    'opponent': opponent,
                    'total_points_for': stats['points_for'],
                    'avg_points_for': avg_for,
                    'games': stats['games'],
                    'record': f"{stats['wins']}-{stats['losses']}-{stats['ties']}"
                }

        nemesis_data[manager] = {
            'nemesis': nemesis,
            'victim': victim
        }

    return nemesis_data


def calculate_value_over_replacement(all_data: Dict) -> Dict:
    """Calculate value over replacement for all players."""
    vor_data = {}

    for year in YEARS:
        if year not in all_data['leagues']:
            continue

        # Collect all player stats by position
        position_stats = defaultdict(list)

        for player_name, seasons in all_data['player_seasons'].items():
            if year in seasons:
                player_info = seasons[year]
                position = player_info['position']
                points = player_info['points']

                # Map position to base position (handle flex designations)
                base_pos = position
                if '/' in position:
                    base_pos = position.split('/')[0]

                if base_pos in STARTABLE_THRESHOLDS:
                    position_stats[base_pos].append({
                        'name': player_name,
                        'points': points,
                        'owner': player_info['team_owner'],
                        'player_id': player_info.get('player_id', None)
                    })

        # Calculate replacement level for each position
        replacement_levels = {}
        for pos, threshold in STARTABLE_THRESHOLDS.items():
            if pos in position_stats and len(position_stats[pos]) > 0:
                # Sort by points
                sorted_players = sorted(position_stats[pos], key=lambda x: x['points'], reverse=True)

                # Replacement level is the threshold-th player
                if len(sorted_players) >= threshold:
                    replacement_points = sorted_players[threshold - 1]['points']
                else:
                    replacement_points = sorted_players[-1]['points']

                replacement_levels[pos] = replacement_points

        # Calculate VOR for each player
        year_vor = {}
        for pos, players in position_stats.items():
            if pos in replacement_levels:
                replacement = replacement_levels[pos]
                for player in players:
                    vor = max(0, player['points'] - replacement)
                    year_vor[player['name']] = {
                        'vor': vor,
                        'points': player['points'],
                        'position': pos,
                        'owner': player['owner'],
                        'player_id': player.get('player_id', None)
                    }

        vor_data[year] = year_vor

    return vor_data


def find_best_draft_picks(all_data: Dict, vor_data: Dict) -> List[Dict]:
    """Find the best draft picks relative to their round peers for each year.

    For every season we calculate the average VOR for each round, then measure each
    pick's delta above that round average (and percentage when possible). The
    function returns the top pick(s) per year based on this round-relative delta.
    """
    best_picks_by_year = []

    for year in YEARS:
        if year not in all_data['draft_data'] or year not in vor_data:
            continue

        draft = all_data['draft_data'][year]
        year_vor = vor_data[year]

        round_vors = defaultdict(list)
        picks_with_vor = []

        # First pass: collect VORs by round to compute averages
        for pick in draft['picks']:
            player_name = pick['player_name']
            if player_name not in year_vor:
                continue

            round_num = pick['round'] if pick['round'] else 1
            round_vors[round_num].append(year_vor[player_name]['vor'])

            picks_with_vor.append({
                'pick': pick,
                'vor': year_vor[player_name]['vor'],
                'points': year_vor[player_name]['points'],
                'round': round_num,
                'is_keeper': pick['is_keeper'],
                'team': get_owner_name(pick['team']) if pick['team'] else 'Unknown',
                'player': player_name,
            })

        if not picks_with_vor:
            continue

        round_avg_vor = {
            rnd: sum(vors) / len(vors)
            for rnd, vors in round_vors.items()
            if vors
        }

        # Second pass: compute deltas and identify the top pick(s) for the year
        year_picks_with_delta = []
        for pick_data in picks_with_vor:
            avg_vor = round_avg_vor.get(pick_data['round'])
            if avg_vor is None:
                continue

            delta = pick_data['vor'] - avg_vor
            pct_delta = (delta / avg_vor) if avg_vor else None

            year_picks_with_delta.append({
                'year': year,
                'player': pick_data['player'],
                'round': pick_data['round'],
                'overall': pick_data['pick'].get('overall'),
                'vor': pick_data['vor'],
                'points': pick_data['points'],
                'is_keeper': pick_data['is_keeper'],
                'team': pick_data['team'],
                'round_avg_vor': avg_vor,
                'round_vor_delta': delta,
                'round_vor_pct_delta': pct_delta,
            })

        if not year_picks_with_delta:
            continue

        best_delta = max(p['round_vor_delta'] for p in year_picks_with_delta)
        best_for_year = [
            p for p in year_picks_with_delta if p['round_vor_delta'] == best_delta
        ]

        # Keep the best pick(s) for the season, sorted by round for readability
        best_picks_by_year.extend(sorted(best_for_year, key=lambda x: x['round']))

    # Sort chronologically for reporting
    best_picks_by_year.sort(key=lambda x: x['year'])

    return best_picks_by_year


def calculate_keeper_value(all_data: Dict, vor_data: Dict) -> Dict[str, float]:
    """Calculate total keeper value for each manager."""
    keeper_values = defaultdict(float)

    for year in YEARS:
        if year not in all_data['draft_data'] or year not in vor_data:
            continue

        draft = all_data['draft_data'][year]
        year_vor = vor_data[year]

        for pick in draft['picks']:
            if pick['is_keeper']:
                player_name = pick['player_name']
                if player_name in year_vor:
                    vor = year_vor[player_name]['vor']
                    if pick['team']:
                        owner = get_owner_name(pick['team'])
                        keeper_values[owner] += vor

    return keeper_values


def calculate_draft_pick_value(all_data: Dict, vor_data: Dict) -> Dict[str, float]:
    """Calculate total non-keeper draft pick value for each manager."""
    draft_values = defaultdict(float)

    for year in YEARS:
        if year not in all_data['draft_data'] or year not in vor_data:
            continue

        # Skip 2021 since that was year 1 (everyone drafted, no keepers to exclude)
        if year == 2021:
            continue

        draft = all_data['draft_data'][year]
        year_vor = vor_data[year]

        for pick in draft['picks']:
            if not pick['is_keeper']:
                player_name = pick['player_name']
                if player_name in year_vor:
                    vor = year_vor[player_name]['vor']
                    if pick['team']:
                        owner = get_owner_name(pick['team'])
                        draft_values[owner] += vor

    return draft_values


def find_most_valuable_player(vor_data: Dict) -> Tuple[str, int, Dict]:
    """Find the single most valuable player across all seasons."""
    max_vor = 0
    mvp = None
    mvp_year = None
    mvp_info = None

    for year, year_vor in vor_data.items():
        for player, data in year_vor.items():
            if data['vor'] > max_vor:
                max_vor = data['vor']
                mvp = player
                mvp_year = year
                mvp_info = data

    return mvp, mvp_year, mvp_info


def calculate_punt_god(all_data: Dict) -> Tuple[str, float, Dict]:
    """
    Calculate the Punt God award - manager with most points from D/ST, K, and P.

    Args:
        all_data: All league data including player_seasons

    Returns:
        Tuple of (manager_name, total_points, position_breakdown)
    """
    special_teams_positions = ['D/ST', 'K', 'P']
    manager_points = defaultdict(lambda: {'total': 0, 'D/ST': 0, 'K': 0, 'P': 0})

    # Aggregate special teams points by manager
    for player_name, seasons in all_data['player_seasons'].items():
        for year, player_data in seasons.items():
            position = player_data.get('position', '')
            points = player_data.get('points', 0)
            owner = player_data.get('team_owner', '')

            # Check if position is one of the special teams positions
            if position in special_teams_positions and owner:
                manager_points[owner]['total'] += points
                manager_points[owner][position] += points

    # Find the Punt God
    if not manager_points:
        return None, 0, {}

    punt_god = max(manager_points.items(), key=lambda x: x[1]['total'])
    manager_name = punt_god[0]
    breakdown = punt_god[1]

    return manager_name, breakdown['total'], breakdown


def calculate_five_year_vor(vor_data: Dict) -> Tuple[List[Dict], List[Dict]]:
    """
    Calculate 5-year VOR totals and averages for all players.

    Args:
        vor_data: VOR data by year

    Returns:
        Tuple of (total_vor_list, average_vor_list) where each is a list of dicts
        containing player, total_vor/avg_vor, seasons_played, years_played, etc.
    """
    player_stats = defaultdict(lambda: {
        'total_vor': 0,
        'seasons_played': 0,
        'years': [],
        'positions': set(),
        'player_id': None
    })

    # Aggregate VOR across all years
    for year, year_vor in vor_data.items():
        for player, data in year_vor.items():
            player_stats[player]['total_vor'] += data['vor']
            player_stats[player]['seasons_played'] += 1
            player_stats[player]['years'].append(year)
            player_stats[player]['positions'].add(data['position'])
            if data.get('player_id') and not player_stats[player]['player_id']:
                player_stats[player]['player_id'] = data['player_id']

    # Calculate totals and averages
    total_vor_list = []
    average_vor_list = []

    for player, stats in player_stats.items():
        total_vor = stats['total_vor']
        seasons = stats['seasons_played']
        avg_vor = total_vor / seasons if seasons > 0 else 0

        # Get primary position (most common)
        position = list(stats['positions'])[0] if stats['positions'] else 'UNKNOWN'

        player_data = {
            'player': player,
            'total_vor': total_vor,
            'avg_vor': avg_vor,
            'seasons_played': seasons,
            'years': sorted(stats['years']),
            'position': position,
            'player_id': stats['player_id']
        }

        total_vor_list.append(player_data)
        average_vor_list.append(player_data)

    # Sort lists
    total_vor_list.sort(key=lambda x: x['total_vor'], reverse=True)
    average_vor_list.sort(key=lambda x: x['avg_vor'], reverse=True)

    return total_vor_list, average_vor_list


def download_player_headshot(player_id: int, player_name: str, save_path: str = None) -> Image:
    """
    Download player headshot from ESPN CDN.

    Args:
        player_id: ESPN player ID
        player_name: Player name (for fallback filename)
        save_path: Optional path to save the image

    Returns:
        PIL Image object or None if download fails
    """
    if not player_id:
        return None

    # ESPN headshot URL pattern
    headshot_url = f"https://a.espncdn.com/i/headshots/nfl/players/full/{player_id}.png"

    try:
        response = requests.get(headshot_url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))

            # Save if path provided
            if save_path:
                img.save(save_path)

            return img
        else:
            return None
    except Exception as e:
        return None


def get_top_player_seasons(vor_data: Dict, limit: int = 10) -> List[Dict]:
    """
    Get the top player seasons ranked by VOR.

    Args:
        vor_data: VOR data by year
        limit: Number of top seasons to return

    Returns:
        List of player season dictionaries with name, year, VOR, etc.
    """
    all_player_seasons = []

    for year, year_vor in vor_data.items():
        for player, data in year_vor.items():
            all_player_seasons.append({
                'player': player,
                'year': year,
                'vor': data['vor'],
                'points': data['points'],
                'position': data['position'],
                'owner': data['owner'],
                'player_id': data.get('player_id', None)
            })

    # Sort by VOR descending
    all_player_seasons.sort(key=lambda x: x['vor'], reverse=True)

    return all_player_seasons[:limit]


def download_top_player_headshots(top_players: List[Dict]) -> Dict[str, Image]:
    """
    Download headshots for a list of top players.

    Args:
        top_players: List of player season dictionaries

    Returns:
        Dictionary mapping player names to Image objects
    """
    headshots = {}

    for player_data in top_players:
        player_name = player_data['player']
        player_id = player_data.get('player_id')

        if player_id and player_name not in headshots:
            img = download_player_headshot(player_id, player_name)
            if img:
                headshots[player_name] = img

    return headshots


# ========================================
# VISUALIZATION
# ========================================

def create_visualizations(all_data: Dict, mvp_name: str = None, mvp_year: int = None,
                         mvp_info: Dict = None, mvp_headshot: Image = None,
                         top_players: List[Dict] = None, player_headshots: Dict[str, Image] = None):
    """Generate all visualization charts including MVP and top player headshots."""
    team_stats = all_data['team_stats']

    # Check if we have any data
    if not team_stats:
        print("\nSkipping visualizations - no data available")
        return

    # Prepare data
    teams = []
    total_points = []
    win_pcts = []
    points_against = []
    championships = []
    playoff_apps = []

    for team, stats in sorted(team_stats.items(), key=lambda x: x[1]['total_points_for'], reverse=True):
        teams.append(team)
        total_points.append(stats['total_points_for'])
        points_against.append(stats['total_points_against'])

        total_games = stats['wins'] + stats['losses'] + stats['ties']
        win_pct = (stats['wins'] + 0.5 * stats['ties']) / total_games if total_games > 0 else 0
        win_pcts.append(win_pct * 100)

        championships.append(stats['championships'])
        playoff_apps.append(stats['playoff_appearances'])

    # Create figure with subplots (3 rows, 3 columns to accommodate Hall of Fame)
    fig = plt.figure(figsize=(20, 16))

    # 1. Total Points Scored (horizontal bar)
    ax1 = plt.subplot(2, 3, 1)
    colors1 = plt.cm.viridis(np.linspace(0.3, 0.9, len(teams)))
    bars1 = ax1.barh(range(len(teams)), total_points, color=colors1)
    ax1.set_yticks(range(len(teams)))
    ax1.set_yticklabels(teams, fontsize=9)
    ax1.set_xlabel('Total Points', fontsize=10, fontweight='bold')
    ax1.set_title('All-Time Points Scored (2021-2025)', fontsize=12, fontweight='bold', pad=10)
    ax1.invert_yaxis()

    # Add value labels
    for i, (bar, val) in enumerate(zip(bars1, total_points)):
        ax1.text(val + 20, i, f'{val:.0f}', va='center', fontsize=8)

    # 2. Win Percentage
    ax2 = plt.subplot(2, 3, 2)
    teams_sorted_wins = sorted(zip(teams, win_pcts), key=lambda x: x[1], reverse=True)
    teams_w = [t[0] for t in teams_sorted_wins]
    pcts_w = [t[1] for t in teams_sorted_wins]
    colors2 = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(teams_w)))
    bars2 = ax2.barh(range(len(teams_w)), pcts_w, color=colors2)
    ax2.set_yticks(range(len(teams_w)))
    ax2.set_yticklabels(teams_w, fontsize=9)
    ax2.set_xlabel('Win Percentage', fontsize=10, fontweight='bold')
    ax2.set_title('All-Time Win Percentage', fontsize=12, fontweight='bold', pad=10)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 100)

    for i, (bar, val) in enumerate(zip(bars2, pcts_w)):
        ax2.text(val + 1, i, f'{val:.1f}%', va='center', fontsize=8)

    # 3. MVP Panel with Headshot
    ax3 = plt.subplot(2, 3, 3)
    ax3.axis('off')

    if mvp_name and mvp_info:
        # Display MVP information
        mvp_text = f"MOST VALUABLE PLAYER\n\n"
        mvp_text += f"{mvp_name}\n"
        mvp_text += f"{mvp_year} Season\n\n"
        mvp_text += f"Position: {mvp_info['position']}\n"
        mvp_text += f"Points: {mvp_info['points']:.1f}\n"
        mvp_text += f"Value Over Replacement: {mvp_info['vor']:.1f}\n"
        mvp_text += f"Team: {mvp_info['owner']}"

        # Add MVP headshot if available
        if mvp_headshot:
            # Create space for headshot at top
            ax3.text(0.5, 0.35, mvp_text, transform=ax3.transAxes,
                    fontsize=11, ha='center', va='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3),
                    family='monospace', fontweight='bold')

            # Display headshot
            img_ax = fig.add_axes([0.7, 0.62, 0.15, 0.25])
            img_ax.imshow(mvp_headshot)
            img_ax.axis('off')
        else:
            # No headshot, just show text centered
            ax3.text(0.5, 0.5, mvp_text, transform=ax3.transAxes,
                    fontsize=12, ha='center', va='center',
                    bbox=dict(boxstyle='round', facecolor='gold', alpha=0.5),
                    family='monospace', fontweight='bold')

    # 4. Luck Analysis (scatter plot)
    ax4 = plt.subplot(2, 3, 4)
    scatter = ax4.scatter(total_points, points_against, c=win_pcts, cmap='RdYlGn',
                         s=200, alpha=0.7, edgecolors='black', linewidth=1.5)

    for i, team in enumerate(teams):
        ax4.annotate(team, (total_points[i], points_against[i]),
                    fontsize=7, ha='center', va='bottom')

    ax4.set_xlabel('Points For', fontsize=10, fontweight='bold')
    ax4.set_ylabel('Points Against', fontsize=10, fontweight='bold')
    ax4.set_title('Luck Analysis: Points For vs Against', fontsize=12, fontweight='bold', pad=10)
    ax4.grid(True, alpha=0.3)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax4)
    cbar.set_label('Win %', fontsize=9)

    # 5. Championships and Playoff Appearances
    ax5 = plt.subplot(2, 3, 5)
    x = np.arange(len(teams))
    width = 0.35

    bars_champ = ax5.bar(x - width/2, championships, width, label='Championships',
                        color='gold', edgecolor='black', linewidth=1.5)
    bars_playoff = ax5.bar(x + width/2, playoff_apps, width, label='Playoff Appearances',
                          color='silver', edgecolor='black', linewidth=1.5)

    ax5.set_ylabel('Count', fontsize=10, fontweight='bold')
    ax5.set_title('Championships & Playoff Appearances', fontsize=12, fontweight='bold', pad=10)
    ax5.set_xticks(x)
    ax5.set_xticklabels(teams, rotation=45, ha='right', fontsize=8)
    ax5.legend(fontsize=9)
    ax5.grid(True, axis='y', alpha=0.3)

    # Add value labels
    for bars in [bars_champ, bars_playoff]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax5.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom', fontsize=8)

    # 6. Hall of Fame - Top Player Seasons (spans bottom row)
    if top_players and player_headshots:
        # Create a large subplot spanning the bottom row
        ax6 = plt.subplot(3, 1, 3)
        ax6.axis('off')
        ax6.set_title('HALL OF FAME - Top 10 Most Valuable Seasons',
                     fontsize=14, fontweight='bold', pad=20)

        # Display top players with headshots in a grid
        num_players = min(10, len(top_players))
        cols = 5
        rows = 2

        for idx, player_data in enumerate(top_players[:num_players]):
            player_name = player_data['player']

            # Calculate position in grid
            row = idx // cols
            col = idx % cols

            # Create subplot for each player
            # Position: [left, bottom, width, height]
            left = 0.05 + col * 0.19
            bottom = 0.12 - row * 0.10
            width = 0.15
            height = 0.08

            player_ax = fig.add_axes([left, bottom, width, height])
            player_ax.axis('off')

            # Add headshot if available
            if player_name in player_headshots:
                img = player_headshots[player_name]
                # Create smaller inset for headshot
                img_ax = fig.add_axes([left, bottom + 0.04, 0.05, 0.04])
                img_ax.imshow(img)
                img_ax.axis('off')

                # Add player info next to headshot
                info_text = f"{player_name}\n"
                info_text += f"{player_data['year']} • {player_data['position']}\n"
                info_text += f"VOR: {player_data['vor']:.1f}"

                player_ax.text(0.35, 0.5, info_text, transform=player_ax.transAxes,
                             fontsize=8, ha='left', va='center',
                             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
            else:
                # No headshot, just show text
                info_text = f"#{idx+1} {player_name}\n"
                info_text += f"{player_data['year']} • {player_data['position']}\n"
                info_text += f"VOR: {player_data['vor']:.1f} • Pts: {player_data['points']:.1f}"

                player_ax.text(0.5, 0.5, info_text, transform=player_ax.transAxes,
                             fontsize=8, ha='center', va='center',
                             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))

    plt.tight_layout(rect=[0, 0.15, 1, 1])  # Leave space for Hall of Fame at bottom
    plt.savefig('fantasy_wrapped_charts.png', dpi=300, bbox_inches='tight')
    print("\nCharts saved to: fantasy_wrapped_charts.png")


# ========================================
# REPORT GENERATION
# ========================================

def generate_report(all_data: Dict):
    """Generate comprehensive text report."""
    team_stats = all_data['team_stats']

    # Check if we have any data
    if not team_stats:
        print("\nERROR: No league data was loaded!")
        print("This could be due to:")
        print("  1. Network/proxy issues preventing API access")
        print("  2. Invalid ESPN credentials (espn_s2 and SWID)")
        print("  3. Incorrect league ID")
        print("\nPlease check your configuration and try again.")
        return

    report = []
    report.append("=" * 80)
    report.append(" ESPN FANTASY FOOTBALL WRAPPED (2021-2025)".center(80))
    report.append("=" * 80)
    report.append("")

    # ========================================
    # CORE STATISTICS
    # ========================================
    report.append("🏆 CORE AWARDS")
    report.append("=" * 80)
    report.append("")

    # All-Time Scoring Leader
    scoring_leader = max(team_stats.items(), key=lambda x: x[1]['total_points_for'])
    report.append(f"📊 ALL-TIME SCORING LEADER: {scoring_leader[0]}")
    report.append(f"   Total Points: {scoring_leader[1]['total_points_for']:.2f}")
    report.append("")

    # Scoring Rankings
    report.append("ALL-TIME SCORING RANKINGS:")
    for i, (team, stats) in enumerate(sorted(team_stats.items(),
                                             key=lambda x: x[1]['total_points_for'],
                                             reverse=True), 1):
        report.append(f"  {i:2d}. {team:30s} {stats['total_points_for']:8.2f} pts")
    report.append("")

    # Unluckiest Manager
    unluckiest = max(team_stats.items(), key=lambda x: x[1]['total_points_against'])
    report.append(f"😢 UNLUCKIEST MANAGER: {unluckiest[0]}")
    report.append(f"   Points Against: {unluckiest[1]['total_points_against']:.2f}")
    report.append("")

    # Luckiest Manager
    luckiest = min(team_stats.items(), key=lambda x: x[1]['total_points_against'])
    report.append(f"🍀 LUCKIEST MANAGER: {luckiest[0]}")
    report.append(f"   Points Against: {luckiest[1]['total_points_against']:.2f}")
    report.append("")

    # Luck Rankings
    report.append("LUCK RANKINGS (Points Against - Lower is Luckier):")
    for i, (team, stats) in enumerate(sorted(team_stats.items(),
                                             key=lambda x: x[1]['total_points_against']), 1):
        report.append(f"  {i:2d}. {team:30s} {stats['total_points_against']:8.2f} pts against")
    report.append("")

    # Best All-Time Record
    best_record_team = max(team_stats.items(),
                          key=lambda x: (x[1]['wins'] + 0.5 * x[1]['ties']) /
                                       (x[1]['wins'] + x[1]['losses'] + x[1]['ties']))
    total_games = (best_record_team[1]['wins'] + best_record_team[1]['losses'] +
                   best_record_team[1]['ties'])
    win_pct = (best_record_team[1]['wins'] + 0.5 * best_record_team[1]['ties']) / total_games * 100

    report.append(f"🏅 BEST ALL-TIME RECORD: {best_record_team[0]}")
    report.append(f"   Record: {best_record_team[1]['wins']}-{best_record_team[1]['losses']}-"
                 f"{best_record_team[1]['ties']} ({win_pct:.1f}%)")
    report.append("")

    # Win Percentage Rankings
    report.append("ALL-TIME WIN PERCENTAGE RANKINGS:")
    sorted_by_wins = sorted(team_stats.items(),
                           key=lambda x: (x[1]['wins'] + 0.5 * x[1]['ties']) /
                                        (x[1]['wins'] + x[1]['losses'] + x[1]['ties']),
                           reverse=True)
    for i, (team, stats) in enumerate(sorted_by_wins, 1):
        total_g = stats['wins'] + stats['losses'] + stats['ties']
        w_pct = (stats['wins'] + 0.5 * stats['ties']) / total_g * 100
        report.append(f"  {i:2d}. {team:30s} {stats['wins']:2d}-{stats['losses']:2d}-"
                     f"{stats['ties']:2d} ({w_pct:5.1f}%)")
    report.append("")

    # Highest Single Week
    highest_week_score = 0
    highest_week_team = None
    for team, stats in team_stats.items():
        if stats['weekly_scores']:
            max_score = max(stats['weekly_scores'])
            if max_score > highest_week_score:
                highest_week_score = max_score
                highest_week_team = team

    report.append(f"💯 HIGHEST SINGLE WEEK: {highest_week_team}")
    report.append(f"   Score: {highest_week_score:.2f}")
    report.append("")

    # Punt God Award
    punt_god, punt_god_points, punt_breakdown = calculate_punt_god(all_data)
    if punt_god:
        report.append(f"🦶 PUNT GOD (Most D/ST, K, P Points): {punt_god}")
        report.append(f"   Total Special Teams Points: {punt_god_points:.2f}")
        report.append(f"   Defense/ST: {punt_breakdown['D/ST']:.2f} | "
                     f"Kicker: {punt_breakdown['K']:.2f} | "
                     f"Punter: {punt_breakdown['P']:.2f}")
        report.append("")

    # ========================================
    # INJURY ANALYSIS
    # ========================================
    report.append("=" * 80)
    report.append("🏥 INJURY ANALYSIS")
    report.append("=" * 80)
    report.append("")

    most_injured = max(team_stats.items(), key=lambda x: x[1]['injury_weeks'])
    report.append(f"🤕 MOST INJURED TEAM: {most_injured[0]}")
    report.append(f"   Total Injury-Weeks: {most_injured[1]['injury_weeks']}")
    report.append(f"   Worst Single Week: {most_injured[1]['max_injuries_single_week']} injuries")

    if most_injured[1]['injured_players']:
        frequent_flyer = most_injured[1]['injured_players'].most_common(1)[0]
        report.append(f"   Frequent Flyer: {frequent_flyer[0]} ({frequent_flyer[1]} injury-weeks)")
    report.append("")

    # Injury Rankings
    report.append("INJURY-WEEK RANKINGS:")
    for i, (team, stats) in enumerate(sorted(team_stats.items(),
                                             key=lambda x: x[1]['injury_weeks'],
                                             reverse=True), 1):
        report.append(f"  {i:2d}. {team:30s} {stats['injury_weeks']:4d} injury-weeks "
                     f"(max {stats['max_injuries_single_week']} in one week)")
    report.append("")

    # ========================================
    # NEMESIS & VICTIMS (FPS-Style Rivalry Stats)
    # ========================================
    report.append("=" * 80)
    report.append("⚔️  NEMESIS & VICTIMS")
    report.append("=" * 80)
    report.append("")

    h2h_stats = calculate_head_to_head_stats(all_data['matchups'])
    nemesis_data = calculate_nemesis_and_victims(h2h_stats)

    # Sort managers alphabetically for consistent display
    for manager in sorted(nemesis_data.keys()):
        data = nemesis_data[manager]
        report.append(f"{manager}:")

        # Nemesis (who crushed them the most)
        if data['nemesis']:
            nem = data['nemesis']
            report.append(f"  💀 Nemesis: {nem['opponent']}")
            report.append(f"     Scored {nem['avg_points_against']:.1f} pts/game against you "
                         f"({nem['total_points_against']:.1f} total, {nem['games']} games)")
            report.append(f"     Your record vs them: {nem['record']}")

        # Victim (who they crushed the most)
        if data['victim']:
            vic = data['victim']
            report.append(f"  🎯 Victim: {vic['opponent']}")
            report.append(f"     You scored {vic['avg_points_for']:.1f} pts/game against them "
                         f"({vic['total_points_for']:.1f} total, {vic['games']} games)")
            report.append(f"     Your record vs them: {vic['record']}")

        report.append("")

    # ========================================
    # PLAYER DEEP DIVE
    # ========================================
    report.append("=" * 80)
    report.append("⭐ PLAYER DEEP DIVE")
    report.append("=" * 80)
    report.append("")

    # Calculate VOR
    vor_data = calculate_value_over_replacement(all_data)

    # Most Valuable Player (Single Season)
    mvp, mvp_year, mvp_info = find_most_valuable_player(vor_data)
    report.append(f"🌟 MOST VALUABLE PLAYER (Single Season): {mvp}")
    report.append(f"   Season: {mvp_year}")
    report.append(f"   Position: {mvp_info['position']}")
    report.append(f"   Total Points: {mvp_info['points']:.2f}")
    report.append(f"   Value Over Replacement: {mvp_info['vor']:.2f}")
    report.append(f"   Team: {mvp_info['owner']}")
    report.append("")

    # Calculate 5-year VOR statistics
    total_vor_rankings, avg_vor_rankings = calculate_five_year_vor(vor_data)

    # Most Valuable Player (5-Year Total VOR)
    if total_vor_rankings:
        top_total = total_vor_rankings[0]
        years_str = ', '.join(str(y) for y in top_total['years'])
        report.append(f"🏆 MOST VALUABLE PLAYER (5-Year Total VOR): {top_total['player']}")
        report.append(f"   Position: {top_total['position']}")
        report.append(f"   Total VOR (2021-2025): {top_total['total_vor']:.2f}")
        report.append(f"   Seasons Played: {top_total['seasons_played']} ({years_str})")
        report.append(f"   Average VOR per Season: {top_total['avg_vor']:.2f}")
        report.append("")

    # Most Valuable Player (5-Year Average VOR)
    if avg_vor_rankings:
        top_avg = avg_vor_rankings[0]
        years_str = ', '.join(str(y) for y in top_avg['years'])
        report.append(f"⭐ MOST VALUABLE PLAYER (5-Year Average VOR): {top_avg['player']}")
        report.append(f"   Position: {top_avg['position']}")
        report.append(f"   Average VOR per Season: {top_avg['avg_vor']:.2f}")
        report.append(f"   Seasons Played: {top_avg['seasons_played']} ({years_str})")
        report.append(f"   Total VOR (2021-2025): {top_avg['total_vor']:.2f}")
        report.append("")

    # Top 10 by Total VOR
    report.append("TOP 10 PLAYERS BY 5-YEAR TOTAL VOR:")
    for i, player_data in enumerate(total_vor_rankings[:10], 1):
        report.append(f"  {i:2d}. {player_data['player']:25s} - "
                     f"{player_data['position']:4s} - "
                     f"Total: {player_data['total_vor']:6.2f} - "
                     f"Avg: {player_data['avg_vor']:5.2f} - "
                     f"{player_data['seasons_played']} seasons")
    report.append("")

    # Top 10 by Average VOR
    report.append("TOP 10 PLAYERS BY 5-YEAR AVERAGE VOR:")
    for i, player_data in enumerate(avg_vor_rankings[:10], 1):
        report.append(f"  {i:2d}. {player_data['player']:25s} - "
                     f"{player_data['position']:4s} - "
                     f"Avg: {player_data['avg_vor']:5.2f} - "
                     f"Total: {player_data['total_vor']:6.2f} - "
                     f"{player_data['seasons_played']} seasons")
    report.append("")

    # Top 10 Most Valuable Seasons
    report.append("TOP 10 MOST VALUABLE PLAYER SEASONS:")
    all_player_seasons = []
    for year, year_vor in vor_data.items():
        for player, data in year_vor.items():
            all_player_seasons.append({
                'player': player,
                'year': year,
                'vor': data['vor'],
                'points': data['points'],
                'position': data['position'],
                'owner': data['owner']
            })

    all_player_seasons.sort(key=lambda x: x['vor'], reverse=True)
    for i, season in enumerate(all_player_seasons[:10], 1):
        report.append(f"  {i:2d}. {season['player']:25s} ({season['year']}) - "
                     f"{season['position']:4s} - VOR: {season['vor']:6.2f} - "
                     f"{season['owner']}")
    report.append("")

    # Best Draft Picks
    best_picks = find_best_draft_picks(all_data, vor_data)

    report.append("🎯 BEST DRAFT PICKS BY YEAR (Round-Relative VOR Delta):")
    non_keeper_picks = [p for p in best_picks if not p['is_keeper']]
    for pick in non_keeper_picks:
        pct_delta = (
            f"{pick['round_vor_pct_delta'] * 100:.1f}%"
            if pick['round_vor_pct_delta'] is not None
            else "N/A"
        )
        report.append(
            f"  {pick['year']}: {pick['player']:25s} - Rd {pick['round']:2d} - "
            f"VOR: {pick['vor']:6.2f} - Δ vs Rd Avg: {pick['round_vor_delta']:6.2f} "
            f"({pct_delta}) - {pick['team']}"
        )
    report.append("")

    keeper_best_picks = [p for p in best_picks if p['is_keeper']]
    if keeper_best_picks:
        report.append("🔒 TOP KEEPER PICKS BY YEAR (Round-Relative VOR Delta):")
        for pick in keeper_best_picks:
            pct_delta = (
                f"{pick['round_vor_pct_delta'] * 100:.1f}%"
                if pick['round_vor_pct_delta'] is not None
                else "N/A"
            )
            report.append(
                f"  {pick['year']}: {pick['player']:25s} - Rd {pick['round']:2d} - "
                f"VOR: {pick['vor']:6.2f} - Δ vs Rd Avg: {pick['round_vor_delta']:6.2f} "
                f"({pct_delta}) - {pick['team']}"
            )
        report.append("")

    # Keeper Value
    keeper_values = calculate_keeper_value(all_data, vor_data)
    report.append("🔒 MOST VALUE FROM KEEPERS:")
    for i, (team, value) in enumerate(sorted(keeper_values.items(),
                                             key=lambda x: x[1],
                                             reverse=True), 1):
        report.append(f"  {i:2d}. {team:30s} Total Keeper VOR: {value:.2f}")
    report.append("")

    # Draft Pick Value (non-keepers, years 2-5)
    draft_values = calculate_draft_pick_value(all_data, vor_data)
    report.append("📝 MOST VALUE FROM DRAFT PICKS (Non-Keepers, 2022-2025):")
    for i, (team, value) in enumerate(sorted(draft_values.items(),
                                             key=lambda x: x[1],
                                             reverse=True), 1):
        report.append(f"  {i:2d}. {team:30s} Total Draft Pick VOR: {value:.2f}")
    report.append("")

    # ========================================
    # CHAMPIONSHIP & PLAYOFF SUMMARY
    # ========================================
    report.append("=" * 80)
    report.append("🏆 CHAMPIONSHIPS & PLAYOFF SUMMARY")
    report.append("=" * 80)
    report.append("")

    report.append("CHAMPIONSHIP COUNT:")
    for i, (team, stats) in enumerate(sorted(team_stats.items(),
                                             key=lambda x: x[1]['championships'],
                                             reverse=True), 1):
        if stats['championships'] > 0:
            report.append(f"  {team:30s} {stats['championships']} championship(s)")
    report.append("")

    report.append("PLAYOFF APPEARANCES:")
    for i, (team, stats) in enumerate(sorted(team_stats.items(),
                                             key=lambda x: x[1]['playoff_appearances'],
                                             reverse=True), 1):
        report.append(f"  {i:2d}. {team:30s} {stats['playoff_appearances']} appearances")
    report.append("")

    # ========================================
    # FOOTER
    # ========================================
    report.append("=" * 80)
    report.append(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)

    # Write to file
    with open('fantasy_wrapped_report.txt', 'w') as f:
        f.write('\n'.join(report))

    print("\nReport saved to: fantasy_wrapped_report.txt")

    # Also print to console
    print("\n" + '\n'.join(report))


# ========================================
# MAIN EXECUTION
# ========================================

def main():
    """Main execution function."""
    print("=" * 80)
    print(" ESPN Fantasy Football Wrapped".center(80))
    print(" Analyzing 5 Years of League History (2021-2025)".center(80))
    print("=" * 80)
    print()

    # Extract all data
    print("Phase 1: Extracting league data...")
    all_data = extract_all_data()

    # Calculate VOR and find MVP
    print("\nPhase 2: Calculating player values and downloading player headshots...")
    vor_data = calculate_value_over_replacement(all_data)
    mvp_name, mvp_year, mvp_info = find_most_valuable_player(vor_data)

    # Download MVP headshot
    mvp_headshot = None
    if mvp_name and mvp_info and mvp_info.get('player_id'):
        print(f"  Found MVP: {mvp_name} ({mvp_year})")
        mvp_headshot = download_player_headshot(
            mvp_info['player_id'],
            mvp_name,
            save_path='mvp_headshot.png'
        )

    # Get top 10 player seasons and download their headshots
    print("  Finding top player seasons...")
    top_players = get_top_player_seasons(vor_data, limit=10)
    print(f"  Downloading headshots for top {len(top_players)} players...")
    player_headshots = download_top_player_headshots(top_players)
    print(f"  Successfully downloaded {len(player_headshots)} headshots")

    print("\nPhase 3: Generating visualizations...")
    create_visualizations(all_data, mvp_name, mvp_year, mvp_info, mvp_headshot,
                         top_players, player_headshots)

    print("\nPhase 4: Generating comprehensive report...")
    generate_report(all_data)

    print("\n" + "=" * 80)
    print(" Analysis Complete!".center(80))
    print(" Check fantasy_wrapped_report.txt and fantasy_wrapped_charts.png".center(80))
    if mvp_headshot:
        print(" MVP headshot saved to mvp_headshot.png".center(80))
    print("=" * 80)


if __name__ == "__main__":
    main()
