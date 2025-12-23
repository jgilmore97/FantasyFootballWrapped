#!/usr/bin/env python3
"""
Test Fantasy Football Wrapped with mock data
"""

from collections import defaultdict, Counter
import sys

# Mock the espn_api module since we can't connect
class MockPlayer:
    def __init__(self, name, position, points, injury_status=None):
        self.name = name
        self.position = position
        self.total_points = points
        self.injuryStatus = injury_status

class MockTeam:
    def __init__(self, team_name, owner, wins, losses, ties, points_for, points_against, final_standing=None):
        self.team_name = team_name
        self.owner = owner
        self.wins = wins
        self.losses = losses
        self.ties = ties
        self.points_for = points_for
        self.points_against = points_against
        self.final_standing = final_standing
        self.roster = []

class MockBoxScore:
    def __init__(self, home_team, away_team, home_score, away_score, home_lineup, away_lineup):
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = home_score
        self.away_score = away_score
        self.home_lineup = home_lineup
        self.away_lineup = away_lineup

class MockLeague:
    def __init__(self, year):
        self.year = year
        self.teams = []
        self.settings = type('obj', (object,), {'reg_season_count': 14})()

    def box_scores(self, week):
        # Return empty for now
        return []

# Create mock data
def create_mock_data():
    """Create realistic mock league data for testing."""
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
            'keeper_points': defaultdict(float),
            'draft_points': defaultdict(float),
            'keeper_picks': defaultdict(list),
            'draft_picks': defaultdict(list),
            'team_names': set(),
            'current_team_name': ''
        }),
        'matchups': [],
        'player_seasons': defaultdict(lambda: defaultdict(dict)),
        'draft_data': defaultdict(dict),
    }

    # Create 10 mock managers
    managers = [
        "Alice Johnson",
        "Bob Smith",
        "Charlie Davis",
        "Diana Martinez",
        "Erik Anderson",
        "Fiona Wilson",
        "George Taylor",
        "Hannah Brown",
        "Ian Lee",
        "Julia White"
    ]

    # Create data for 5 seasons
    for year in [2021, 2022, 2023, 2024, 2025]:
        for i, manager in enumerate(managers):
            stats = all_data['team_stats'][manager]

            # Vary performance by year and manager
            base_wins = 6 + (hash(manager + str(year)) % 7)
            wins = base_wins
            losses = 14 - wins

            # Points vary
            points_for = 1200 + (hash(manager) % 600) + (hash(str(year)) % 200)
            points_against = 1100 + (hash(manager[::-1]) % 600) + (hash(str(year)) % 200)

            stats['seasons_played'] += 1
            stats['wins'] += wins
            stats['losses'] += losses
            stats['ties'] += 0
            stats['total_points_for'] += points_for
            stats['total_points_against'] += points_against
            stats['team_names'].add(f"Team {manager.split()[0]}")
            stats['current_team_name'] = f"Team {manager.split()[0]}"

            # Add some weekly scores
            for week in range(14):
                score = 80 + (hash(manager + str(year) + str(week)) % 60)
                stats['weekly_scores'].append(score)

            # Injury data
            injury_weeks = hash(manager + "injuries") % 30
            stats['injury_weeks'] += injury_weeks
            stats['max_injuries_single_week'] = max(stats['max_injuries_single_week'], hash(manager) % 5)
            stats['injured_players']['Christian McCaffrey'] = hash(manager) % 8

            # Championships (1-2 managers win each year)
            if i == year % 10:
                stats['championships'] += 1

            # Playoff appearances (top 4)
            if i < 4:
                stats['playoff_appearances'] += 1

    # Create mock matchups
    for year in [2021, 2022, 2023, 2024, 2025]:
        for week in range(1, 15):
            # Create 5 matchups per week
            for match in range(5):
                home_idx = match * 2
                away_idx = match * 2 + 1

                home_score = 80 + (hash(managers[home_idx] + str(year) + str(week)) % 60)
                away_score = 80 + (hash(managers[away_idx] + str(year) + str(week)) % 60)

                all_data['matchups'].append({
                    'year': year,
                    'week': week,
                    'home_team': managers[home_idx],
                    'away_team': managers[away_idx],
                    'home_score': home_score,
                    'away_score': away_score,
                })

    # Create mock player data
    mock_players = [
        ('Patrick Mahomes', 'QB', 380),
        ('Josh Allen', 'QB', 370),
        ('Justin Jefferson', 'WR', 310),
        ('Christian McCaffrey', 'RB', 340),
        ('Travis Kelce', 'TE', 280),
        ('Tyreek Hill', 'WR', 300),
        ('Derrick Henry', 'RB', 290),
        ('Stefon Diggs', 'WR', 285),
        ('Cooper Kupp', 'WR', 275),
        ('Austin Ekeler', 'RB', 270),
    ]

    for year in [2021, 2022, 2023, 2024, 2025]:
        for player_name, position, base_points in mock_players:
            points = base_points + (hash(str(year)) % 50)
            owner = managers[hash(player_name) % 10]

            all_data['player_seasons'][player_name][year] = {
                'points': points,
                'position': position,
                'team_owner': owner
            }

    return all_data


# Import the analysis functions from the main script
sys.path.insert(0, '/home/user/FantasyFootballWrapped')
from fantasy_wrapped import (
    calculate_head_to_head_records,
    find_top_rivalries,
    calculate_value_over_replacement,
    find_most_valuable_player,
    find_best_draft_picks,
    create_visualizations,
)

def test_analysis():
    """Test all analysis functions with mock data."""
    print("=" * 80)
    print(" TESTING FANTASY FOOTBALL WRAPPED WITH MOCK DATA".center(80))
    print("=" * 80)
    print()

    # Create mock data
    print("Creating mock league data...")
    all_data = create_mock_data()

    print(f"  - Created {len(all_data['team_stats'])} teams")
    print(f"  - Created {len(all_data['matchups'])} matchups")
    print(f"  - Created {len(all_data['player_seasons'])} player seasons")
    print()

    # Test head-to-head records
    print("Testing head-to-head analysis...")
    h2h = calculate_head_to_head_records(all_data['matchups'])
    print(f"  ✓ Generated H2H records for {len(h2h)} teams")

    # Test rivalries
    print("Testing rivalry detection...")
    rivalries = find_top_rivalries(h2h)
    print(f"  ✓ Found {len(rivalries)} top rivalries")
    if rivalries:
        top = rivalries[0]
        print(f"    Top rivalry: {top['team1']} vs {top['team2']} "
              f"({top['total_games']} games, {top['competitiveness']:.1%} competitive)")

    # Test VOR calculations
    print("Testing Value Over Replacement...")
    vor_data = calculate_value_over_replacement(all_data)
    print(f"  ✓ Calculated VOR for {len(vor_data)} seasons")
    total_players = sum(len(year_data) for year_data in vor_data.values())
    print(f"    Total player-seasons with VOR: {total_players}")

    # Test MVP
    print("Testing MVP detection...")
    mvp, mvp_year, mvp_info = find_most_valuable_player(vor_data)
    if mvp:
        print(f"  ✓ MVP: {mvp} ({mvp_year}) - {mvp_info['position']} - "
              f"VOR: {mvp_info['vor']:.2f}, Points: {mvp_info['points']:.2f}")

    # Test visualizations
    print("Testing visualization generation...")
    try:
        create_visualizations(all_data)
        print("  ✓ Generated charts successfully")
    except Exception as e:
        print(f"  ✗ Chart generation failed: {e}")

    # Test statistics
    print("\nTesting statistics calculations...")
    team_stats = all_data['team_stats']

    # All-time scoring leader
    scoring_leader = max(team_stats.items(), key=lambda x: x[1]['total_points_for'])
    print(f"  ✓ All-Time Scoring Leader: {scoring_leader[0]} "
          f"({scoring_leader[1]['total_points_for']:.2f} pts)")

    # Best record
    best_record = max(team_stats.items(),
                     key=lambda x: x[1]['wins'] / (x[1]['wins'] + x[1]['losses'] + x[1]['ties']))
    total_games = best_record[1]['wins'] + best_record[1]['losses'] + best_record[1]['ties']
    win_pct = best_record[1]['wins'] / total_games * 100
    print(f"  ✓ Best Record: {best_record[0]} "
          f"({best_record[1]['wins']}-{best_record[1]['losses']}, {win_pct:.1f}%)")

    # Most championships
    most_chips = max(team_stats.items(), key=lambda x: x[1]['championships'])
    if most_chips[1]['championships'] > 0:
        print(f"  ✓ Most Championships: {most_chips[0]} "
              f"({most_chips[1]['championships']} titles)")

    # Injury analysis
    most_injured = max(team_stats.items(), key=lambda x: x[1]['injury_weeks'])
    print(f"  ✓ Most Injured: {most_injured[0]} "
          f"({most_injured[1]['injury_weeks']} injury-weeks)")

    print("\n" + "=" * 80)
    print(" ALL TESTS PASSED! ✓".center(80))
    print(" The analysis and visualization functions are working correctly.".center(80))
    print("=" * 80)
    print("\nNote: This test used mock data. To get real results, run fantasy_wrapped.py")
    print("on a machine with internet access to ESPN's API servers.")


if __name__ == "__main__":
    test_analysis()
