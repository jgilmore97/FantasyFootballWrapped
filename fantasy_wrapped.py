#!/usr/bin/env python3
"""
ESPN Fantasy Football Wrapped
A "Spotify Wrapped" style summary tool for ESPN Fantasy Football leagues
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Tuple, Any
import warnings

warnings.filterwarnings('ignore')

from espn_api.football import League
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np
from PIL import Image
import requests
from io import BytesIO

# ========================================
# CONFIGURATION
# ========================================


LEAGUE_ID = 778135041
YEARS = [2021, 2022, 2023, 2024, 2025]
ESPN_S2 = "AECZk7m5ZiOXfGwzOnbj7p3EoalPIV2RCeA%2BjgMiZfLTu731Pjk1h%2FkbHIVTCJ7QD0vd4XlZ%2FVezppPxysurKT6DFjtS2U6hF5XJUmHcjvHewmCbPaWv1YNI0FpLdBEADn3N1xKN9ert4%2BA9pljrcO3v9zrPV9h0h7u9%2ByCKJDEYxAoZjIWQTHD2qHdY4EOhi%2F0Y8iZYlrMp1BRmI8HDmYcZjtUwXTL%2Bx3H70FZtE1bfXPyqxs1n5zgFc0X7tRu3I2GfdTazuworr3VflODY9fVi8Hsf9ttxlat1slyF5zBGng%3D%3D"
SWID = "{CFD648CA-1223-407F-8E12-A5F773A4C738}"

def _coerce_years(years_value) -> List[int]:
    """Normalize a variety of year inputs into a sorted list of integers."""

    if isinstance(years_value, list):
        return [int(y) for y in years_value if str(y).strip()]

    if isinstance(years_value, str):
        cleaned = years_value.strip().strip("[]")
        if not cleaned:
            return []
        parts = [p.strip() for p in cleaned.replace(";", ",").split(",") if p.strip()]
        return [int(p) for p in parts]

    if years_value:
        try:
            return [int(years_value)]
        except Exception:
            return []

    return []


def load_configuration() -> None:
    """Load runtime configuration from CLI args and environment variables."""
    global LEAGUE_ID, YEARS, ESPN_S2, SWID  # Must be FIRST, before any usage

    parser = argparse.ArgumentParser(description="Generate a Fantasy Football Wrapped report")
    parser.add_argument("--league-id", type=int, default=None,
                        help="ESPN league ID (can also be set via LEAGUE_ID env var)")
    parser.add_argument("--years", type=str, default=None,
                        help="Comma-separated list of seasons to analyze (or YEARS env var)")
    parser.add_argument("--espn-s2", dest="espn_s2", default=None,
                        help="ESPN_S2 cookie value (or ESPN_S2 env var)")
    parser.add_argument("--swid", dest="swid", default=None,
                        help="SWID cookie value (or SWID env var)")

    args = parser.parse_args()

    # CLI args override env vars, which override hardcoded defaults
    if args.league_id is not None:
        LEAGUE_ID = args.league_id
    elif os.getenv("LEAGUE_ID"):
        LEAGUE_ID = int(os.getenv("LEAGUE_ID"))

    if args.espn_s2:
        ESPN_S2 = args.espn_s2
    elif os.getenv("ESPN_S2"):
        ESPN_S2 = os.getenv("ESPN_S2")

    if args.swid:
        SWID = args.swid
    elif os.getenv("SWID"):
        SWID = os.getenv("SWID")

    if args.years:
        YEARS = _coerce_years(args.years)
    elif os.getenv("YEARS"):
        YEARS = _coerce_years(os.getenv("YEARS"))

    print("Using configuration:")
    print(f"  League ID: {LEAGUE_ID}")
    print(f"  Years: {', '.join(str(y) for y in YEARS)}")
    print("  Auth: espn_s2 and SWID provided")

# Position-specific thresholds for "startable" players (for value over replacement)
STARTABLE_THRESHOLDS = {
    'QB': 25,  # Top 25 QBs
    'RB': 40,  # Top 40 RBs
    'WR': 50,  # Top 50 WRs
    'TE': 15,  # Top 15 TEs
    'D/ST': 15,  # Top 15 Defenses
    'K': 15,   # Top 15 Kickers
}

INJURY_STATUSES = [
    'OUT',
    'IR',
    'INJURY_RESERVE',
    'PUP',
    'PUP-R'
]

# ========================================
# DATA EXTRACTION
# ========================================

def load_league_data(year: int) -> League:
    """Load league data for a specific year."""
    print(f"Loading {year} season data...")
    league_url = f"https://fantasy.espn.com/football/league?leagueId={LEAGUE_ID}&seasonId={year}"
    print(f"  League URL: {league_url}")

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
        print("  Verify the league ID and authentication cookies (espn_s2, SWID) are correct and current.")
        return None


def get_owner_name(team):
    """Safely extract owner name from team object."""

    def _is_generic_display(name: str) -> bool:
        """Detect placeholder names like ESPNFAN123456."""
        if not name:
            return False
        upper = name.upper()
        return upper.startswith('ESPNFAN') or upper.startswith('FANTASY MANAGER')

    def _normalize_owner(owner):
        """Convert various owner representations (dict/list/str) to a stable string."""
        if isinstance(owner, list):
            return _normalize_owner(owner[0]) if owner else 'Unknown'

        if isinstance(owner, dict):
            # Try common keys exposed by the ESPN API
            display_name = owner.get('displayName') or owner.get('nickname')

            # ESPN returns richer profile details alongside the default ESPNFAN label
            # for leagues where managers never customized their public display name.
            first = owner.get('firstName') or owner.get('first_name')
            last = owner.get('lastName') or owner.get('last_name')
            full_name = f"{first or ''} {last or ''}".strip()

            # Some responses embed an additional profile dict (e.g., user/profile)
            profile = owner.get('userProfile') or owner.get('user') or {}
            if not full_name:
                pf_first = profile.get('firstName') or profile.get('givenName')
                pf_last = profile.get('lastName') or profile.get('familyName')
                if pf_first or pf_last:
                    full_name = f"{pf_first or ''} {pf_last or ''}".strip()

            stable_id = owner.get('id') or profile.get('id') or profile.get('userId')

            # Prefer a real name over the generic ESPNFAN string when available.
            if full_name:
                best = full_name
            elif display_name and not _is_generic_display(display_name):
                best = display_name
            else:
                best = display_name or 'Unknown'

            # Only surface the stable identifier when we have no meaningful name.
            if _is_generic_display(best) and stable_id and best != str(stable_id):
                return f"{best} ({stable_id})"
            return best or 'Unknown'

        # For primitive types (str/int/etc.) just coerce to string
        return str(owner) if owner is not None else 'Unknown'

    # Handle both 'owner' (old API) and 'owners' (new API)
    if hasattr(team, 'owner'):
        return _normalize_owner(team.owner)
    elif hasattr(team, 'owners'):
        return _normalize_owner(team.owners)
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
            'keeper_points': defaultdict(float),  # year -> points from keepers
            'draft_points': defaultdict(float),   # year -> points from draft picks
            'keeper_picks': defaultdict(list),    # year -> list of keeper picks
            'draft_picks': defaultdict(list),     # year -> list of draft picks
        }),
        'matchups': [],
        'player_seasons': defaultdict(lambda: defaultdict(float)),  # player_key -> year -> data
        'player_id_to_name': {},  # player_id -> canonical name (most recent)
        'draft_data': defaultdict(dict),  # year -> draft info
        # New: detailed injury tracking for weighted calculations
        'injury_details': defaultdict(lambda: defaultdict(list)),  # year -> owner -> list of {player_key, week, player_name}
        'weekly_rosters': defaultdict(lambda: defaultdict(dict)),  # year -> week -> owner -> set of player_keys
        'weekly_player_points': defaultdict(lambda: defaultdict(dict)),  # year -> week -> player_key -> points
        'season_weeks': {},  # year -> total regular season weeks
        # NEW: Track player details from box scores for dropped player recovery
        # Structure: year -> player_key -> {weekly_points: [], position, player_name, player_id, owners: set}
        'box_score_player_data': defaultdict(lambda: defaultdict(lambda: {
            'weekly_points': [],
            'position': None,
            'player_name': None,
            'player_id': None,
            'owners': set()
        })),
        # NEW: Transaction and acquisition tracking
        'team_id_to_owner': defaultdict(dict),  # year -> team_id -> owner name
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

            # Track team_id -> owner mapping for transaction parsing
            team_id = getattr(team, 'team_id', None)
            if team_id is None:
                team_id = getattr(team, 'teamId', None)
            if team_id is None:
                team_id = getattr(team, 'id', None)
            if team_id is not None:
                all_data['team_id_to_owner'][year][team_id] = owner_name

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

        # Process weekly matchups
        try:
            total_weeks = league.settings.reg_season_count
            all_data['season_weeks'][year] = total_weeks
            
            for week in range(1, total_weeks + 1):
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

                            # Injury tracking (original simple tracking)
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
                            
                            # NEW: Detailed injury tracking for weighted calculations
                            for injury in home_injuries['details']:
                                all_data['injury_details'][year][home_owner].append({
                                    'player_key': injury['player_key'],
                                    'player_name': injury['player_name'],
                                    'week': week
                                })
                            for injury in away_injuries['details']:
                                all_data['injury_details'][year][away_owner].append({
                                    'player_key': injury['player_key'],
                                    'player_name': injury['player_name'],
                                    'week': week
                                })
                            
                            # NEW: Track rosters and player points for season-ending injury detection
                            home_lineup_info = extract_lineup_info(matchup.home_lineup)
                            away_lineup_info = extract_lineup_info(matchup.away_lineup)
                            
                            all_data['weekly_rosters'][year][week][home_owner] = home_lineup_info['roster']
                            all_data['weekly_rosters'][year][week][away_owner] = away_lineup_info['roster']
                            
                            # Merge player points into the weekly tracker
                            for player_key, points in home_lineup_info['player_points'].items():
                                all_data['weekly_player_points'][year][week][player_key] = points
                            for player_key, points in away_lineup_info['player_points'].items():
                                all_data['weekly_player_points'][year][week][player_key] = points
                            
                            # NEW: Collect detailed player data from box scores for dropped player recovery
                            # This ensures we capture season data for players who were dropped mid-season
                            for player_key, details in home_lineup_info['player_details'].items():
                                bs_data = all_data['box_score_player_data'][year][player_key]
                                bs_data['weekly_points'].append(details['points'])
                                bs_data['position'] = details['position']
                                bs_data['player_name'] = details['player_name']
                                bs_data['player_id'] = details['player_id']
                                bs_data['owners'].add(home_owner)
                            
                            for player_key, details in away_lineup_info['player_details'].items():
                                bs_data = all_data['box_score_player_data'][year][player_key]
                                bs_data['weekly_points'].append(details['points'])
                                bs_data['position'] = details['position']
                                bs_data['player_name'] = details['player_name']
                                bs_data['player_id'] = details['player_id']
                                bs_data['owners'].add(away_owner)

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
    """Count injured players in a lineup and return detailed info."""
    injury_count = 0
    injured_players = []
    injured_details = []  # New: detailed info for weighted tracking

    for player in lineup:
        status = getattr(player, 'injuryStatus', None)
        normalized_status = str(status).replace('-', '_').upper() if status else None

        if normalized_status and normalized_status in INJURY_STATUSES:
            injury_count += 1
            player_id = getattr(player, 'playerId', None)
            player_key = str(player_id) if player_id else None
            
            if hasattr(player, 'name'):
                player_name = player.name
                # Handle case where name might be a dict or other non-string type
                if isinstance(player_name, dict):
                    # Try to extract a string representation
                    player_name = player_name.get('fullName') or player_name.get('name') or str(player_name)
                elif not isinstance(player_name, str):
                    player_name = str(player_name)
                injured_players.append(player_name)
                
                # Add detailed info
                if player_key:
                    injured_details.append({
                        'player_key': player_key,
                        'player_name': player_name,
                        'player_id': player_id
                    })

    return {
        'count': injury_count,
        'players': injured_players,
        'details': injured_details  # New field
    }


def extract_lineup_info(lineup: List) -> Dict:
    """Extract roster and points info from a lineup for a given week."""
    roster = set()
    player_points = {}
    player_details = {}  # NEW: Capture full player details for season aggregation
    
    for player in lineup:
        player_id = getattr(player, 'playerId', None)
        if player_id:
            player_key = str(player_id)
            roster.add(player_key)
            # Get points scored this week
            points = getattr(player, 'points', 0) or 0
            player_points[player_key] = points
            
            # NEW: Capture player details for later aggregation
            player_name = getattr(player, 'name', '')
            if isinstance(player_name, dict):
                player_name = player_name.get('fullName') or player_name.get('name') or str(player_name)
            elif not isinstance(player_name, str):
                player_name = str(player_name)
            
            position = getattr(player, 'position', 'UNKNOWN')
            
            player_details[player_key] = {
                'player_id': player_id,
                'player_name': player_name,
                'position': position,
                'points': points
            }
    
    return {
        'roster': roster,
        'player_points': player_points,
        'player_details': player_details  # NEW
    }


def process_player_data(league: League, year: int, all_data: Dict):
    """Process player scoring data for value calculations.
    
    This function collects player data from two sources:
    1. team.roster - The current roster (may miss players dropped mid-season)
    2. box_score_player_data - Aggregated from weekly box scores (captures all players)
    
    We prefer roster data when available (has accurate total_points from ESPN),
    but supplement with box score aggregated data for players who were dropped
    mid-season and no longer appear on any roster.
    """
    roster_player_keys = set()  # Track which players we found on rosters
    
    # First pass: Collect all player season stats from current rosters
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
                    player_id = getattr(player, 'playerId', None)

                    # Use player_id as the primary key if available, fall back to name
                    player_key = str(player_id) if player_id else player_name
                    roster_player_keys.add(player_key)
                    
                    # Store player season stats keyed by player_id
                    all_data['player_seasons'][player_key][year] = {
                        'points': points,
                        'position': position,
                        'team_owner': owner,
                        'player_id': player_id,
                        'player_name': player_name  # Store name with each season
                    }
                    
                    # Update the player_id -> name mapping (use most recent name)
                    all_data['player_id_to_name'][player_key] = player_name

    # Second pass: Add players from box scores who are NOT on any current roster
    # This captures players who were dropped mid-season (e.g., due to injury)
    if year in all_data['box_score_player_data']:
        for player_key, bs_data in all_data['box_score_player_data'][year].items():
            # Only add if NOT already captured from roster data
            if player_key not in roster_player_keys:
                # Aggregate weekly points for season total
                total_points = sum(bs_data['weekly_points'])
                position = bs_data['position'] or 'UNKNOWN'
                player_name = bs_data['player_name'] or player_key
                player_id = bs_data['player_id']
                
                # Use the most recent owner (last team to roster them)
                # If multiple owners, just pick one (they were traded/dropped)
                owners = bs_data['owners']
                owner = list(owners)[-1] if owners else 'Unknown'
                
                all_data['player_seasons'][player_key][year] = {
                    'points': total_points,
                    'position': position,
                    'team_owner': owner,
                    'player_id': player_id,
                    'player_name': player_name,
                    '_from_box_scores': True  # Flag for debugging
                }
                
                # Update the player_id -> name mapping
                if player_name and player_name != player_key:
                    all_data['player_id_to_name'][player_key] = player_name

    # Process draft data
    try:
        if hasattr(league, 'draft'):
            draft_picks = league.draft
            all_data['draft_data'][year] = {
                'picks': []
            }

            for pick in draft_picks:
                player_name = getattr(pick, 'playerName', None)
                player_id = getattr(pick, 'playerId', None)

                # Handle case where playerName might be a dict or other non-string type
                if isinstance(player_name, dict):
                    player_name = player_name.get('fullName') or player_name.get('name') or str(player_name)
                elif player_name and not isinstance(player_name, str):
                    player_name = str(player_name)

                # Use player_id as key if available
                player_key = str(player_id) if player_id else player_name
                
                # Update name mapping
                if player_key and player_name:
                    all_data['player_id_to_name'][player_key] = player_name

                pick_info = {
                    'round': getattr(pick, 'round_num', None),
                    'pick': getattr(pick, 'round_pick', None),
                    'overall': getattr(pick, 'overall_pick', None),
                    'player_name': player_name,
                    'player_key': player_key,  # Add player_key for lookups
                    'player_id': player_id,
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


def calculate_head_to_head_records(matchups: List) -> Dict:
    """Backward-compatible wrapper that mirrors calculate_head_to_head_stats."""
    return calculate_head_to_head_stats(matchups)


def find_top_rivalries(h2h_stats: Dict, top_n: int = 5) -> List[Dict]:
    """Identify the most competitive rivalries based on head-to-head history."""
    rivalries = []

    for team, opponents in h2h_stats.items():
        for opponent, stats in opponents.items():
            # Avoid duplicating pairings by enforcing an ordering
            if team >= opponent or stats['games'] == 0:
                continue

            total_games = stats['games']
            if total_games == 0:
                continue

            # Competitiveness: closer win/loss split and closer scoring margins are better
            record_imbalance = abs(stats['wins'] - stats['losses']) / total_games
            avg_margin = abs(stats['points_for'] - stats['points_against']) / total_games if total_games else 0
            competitiveness = 1 - (record_imbalance * 0.6 + min(avg_margin, 50) / 50 * 0.4)

            rivalry = {
                'team1': team,
                'team2': opponent,
                'total_games': total_games,
                'competitiveness': max(0, competitiveness),
                'record': f"{stats['wins']}-{stats['losses']}-{stats['ties']}",
                'points_for': stats['points_for'],
                'points_against': stats['points_against'],
            }
            rivalries.append(rivalry)

    rivalries.sort(key=lambda r: (r['competitiveness'], r['total_games']), reverse=True)
    return rivalries[:top_n]


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


def generate_h2h_matrix(h2h_stats: Dict) -> List[str]:
    """
    Generate a head-to-head record matrix showing all managers vs all managers.

    Returns a list of formatted strings representing the table.
    """
    # Get all unique managers, sorted alphabetically
    all_managers = sorted(set(h2h_stats.keys()))

    if not all_managers:
        return ["No head-to-head data available"]

    # Create abbreviated names for column headers (use initials or first 3 chars)
    def abbreviate_name(name):
        """Create a short abbreviation for table headers."""
        parts = name.split()
        if len(parts) >= 2:
            # Use first initial + last name first 2 chars
            return f"{parts[0][0]}{parts[-1][:2]}"
        else:
            # Use first 3 characters
            return name[:3]

    abbrevs = {manager: abbreviate_name(manager) for manager in all_managers}

    # Build header row with column numbers
    matrix = []
    matrix.append("")  # Empty line before table
    matrix.append("ALL-TIME HEAD-TO-HEAD RECORDS MATRIX")
    matrix.append("Records shown as W-L-T (Wins-Losses-Ties)")
    matrix.append("")

    # Create legend mapping numbers to managers
    matrix.append("LEGEND:")
    for i, manager in enumerate(all_managers, 1):
        matrix.append(f"  {i:2d}. {manager}")
    matrix.append("")

    # Header row
    header = "    |"
    for i in range(len(all_managers)):
        header += f"  {i+1:2d}  |"
    matrix.append(header)
    matrix.append("-" * len(header))

    # Data rows
    for i, manager_a in enumerate(all_managers):
        row = f" {i+1:2d} |"

        for j, manager_b in enumerate(all_managers):
            if manager_a == manager_b:
                # Diagonal - same manager
                row += "  --  |"
            else:
                # Get record
                stats = h2h_stats.get(manager_a, {}).get(manager_b, {})
                wins = stats.get('wins', 0)
                losses = stats.get('losses', 0)
                ties = stats.get('ties', 0)

                if wins + losses + ties == 0:
                    # No games played
                    row += "  --  |"
                else:
                    # Format as W-L or W-L-T
                    if ties > 0:
                        record = f"{wins}-{losses}-{ties}"
                    else:
                        record = f"{wins}-{losses}"
                    row += f" {record:>4s} |"

        matrix.append(row)

    matrix.append("")
    matrix.append("How to read: Row manager's record vs Column manager")
    matrix.append("Example: Row 1, Column 2 shows manager #1's record against manager #2")
    matrix.append("")

    return matrix


def calculate_heartbreaker_award(matchups: List) -> Dict:
    """
    Find the manager with the most losses by less than 5 points.

    Returns dict with 'manager', 'count', and 'close_losses' list.
    """
    close_losses = defaultdict(list)

    for matchup in matchups:
        home = matchup['home_team']
        away = matchup['away_team']
        home_score = matchup['home_score']
        away_score = matchup['away_score']
        margin = abs(home_score - away_score)

        if 0 < margin < 5:
            # Close game
            if home_score < away_score:
                # Home team lost by less than 5
                close_losses[home].append({
                    'year': matchup['year'],
                    'week': matchup['week'],
                    'opponent': away,
                    'score': home_score,
                    'opponent_score': away_score,
                    'margin': margin
                })
            else:
                # Away team lost by less than 5
                close_losses[away].append({
                    'year': matchup['year'],
                    'week': matchup['week'],
                    'opponent': home,
                    'score': away_score,
                    'opponent_score': home_score,
                    'margin': margin
                })

    if not close_losses:
        return None

    # Find manager with most close losses
    heartbreaker = max(close_losses.items(), key=lambda x: len(x[1]))

    return {
        'manager': heartbreaker[0],
        'count': len(heartbreaker[1]),
        'close_losses': heartbreaker[1]
    }


def find_offensive_explosion(matchups: List) -> Dict:
    """
    Find the highest single-week score with context.

    Returns dict with 'manager', 'score', 'year', 'week', 'opponent', 'opponent_score'.
    """
    best = None

    for matchup in matchups:
        home_score = matchup['home_score']
        away_score = matchup['away_score']

        if home_score > (best['score'] if best else 0):
            best = {
                'manager': matchup['home_team'],
                'score': home_score,
                'year': matchup['year'],
                'week': matchup['week'],
                'opponent': matchup['away_team'],
                'opponent_score': away_score
            }

        if away_score > (best['score'] if best else 0):
            best = {
                'manager': matchup['away_team'],
                'score': away_score,
                'year': matchup['year'],
                'week': matchup['week'],
                'opponent': matchup['home_team'],
                'opponent_score': home_score
            }

    return best


def find_offensive_dud(matchups: List) -> Dict:
    """
    Find the lowest single-week score with context.

    Returns dict with 'manager', 'score', 'year', 'week', 'opponent', 'opponent_score'.
    """
    worst = None

    for matchup in matchups:
        home_score = matchup['home_score']
        away_score = matchup['away_score']

        if worst is None or home_score < worst['score']:
            worst = {
                'manager': matchup['home_team'],
                'score': home_score,
                'year': matchup['year'],
                'week': matchup['week'],
                'opponent': matchup['away_team'],
                'opponent_score': away_score
            }

        if worst is None or away_score < worst['score']:
            worst = {
                'manager': matchup['away_team'],
                'score': away_score,
                'year': matchup['year'],
                'week': matchup['week'],
                'opponent': matchup['home_team'],
                'opponent_score': home_score
            }

    return worst


def calculate_win_loss_streaks(matchups: List) -> Dict:
    """
    Calculate longest win and loss streaks for all managers.

    Returns dict with 'longest_win_streak' and 'longest_loss_streak'.
    """
    # Sort matchups by year and week
    sorted_matchups = sorted(matchups, key=lambda m: (m['year'], m['week']))

    # Track current streaks for each manager
    current_streaks = defaultdict(lambda: {'type': None, 'count': 0, 'start_year': None, 'start_week': None})
    best_win_streaks = defaultdict(lambda: {'count': 0, 'start_year': None, 'start_week': None, 'end_year': None, 'end_week': None})
    best_loss_streaks = defaultdict(lambda: {'count': 0, 'start_year': None, 'start_week': None, 'end_year': None, 'end_week': None})

    for matchup in sorted_matchups:
        home = matchup['home_team']
        away = matchup['away_team']
        home_score = matchup['home_score']
        away_score = matchup['away_score']
        year = matchup['year']
        week = matchup['week']

        # Determine outcomes
        if home_score > away_score:
            home_result = 'win'
            away_result = 'loss'
        elif away_score > home_score:
            home_result = 'loss'
            away_result = 'win'
        else:
            home_result = 'tie'
            away_result = 'tie'

        # Update streaks for both teams
        for manager, result in [(home, home_result), (away, away_result)]:
            if result == 'tie':
                # Ties break streaks
                current_streaks[manager] = {'type': None, 'count': 0, 'start_year': None, 'start_week': None}
                continue

            current = current_streaks[manager]

            if current['type'] == result:
                # Continue streak
                current['count'] += 1
            else:
                # Start new streak
                current['type'] = result
                current['count'] = 1
                current['start_year'] = year
                current['start_week'] = week

            # Check if this is a new best
            if result == 'win' and current['count'] > best_win_streaks[manager]['count']:
                best_win_streaks[manager] = {
                    'count': current['count'],
                    'start_year': current['start_year'],
                    'start_week': current['start_week'],
                    'end_year': year,
                    'end_week': week
                }
            elif result == 'loss' and current['count'] > best_loss_streaks[manager]['count']:
                best_loss_streaks[manager] = {
                    'count': current['count'],
                    'start_year': current['start_year'],
                    'start_week': current['start_week'],
                    'end_year': year,
                    'end_week': week
                }

    # Find overall longest streaks
    longest_win = None
    longest_loss = None

    for manager, streak in best_win_streaks.items():
        if streak['count'] > 0 and (longest_win is None or streak['count'] > longest_win['count']):
            longest_win = {**streak, 'manager': manager}

    for manager, streak in best_loss_streaks.items():
        if streak['count'] > 0 and (longest_loss is None or streak['count'] > longest_loss['count']):
            longest_loss = {**streak, 'manager': manager}

    return {
        'longest_win_streak': longest_win,
        'longest_loss_streak': longest_loss
    }


def calculate_late_round_legend(all_data: Dict, vor_data: Dict) -> Dict:
    """
    Find the best draft pick from round 12 or later by VOR.

    Returns dict with 'player', 'manager', 'year', 'round', 'pick', 'vor'.
    """
    best_late_pick = None

    for year in YEARS:
        if year not in all_data['draft_data']:
            continue

        draft_info = all_data['draft_data'][year]
        picks = draft_info.get('picks', [])

        for pick in picks:
            round_num = pick.get('round_num')
            if round_num and round_num >= 12:
                player_key = pick.get('player_key')

                # Get VOR for this player in this year
                if year in vor_data and player_key in vor_data[year]:
                    player_vor = vor_data[year][player_key]['vor']

                    if best_late_pick is None or player_vor > best_late_pick['vor']:
                        best_late_pick = {
                            'player': pick.get('player_name', player_key),
                            'manager': pick.get('team_owner', 'Unknown'),
                            'year': year,
                            'round': round_num,
                            'pick': pick.get('overall_pick'),
                            'vor': player_vor
                        }

    return best_late_pick


def calculate_unlucky_loser(matchups: List) -> Dict:
    """
    Find the manager who scored the most total points in games they lost.

    Returns dict with 'manager', 'total_points_in_losses', 'loss_count'.
    """
    points_in_losses = defaultdict(float)
    loss_counts = defaultdict(int)

    for matchup in matchups:
        home = matchup['home_team']
        away = matchup['away_team']
        home_score = matchup['home_score']
        away_score = matchup['away_score']

        if home_score < away_score:
            # Home lost
            points_in_losses[home] += home_score
            loss_counts[home] += 1
        elif away_score < home_score:
            # Away lost
            points_in_losses[away] += away_score
            loss_counts[away] += 1

    if not points_in_losses:
        return None

    unlucky = max(points_in_losses.items(), key=lambda x: x[1])

    return {
        'manager': unlucky[0],
        'total_points_in_losses': unlucky[1],
        'loss_count': loss_counts[unlucky[0]],
        'avg_points_in_losses': unlucky[1] / loss_counts[unlucky[0]] if loss_counts[unlucky[0]] > 0 else 0
    }


def calculate_bad_beat(matchups: List) -> Dict:
    """
    Find instances where someone scored 2nd highest in a week but still lost.

    Returns the worst bad beat (highest 2nd place score that lost).
    """
    # Group matchups by year and week
    weekly_scores = defaultdict(list)

    for matchup in matchups:
        key = (matchup['year'], matchup['week'])
        weekly_scores[key].append({
            'manager': matchup['home_team'],
            'score': matchup['home_score'],
            'opponent': matchup['away_team'],
            'opponent_score': matchup['away_score']
        })
        weekly_scores[key].append({
            'manager': matchup['away_team'],
            'score': matchup['away_score'],
            'opponent': matchup['home_team'],
            'opponent_score': matchup['home_score']
        })

    worst_bad_beat = None

    for (year, week), scores in weekly_scores.items():
        # Sort by score descending
        sorted_scores = sorted(scores, key=lambda x: x['score'], reverse=True)

        if len(sorted_scores) >= 2:
            first = sorted_scores[0]
            second = sorted_scores[1]

            # Check if second place lost their matchup
            if second['score'] < second['opponent_score']:
                # This is a bad beat
                if worst_bad_beat is None or second['score'] > worst_bad_beat['score']:
                    worst_bad_beat = {
                        'manager': second['manager'],
                        'score': second['score'],
                        'year': year,
                        'week': week,
                        'opponent': second['opponent'],
                        'opponent_score': second['opponent_score'],
                        'top_score': first['score'],
                        'top_scorer': first['manager']
                    }

    return worst_bad_beat


def calculate_value_over_replacement(all_data: Dict) -> Dict:
    """Calculate value over replacement for all players."""
    vor_data = {}
    player_id_to_name = all_data.get('player_id_to_name', {})

    for year in YEARS:
        if year not in all_data['leagues']:
            continue

        # Collect all player stats by position
        position_stats = defaultdict(list)

        for player_key, seasons in all_data['player_seasons'].items():
            if year in seasons:
                player_info = seasons[year]
                position = player_info['position']
                points = player_info['points']
                
                # Get display name from mapping or from season data
                display_name = player_id_to_name.get(player_key, player_info.get('player_name', player_key))

                # Map position to base position (handle flex designations)
                base_pos = position
                if '/' in position:
                    base_pos = position.split('/')[0]

                if base_pos in STARTABLE_THRESHOLDS:
                    position_stats[base_pos].append({
                        'player_key': player_key,
                        'name': display_name,
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
                    # Keep VOR for all players, even if they fall outside the
                    # top-K replacement threshold for their position. Using the
                    # top-K cutoff only to set the replacement line preserves
                    # meaningful negative VOR in later seasons for players who
                    # drop in production.
                    vor = player['points'] - replacement
                    # Use player_key as the dictionary key for consistent lookups
                    year_vor[player['player_key']] = {
                        'vor': vor,
                        'points': player['points'],
                        'position': pos,
                        'owner': player['owner'],
                        'player_id': player.get('player_id', None),
                        'name': player['name']  # Include display name
                    }

        vor_data[year] = year_vor

    return vor_data


def build_player_owner_shares(all_data: Dict) -> Dict[int, Dict[str, Dict[str, float]]]:
    """Estimate how much of each season's value belonged to each owner."""

    shares_by_year: Dict[int, Dict[str, Dict[str, float]]] = defaultdict(dict)

    for year in YEARS:
        week_rosters = all_data['weekly_rosters'].get(year, {})
        player_weeks: Dict[str, Counter] = defaultdict(Counter)
        max_week_seen = 0

        for week, rosters in week_rosters.items():
            max_week_seen = max(max_week_seen, week)
            for owner, roster in rosters.items():
                for player_key in roster:
                    player_weeks[player_key][owner] += 1

        total_weeks = all_data['season_weeks'].get(year, 0)
        # Use observed data if configured total weeks is missing
        total_weeks = max(total_weeks, max_week_seen)

        if total_weeks == 0:
            total_weeks = 1  # Avoid division by zero; will fall back to season owner mapping below

        for player_key, owner_counts in player_weeks.items():
            shares_by_year[year][player_key] = {
                owner: owner_count / total_weeks
                for owner, owner_count in owner_counts.items()
                if total_weeks > 0
            }

        # Fallback: if we have no weekly roster data for a player, attribute the
        # full season to the roster owner recorded in player_seasons.
        for player_key, seasons in all_data['player_seasons'].items():
            if year in seasons and player_key not in shares_by_year[year]:
                owner = seasons[year].get('team_owner')
                if owner:
                    shares_by_year[year][player_key] = {owner: 1.0}

    return shares_by_year


def find_best_draft_picks(all_data: Dict, vor_data: Dict) -> Tuple[List[Dict], Dict[int, Dict[int, float]]]:
    """
    Find the best draft picks by comparing VOR to round average.

    Returns:
        Tuple of (best_picks list, round_averages_by_year dict)

    The value_score is calculated as delta vs round average - how much better
    a pick performed compared to other players drafted in the same round that year.
    This properly rewards late-round steals over early-round picks that merely
    met expectations.
    """
    owner_shares_by_year = build_player_owner_shares(all_data)

    # First pass: collect all picks with their VOR data
    all_picks = []
    player_id_to_name = all_data.get('player_id_to_name', {})

    for year in YEARS:
        if year not in all_data['draft_data'] or year not in vor_data:
            continue

        draft = all_data['draft_data'][year]
        year_vor_lookup = vor_data[year]

        for pick in draft['picks']:
            player_name = pick['player_name']
            # Use player_key for lookups (matches how VOR data is keyed)
            player_key = pick.get('player_key', player_name)

            # Get display name from mapping
            display_name = player_id_to_name.get(player_key, player_name)

            drafting_owner = get_owner_name(pick['team']) if pick['team'] else 'Unknown'

            # Look at production in the draft year and all future years where the drafting
            # owner actually rostered the player.
            tenure_years = []
            tenure_vor = 0.0
            draft_year_vor = 0.0

            for candidate_year in YEARS:
                if candidate_year < year:
                    continue
                if candidate_year not in vor_data or player_key not in vor_data[candidate_year]:
                    continue

                owner_shares = owner_shares_by_year.get(candidate_year, {}).get(player_key, {})
                share = owner_shares.get(drafting_owner, 0.0)
                if share <= 0:
                    continue

                year_vor_value = vor_data[candidate_year][player_key]['vor'] * share
                tenure_vor += year_vor_value
                tenure_years.append(candidate_year)

                if candidate_year == year:
                    draft_year_vor = year_vor_value

            if not tenure_years:
                continue

            avg_tenure_vor = tenure_vor / len(tenure_years)
            draft_year_points = year_vor_lookup.get(player_key, {}).get('points', 0)

            round_num = pick['round'] if pick['round'] else 1
            is_keeper = pick['is_keeper']

            all_picks.append({
                'year': year,
                'player': display_name,  # Use display name for output
                'player_key': player_key,  # Keep key for internal lookups
                'round': round_num,
                'overall': pick['overall'],
                'vor': tenure_vor,
                'draft_year_vor': draft_year_vor,
                'avg_future_vor': avg_tenure_vor,
                'seasons_contributing': len(set(tenure_years)),
                'points': draft_year_points,
                'is_keeper': is_keeper,
                'team': drafting_owner
            })

    # Second pass: calculate round averages per year (excluding keepers for fair comparison)
    round_averages_by_year: Dict[int, Dict[int, float]] = {}
    
    for year in YEARS:
        year_picks = [p for p in all_picks if p['year'] == year and not p['is_keeper']]
        if not year_picks:
            continue
            
        round_vor_totals = defaultdict(list)
        for pick in year_picks:
            round_vor_totals[pick['round']].append(pick['vor'])
        
        round_averages_by_year[year] = {
            rnd: sum(vors) / len(vors)
            for rnd, vors in round_vor_totals.items()
            if vors
        }

    # Third pass: calculate value_score as delta vs round average
    for pick in all_picks:
        year = pick['year']
        round_num = pick['round']
        
        # For keepers, we don't have a meaningful "round average" comparison
        # since they're not competing for draft slots. Use raw VOR instead.
        if pick['is_keeper']:
            pick['round_average'] = 0
            pick['value_score'] = pick['vor']
        else:
            round_avg = round_averages_by_year.get(year, {}).get(round_num, 0)
            pick['round_average'] = round_avg
            pick['value_score'] = pick['vor'] - round_avg

    # Sort by value score (delta vs round average)
    all_picks.sort(key=lambda x: x['value_score'], reverse=True)

    return all_picks, round_averages_by_year


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
                # Use player_key for lookup (matches VOR data keys)
                player_key = pick.get('player_key', pick['player_name'])
                if player_key in year_vor:
                    vor = year_vor[player_key]['vor']
                    if pick['team']:
                        owner = get_owner_name(pick['team'])
                        keeper_values[owner] += vor

    return keeper_values


def calculate_draft_pick_value(all_data: Dict, vor_data: Dict) -> Dict[str, float]:
    """Calculate total non-keeper draft pick value for each manager.

    Attribution mirrors the tenure-based best-pick logic but only counts the
    draft-year value for non-keeper selections. If a player is later kept, the
    keeper-year VOR is excluded from this leaderboard; only the draft-year
    production that occurred while the drafting owner rostered the player is
    credited.
    """
    draft_values = defaultdict(float)
    owner_shares_by_year = build_player_owner_shares(all_data)

    for year in YEARS:
        if year not in all_data['draft_data'] or year not in vor_data:
            continue

        # Skip 2021 since that was year 1 (everyone drafted, no keepers to exclude)
        if year == 2021:
            continue

        draft = all_data['draft_data'][year]
        year_vor = vor_data[year]

        for pick in draft['picks']:
            if pick['is_keeper']:
                continue

            # Use player_key for lookup (matches VOR data keys)
            player_key = pick.get('player_key', pick['player_name'])
            if player_key not in year_vor:
                continue

            if not pick['team']:
                continue

            owner = get_owner_name(pick['team'])
            owner_shares = owner_shares_by_year.get(year, {}).get(player_key, {})
            share = owner_shares.get(owner, 0.0)

            if share <= 0:
                continue

            vor = year_vor[player_key]['vor'] * share
            draft_values[owner] += vor

    return draft_values


def build_draft_capital_lookup(all_data: Dict, vor_data: Dict) -> Dict[int, Dict[str, int]]:
    """
    Build a lookup of player_key -> draft capital value for each year.
    
    Draft capital uses inverse round number: Round 1 = 15 pts, Round 2 = 14 pts, etc.
    
    For keepers (2022+), we sort them by prior year VOR and assign synthetic rounds 1-6.
    For drafted players, we use their actual draft round.
    Undrafted/waiver players get value = 0.
    
    Returns:
        Dict of year -> player_key -> draft_capital_value
    """
    draft_capital = {}
    
    for year in YEARS:
        if year not in all_data['draft_data']:
            continue
            
        draft_capital[year] = {}
        draft = all_data['draft_data'][year]
        
        # Separate keepers and regular draft picks
        keepers = []
        regular_picks = []
        
        for pick in draft['picks']:
            player_key = pick.get('player_key')
            if not player_key:
                continue
                
            if pick['is_keeper']:
                keepers.append(pick)
            else:
                regular_picks.append(pick)
        
        # Handle keepers: sort by prior year VOR and assign synthetic rounds 1-6
        if keepers and year > 2021 and (year - 1) in vor_data:
            prior_year_vor = vor_data[year - 1]
            
            # Get prior year VOR for each keeper
            keeper_vor_list = []
            for pick in keepers:
                player_key = pick.get('player_key')
                prior_vor = prior_year_vor.get(player_key, {}).get('vor', 0)
                keeper_vor_list.append({
                    'player_key': player_key,
                    'prior_vor': prior_vor,
                    'player_name': pick.get('player_name')
                })
            
            # Sort by prior VOR descending (best keeper = round 1)
            keeper_vor_list.sort(key=lambda x: x['prior_vor'], reverse=True)
            
            # Assign synthetic rounds 1-6
            for i, keeper in enumerate(keeper_vor_list):
                synthetic_round = i + 1  # 1, 2, 3, 4, 5, 6
                # Inverse round: Round 1 = 15, Round 6 = 10
                capital_value = max(1, 16 - synthetic_round)
                draft_capital[year][keeper['player_key']] = capital_value
        
        # Handle regular draft picks (rounds 7+)
        for pick in regular_picks:
            player_key = pick.get('player_key')
            if not player_key:
                continue
            round_num = pick.get('round', 15)
            # Inverse round: Round 7 = 9, Round 15 = 1
            capital_value = max(1, 16 - round_num)
            draft_capital[year][player_key] = capital_value
    
    return draft_capital


def calculate_weighted_injury_impact(all_data: Dict, vor_data: Dict) -> Dict:
    """
    Calculate weighted injury impact for each manager.
    
    This weights injuries by draft capital (inverse round number) to capture
    that losing a 1st round pick hurts more than losing a waiver pickup.
    
    Also detects season-ending injuries where a player was dropped while injured
    and never played again that season.
    
    Returns:
        Dict with:
        - 'manager_scores': {manager -> total weighted injury score}
        - 'most_costly': {manager -> {player_name, total_impact, weeks, draft_capital, year}}
        - 'season_ending': {manager -> list of season-ending injuries detected}
    """
    draft_capital = build_draft_capital_lookup(all_data, vor_data)
    player_id_to_name = all_data.get('player_id_to_name', {})
    
    manager_scores = defaultdict(float)
    # Track per-year, per-player injuries to handle draft capital correctly
    # Structure: manager -> (year, player_key) -> injury info
    player_injury_totals = defaultdict(lambda: defaultdict(lambda: {
        'weeks': 0,
        'draft_capital': 0,
        'player_name': '',
        'player_key': '',
        'year': 0
    }))
    season_ending_injuries = defaultdict(list)
    
    for year in YEARS:
        if year not in all_data['injury_details']:
            continue
            
        year_capital = draft_capital.get(year, {})
        total_weeks = all_data['season_weeks'].get(year, 14)
        
        # Determine the last week we actually have data for this year
        # This handles incomplete/in-progress seasons
        weeks_with_data = set()
        for week in all_data['weekly_rosters'].get(year, {}).keys():
            weeks_with_data.add(week)
        last_week_with_data = max(weeks_with_data) if weeks_with_data else 0
        
        # Check if season is complete (we have data for all regular season weeks)
        season_complete = last_week_with_data >= total_weeks
        
        # First pass: count regular injury weeks (while on roster)
        for owner, injuries in all_data['injury_details'][year].items():
            for injury in injuries:
                player_key = injury['player_key']
                player_name = injury['player_name']
                
                # Get draft capital for THIS year (0 for undrafted/waiver)
                capital = year_capital.get(player_key, 0)
                
                if capital > 0:  # Only count drafted players
                    manager_scores[owner] += capital
                    
                    # Track per-year, per-player totals for "most costly" calculation
                    key = (year, player_key)
                    player_injury_totals[owner][key]['weeks'] += 1
                    player_injury_totals[owner][key]['draft_capital'] = capital
                    player_injury_totals[owner][key]['player_name'] = player_name
                    player_injury_totals[owner][key]['player_key'] = player_key
                    player_injury_totals[owner][key]['year'] = year
        
        # Second pass: detect season-ending injuries (dropped while injured, never played again)
        # Only do this for COMPLETE seasons to avoid false positives
        if not season_complete:
            continue
            
        for owner, injuries in all_data['injury_details'][year].items():
            # Group injuries by player to find their last injured week with this owner
            player_last_injured_week = defaultdict(int)
            player_names = {}
            
            for injury in injuries:
                player_key = injury['player_key']
                week = injury['week']
                if week > player_last_injured_week[player_key]:
                    player_last_injured_week[player_key] = week
                    player_names[player_key] = injury['player_name']
            
            # For each player, check if they were on roster after their last injured week
            for player_key, last_injured_week in player_last_injured_week.items():
                capital = year_capital.get(player_key, 0)
                if capital == 0:
                    continue  # Skip undrafted players
                
                # Skip if already at end of season (no remaining weeks to credit)
                if last_injured_week >= total_weeks:
                    continue
                
                # Check if player was on this owner's roster in any subsequent week
                was_kept = False
                for check_week in range(last_injured_week + 1, total_weeks + 1):
                    week_rosters = all_data['weekly_rosters'].get(year, {}).get(check_week, {})
                    if player_key in week_rosters.get(owner, set()):
                        was_kept = True
                        break
                
                if was_kept:
                    continue  # Player stayed on roster, not a season-ender
                
                # Player was dropped - check if they ever played again (scored points for anyone)
                played_again = False
                for check_week in range(last_injured_week + 1, total_weeks + 1):
                    week_points = all_data['weekly_player_points'].get(year, {}).get(check_week, {})
                    if week_points.get(player_key, 0) > 0:
                        played_again = True
                        break
                
                if not played_again:
                    # Season-ending injury detected!
                    # Credit only the weeks AFTER they were dropped (not already counted)
                    remaining_weeks = total_weeks - last_injured_week
                    additional_impact = remaining_weeks * capital
                    
                    manager_scores[owner] += additional_impact
                    
                    # Add to the per-year tracking
                    key = (year, player_key)
                    player_injury_totals[owner][key]['weeks'] += remaining_weeks
                    
                    season_ending_injuries[owner].append({
                        'player_key': player_key,
                        'player_name': player_names.get(player_key, player_id_to_name.get(player_key, player_key)),
                        'last_rostered_week': last_injured_week,
                        'remaining_weeks': remaining_weeks,
                        'additional_impact': additional_impact,
                        'year': year
                    })
    
    # Calculate most costly injury per manager (across all years)
    most_costly = {}
    for owner, year_players in player_injury_totals.items():
        max_impact = 0
        worst_injury = None
        
        for (year, player_key), info in year_players.items():
            total_impact = info['weeks'] * info['draft_capital']
            if total_impact > max_impact:
                max_impact = total_impact
                worst_injury = {
                    'player_name': info['player_name'],
                    'player_key': player_key,
                    'weeks': info['weeks'],
                    'draft_capital': info['draft_capital'],
                    'total_impact': total_impact,
                    'year': year
                }
        
        if worst_injury:
            most_costly[owner] = worst_injury
    
    return {
        'manager_scores': dict(manager_scores),
        'most_costly': most_costly,
        'season_ending': dict(season_ending_injuries)
    }


def find_most_valuable_player(vor_data: Dict) -> Tuple[str, int, Dict]:
    """Find the single most valuable player across all seasons."""
    max_vor = 0
    mvp = None
    mvp_year = None
    mvp_info = None

    for year, year_vor in vor_data.items():
        for player_key, data in year_vor.items():
            if data['vor'] > max_vor:
                max_vor = data['vor']
                # Use display name from data
                mvp = data.get('name', player_key)
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
    for player_key, seasons in all_data['player_seasons'].items():
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
        'player_id': None,
        'name': None  # Track display name
    })

    # Aggregate VOR across all years
    for year, year_vor in vor_data.items():
        for player_key, data in year_vor.items():
            player_stats[player_key]['total_vor'] += data['vor']
            player_stats[player_key]['seasons_played'] += 1
            player_stats[player_key]['years'].append(year)
            player_stats[player_key]['positions'].add(data['position'])
            if data.get('player_id') and not player_stats[player_key]['player_id']:
                player_stats[player_key]['player_id'] = data['player_id']
            # Update name (use most recent)
            if data.get('name'):
                player_stats[player_key]['name'] = data['name']

    # Calculate totals and averages
    total_vor_list = []
    average_vor_list = []

    for player_key, stats in player_stats.items():
        total_vor = stats['total_vor']
        seasons = stats['seasons_played']
        avg_vor = total_vor / seasons if seasons > 0 else 0

        # Get primary position (most common)
        position = list(stats['positions'])[0] if stats['positions'] else 'UNKNOWN'
        
        # Get display name, fall back to player_key if not available
        display_name = stats['name'] if stats['name'] else player_key

        player_data = {
            'player': display_name,  # Use display name
            'player_key': player_key,  # Keep key for lookups
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
        for player_key, data in year_vor.items():
            # Use display name from data
            display_name = data.get('name', player_key)
            all_player_seasons.append({
                'player': display_name,
                'player_key': player_key,
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

    for team, stats in sorted(team_stats.items(), key=lambda x: x[1]['total_points_for'], reverse=True):
        teams.append(team)
        total_points.append(stats['total_points_for'])
        points_against.append(stats['total_points_against'])

        total_games = stats['wins'] + stats['losses'] + stats['ties']
        win_pct = (stats['wins'] + 0.5 * stats['ties']) / total_games if total_games > 0 else 0
        win_pcts.append(win_pct * 100)

        championships.append(stats['championships'])

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

    # 5. Championships
    ax5 = plt.subplot(2, 3, 5)
    x = np.arange(len(teams))

    bars_champ = ax5.bar(x, championships, label='Championships',
                        color='gold', edgecolor='black', linewidth=1.5)

    ax5.set_ylabel('Count', fontsize=10, fontweight='bold')
    ax5.set_title('Championships', fontsize=12, fontweight='bold', pad=10)
    ax5.set_xticks(x)
    ax5.set_xticklabels(teams, rotation=45, ha='right', fontsize=8)
    ax5.grid(True, axis='y', alpha=0.3)

    # Add value labels
    for bar in bars_champ:
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


def save_structured_data(payload: Dict[str, Any]) -> None:
    """Persist structured outputs for downstream analysis."""
    try:
        with open('fantasy_wrapped_data.json', 'w') as f:
            json.dump(payload, f, indent=2)

        if payload.get('best_picks'):
            pd.DataFrame(payload['best_picks']).to_csv(
                'fantasy_wrapped_best_picks.csv', index=False
            )

        if payload.get('best_pick_by_year'):
            pd.DataFrame(payload['best_pick_by_year']).to_csv(
                'fantasy_wrapped_best_pick_by_year.csv', index=False
            )

        print("\nStructured data saved to: fantasy_wrapped_data.json, "
              "fantasy_wrapped_best_picks.csv, and fantasy_wrapped_best_pick_by_year.csv")
    except Exception as e:
        print(f"\nWarning: Unable to save structured data: {e}")


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

    generated_at = datetime.now()
    
    # Calculate VOR early since it's needed by multiple sections
    vor_data = calculate_value_over_replacement(all_data)

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
    report.append(f"📈 ALL-TIME SCORING LEADER: {scoring_leader[0]}")
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
    report.append(f"😬 UNLUCKIEST MANAGER: {unluckiest[0]}")
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

    report.append(f"🥇 BEST ALL-TIME RECORD: {best_record_team[0]}")
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

    # ========================================
    # SCORING & MATCHUP AWARDS
    # ========================================

    # Offensive Explosion
    explosion = find_offensive_explosion(all_data['matchups'])
    if explosion:
        report.append(f"💥 OFFENSIVE EXPLOSION (Highest Single Week): {explosion['manager']}")
        report.append(f"   Score: {explosion['score']:.2f}")
        report.append(f"   When: {explosion['year']} Week {explosion['week']}")
        report.append(f"   vs {explosion['opponent']} ({explosion['opponent_score']:.2f})")
        report.append("")

    # Offensive Dud
    dud = find_offensive_dud(all_data['matchups'])
    if dud:
        report.append(f"💀 OFFENSIVE DUD (Lowest Single Week): {dud['manager']}")
        report.append(f"   Score: {dud['score']:.2f}")
        report.append(f"   When: {dud['year']} Week {dud['week']}")
        report.append(f"   vs {dud['opponent']} ({dud['opponent_score']:.2f})")
        report.append("")

    # Heartbreaker
    heartbreaker = calculate_heartbreaker_award(all_data['matchups'])
    if heartbreaker:
        report.append(f"💔 HEARTBREAKER (Most Losses by <5 Points): {heartbreaker['manager']}")
        report.append(f"   Close Losses: {heartbreaker['count']}")
        if heartbreaker['close_losses']:
            # Show a few examples
            report.append("   Recent heartbreaks:")
            for loss in heartbreaker['close_losses'][-3:]:
                report.append(f"     {loss['year']} Wk{loss['week']}: Lost {loss['score']:.2f}-{loss['opponent_score']:.2f} "
                             f"vs {loss['opponent']} (margin: {loss['margin']:.2f})")
        report.append("")

    # Win and Loss Streaks
    streaks = calculate_win_loss_streaks(all_data['matchups'])
    if streaks['longest_win_streak']:
        ws = streaks['longest_win_streak']
        report.append(f"🔥 LONGEST WIN STREAK: {ws['manager']}")
        report.append(f"   {ws['count']} wins in a row")
        report.append(f"   {ws['start_year']} Week {ws['start_week']} - {ws['end_year']} Week {ws['end_week']}")
        report.append("")

    if streaks['longest_loss_streak']:
        ls = streaks['longest_loss_streak']
        report.append(f"😭 LONGEST LOSING STREAK: {ls['manager']}")
        report.append(f"   {ls['count']} losses in a row")
        report.append(f"   {ls['start_year']} Week {ls['start_week']} - {ls['end_year']} Week {ls['end_week']}")
        report.append("")

    # Unlucky Loser
    unlucky = calculate_unlucky_loser(all_data['matchups'])
    if unlucky:
        report.append(f"😤 UNLUCKY LOSER (Most Points in Losses): {unlucky['manager']}")
        report.append(f"   Total Points in Losses: {unlucky['total_points_in_losses']:.2f}")
        report.append(f"   Losses: {unlucky['loss_count']}")
        report.append(f"   Average Points in Losses: {unlucky['avg_points_in_losses']:.2f}")
        report.append("")

    # Bad Beat
    bad_beat = calculate_bad_beat(all_data['matchups'])
    if bad_beat:
        report.append(f"🎰 BAD BEAT (2nd Highest Score but Lost): {bad_beat['manager']}")
        report.append(f"   Score: {bad_beat['score']:.2f}")
        report.append(f"   When: {bad_beat['year']} Week {bad_beat['week']}")
        report.append(f"   Lost to {bad_beat['opponent']} ({bad_beat['opponent_score']:.2f})")
        report.append(f"   Week's top score: {bad_beat['top_scorer']} ({bad_beat['top_score']:.2f})")
        report.append("")

    # Late Round Legend
    late_legend = calculate_late_round_legend(all_data, vor_data)
    if late_legend:
        report.append(f"💎 LATE ROUND LEGEND (Best Pick Rd 12+): {late_legend['player']}")
        report.append(f"   Drafted by: {late_legend['manager']}")
        report.append(f"   {late_legend['year']} - Round {late_legend['round']}, Pick {late_legend['pick']}")
        report.append(f"   Value Over Replacement: {late_legend['vor']:.2f}")
        report.append("")

    # Punt God Award
    punt_god, punt_god_points, punt_breakdown = calculate_punt_god(all_data)
    if punt_god:
        report.append(f"🦵 PUNT GOD (Most D/ST, K, P Points): {punt_god}")
        report.append(f"   Total Special Teams Points: {punt_god_points:.2f}")
        report.append(f"   Defense/ST: {punt_breakdown['D/ST']:.2f} | "
                     f"Kicker: {punt_breakdown['K']:.2f} | "
                     f"Punter: {punt_breakdown['P']:.2f}")
        report.append("")

    # ========================================
    # INJURY ANALYSIS
    # ========================================
    report.append("=" * 80)
    report.append("🩺 INJURY ANALYSIS")
    report.append("=" * 80)
    report.append("")

    most_injured = max(team_stats.items(), key=lambda x: x[1]['injury_weeks'])
    report.append(f"🤒 MOST INJURED TEAM: {most_injured[0]}")
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
    # WEIGHTED INJURY IMPACT
    # ========================================
    report.append("=" * 80)
    report.append("💸 INJURY IMPACT (Draft Capital Weighted)")
    report.append("=" * 80)
    report.append("")
    
    report.append("Draft capital = inverse round (Rd 1 = 15 pts, Rd 15 = 1 pt)")
    report.append("Keepers ranked by prior year VOR and assigned rounds 1-6")
    report.append("Undrafted/waiver players excluded")
    report.append("")
    
    weighted_injury_data = calculate_weighted_injury_impact(all_data, vor_data)

    weighted_scores = weighted_injury_data['manager_scores']
    if weighted_scores:
        report.append("WEIGHTED INJURY SCORE RANKINGS:")
        for i, (manager, score) in enumerate(sorted(weighted_scores.items(),
                                                    key=lambda x: x[1],
                                                    reverse=True), 1):
            report.append(f"  {i:2d}. {manager:30s} Weighted Injury Score: {score:.0f}")
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
            report.append(f"  👿 Nemesis: {nem['opponent']}")
            report.append(f"     Scored {nem['avg_points_against']:.1f} pts/game against you "
                         f"({nem['total_points_against']:.1f} total, {nem['games']} games)")
            report.append(f"     Your record vs them: {nem['record']}")

        # Victim (who they crushed the most)
        if data['victim']:
            vic = data['victim']
            report.append(f"  🏹 Victim: {vic['opponent']}")
            report.append(f"     You scored {vic['avg_points_for']:.1f} pts/game against them "
                         f"({vic['total_points_for']:.1f} total, {vic['games']} games)")
            report.append(f"     Your record vs them: {vic['record']}")

        report.append("")

    # Add head-to-head matrix
    h2h_matrix = generate_h2h_matrix(h2h_stats)
    report.extend(h2h_matrix)

    # ========================================
    # PLAYER DEEP DIVE
    # ========================================
    report.append("=" * 80)
    report.append("🔍 PLAYER DEEP DIVE")
    report.append("=" * 80)
    report.append("")

    # Most Valuable Player (Single Season)
    mvp, mvp_year, mvp_info = find_most_valuable_player(vor_data)
    report.append(f"🏅 MOST VALUABLE PLAYER (Single Season): {mvp}")
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
        report.append(f"🏅 MOST VALUABLE PLAYER (5-Year Average VOR): {top_avg['player']}")
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

    # Top 10 by Average VOR (minimum 2 seasons to qualify)
    report.append("TOP 10 PLAYERS BY 5-YEAR AVERAGE VOR (Min. 2 Seasons):")
    qualified_avg_vor = [p for p in avg_vor_rankings if p['seasons_played'] >= 2]
    for i, player_data in enumerate(qualified_avg_vor[:10], 1):
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
        for player_key, data in year_vor.items():
            display_name = data.get('name', player_key)
            all_player_seasons.append({
                'player': display_name,
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
    best_picks, round_average_by_year = find_best_draft_picks(all_data, vor_data)

    report.append("🎯 BEST DRAFT PICKS (By Δ vs Round Average):")
    non_keeper_picks = [p for p in best_picks if not p['is_keeper']][:10]
    for i, pick in enumerate(non_keeper_picks, 1):
        report.append(f"  {i:2d}. {pick['player']:25s} ({pick['year']}) - "
                     f"Rd {pick['round']:2d} - VOR: {pick['vor']:6.2f} "
                     f"(Round Avg: {pick['round_average']:6.2f}) - "
                     f"Î”: +{pick['value_score']:6.2f} - {pick['team']}")
    report.append("")

    # Best Draft Pick by Year
    report.append("BEST DRAFT PICK BY YEAR (vs Round Average):")
    best_pick_by_year = []
    for year in YEARS:
        year_picks = [p for p in best_picks if p['year'] == year and not p['is_keeper']]
        if not year_picks:
            continue

        # Find the best pick for this year (highest value_score = delta vs round avg)
        best = max(year_picks, key=lambda p: p['value_score'])

        best_pick_by_year.append({
            'year': year,
            'player': best['player'],
            'round': best['round'],
            'vor': best['vor'],
            'round_average_vor': best['round_average'],
            'delta_vs_round': best['value_score'],
            'seasons_contributing': best['seasons_contributing'],
            'team': best['team']
        })

        report.append(
            f"  {year}: {best['player']:25s} - Rd {best['round']:2d} - "
            f"VOR: {best['vor']:6.2f} (Round Avg: {best['round_average']:6.2f}) - "
            f"Î”: +{best['value_score']:6.2f} - Seasons: {best['seasons_contributing']:2d} - {best['team']}"
        )
    report.append("")

    # Keeper Value
    keeper_values = calculate_keeper_value(all_data, vor_data)
    report.append("📈 MOST VALUE FROM KEEPERS:")
    for i, (team, value) in enumerate(sorted(keeper_values.items(),
                                             key=lambda x: x[1],
                                             reverse=True), 1):
        report.append(f"  {i:2d}. {team:30s} Total Keeper VOR: {value:.2f}")
    report.append("")

    # Draft Pick Value (non-keepers, years 2-5)
    draft_values = calculate_draft_pick_value(all_data, vor_data)
    report.append("📊 MOST VALUE FROM DRAFT PICKS (Non-Keepers, 2022-2025):")
    for i, (team, value) in enumerate(sorted(draft_values.items(),
                                             key=lambda x: x[1],
                                             reverse=True), 1):
        report.append(f"  {i:2d}. {team:30s} Total Draft Pick VOR: {value:.2f}")
    report.append("")

    # ========================================
    # FOOTER
    # ========================================
    report.append("=" * 80)
    report.append(f"Generated on {generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)

    # Write to file
    with open('fantasy_wrapped_report.txt', 'w') as f:
        f.write('\n'.join(report))

    print("\nReport saved to: fantasy_wrapped_report.txt")

    save_structured_data({
        'generated_at': generated_at.isoformat(),
        'best_picks': best_picks,
        'best_pick_by_year': best_pick_by_year,
        'round_average_vor_by_year': {
            year: {str(rnd): avg for rnd, avg in round_map.items()}
            for year, round_map in round_average_by_year.items()
        }
    })

    # Also print to console
    print("\n" + '\n'.join(report))


# ========================================
# MAIN EXECUTION
# ========================================

def main():
    """Main execution function."""
    load_configuration()

    year_span = f"{min(YEARS)}-{max(YEARS)}" if YEARS else "No years configured"
    print("=" * 80)
    print(" ESPN Fantasy Football Wrapped".center(80))
    print(f" Analyzing League History ({year_span})".center(80))
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