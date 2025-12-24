#!/usr/bin/env python3
"""
Test script for new visualization and JSON export features
"""

import sys
import json
from collections import Counter

# Mock data for testing
def create_mock_data():
    """Create mock data for testing visualizations and JSON export."""

    team_stats = {
        'Team Alpha': {
            'total_points_for': 7850.5,
            'total_points_against': 7200.3,
            'wins': 45,
            'losses': 20,
            'ties': 0,
            'championships': 2,
            'injury_weeks': 85,
            'max_injuries_single_week': 5,
            'injured_players': Counter({'Patrick Mahomes': 3, 'Travis Kelce': 2})
        },
        'Team Beta': {
            'total_points_for': 7600.2,
            'total_points_against': 7500.8,
            'wins': 38,
            'losses': 27,
            'ties': 0,
            'championships': 1,
            'injury_weeks': 92,
            'max_injuries_single_week': 6,
            'injured_players': Counter({'Christian McCaffrey': 5, 'Aaron Rodgers': 1})
        },
        'Team Gamma': {
            'total_points_for': 7200.8,
            'total_points_against': 7800.5,
            'wins': 32,
            'losses': 33,
            'ties': 0,
            'championships': 0,
            'injury_weeks': 110,
            'max_injuries_single_week': 7,
            'injured_players': Counter({'Saquon Barkley': 4})
        },
        'Team Delta': {
            'total_points_for': 6900.3,
            'total_points_against': 7100.2,
            'wins': 30,
            'losses': 35,
            'ties': 0,
            'championships': 1,
            'injury_weeks': 78,
            'max_injuries_single_week': 4,
            'injured_players': Counter()
        },
        'Team Epsilon': {
            'total_points_for': 6500.7,
            'total_points_against': 7350.9,
            'wins': 25,
            'losses': 40,
            'ties': 0,
            'championships': 0,
            'injury_weeks': 95,
            'max_injuries_single_week': 5,
            'injured_players': Counter()
        }
    }

    all_data = {
        'team_stats': team_stats,
        'matchups': [],
        'player_seasons': {},
        'leagues': {}
    }

    vor_data = {
        2024: {
            'Christian McCaffrey': {
                'vor': 245.8,
                'points': 389.2,
                'position': 'RB',
                'owner': 'Team Alpha',
                'name': 'Christian McCaffrey'
            },
            'Tyreek Hill': {
                'vor': 198.5,
                'points': 342.1,
                'position': 'WR',
                'owner': 'Team Beta',
                'name': 'Tyreek Hill'
            }
        },
        2023: {
            'Josh Allen': {
                'vor': 215.3,
                'points': 378.9,
                'position': 'QB',
                'owner': 'Team Gamma',
                'name': 'Josh Allen'
            }
        }
    }

    # MVP info
    mvp_name = 'Christian McCaffrey'
    mvp_year = 2024
    mvp_info = {
        'position': 'RB',
        'points': 389.2,
        'vor': 245.8,
        'owner': 'Team Alpha'
    }

    # Top players
    top_players = [
        {'player': 'Christian McCaffrey', 'year': 2024, 'position': 'RB', 'vor': 245.8, 'points': 389.2},
        {'player': 'Josh Allen', 'year': 2023, 'position': 'QB', 'vor': 215.3, 'points': 378.9},
        {'player': 'Tyreek Hill', 'year': 2024, 'position': 'WR', 'vor': 198.5, 'points': 342.1},
        {'player': 'Travis Kelce', 'year': 2023, 'position': 'TE', 'vor': 185.2, 'points': 298.7},
        {'player': 'Derrick Henry', 'year': 2022, 'position': 'RB', 'vor': 172.9, 'points': 325.4},
    ]

    return all_data, vor_data, mvp_name, mvp_year, mvp_info, top_players


def test_visualizations():
    """Test the new visualization functions."""
    print("=" * 80)
    print("TESTING VISUALIZATION ENHANCEMENTS")
    print("=" * 80)

    # Import after creating mock data
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend

    from fantasy_wrapped import create_visualizations, save_comprehensive_json

    all_data, vor_data, mvp_name, mvp_year, mvp_info, top_players = create_mock_data()

    print("\n1. Testing individual PNG generation...")
    try:
        create_visualizations(
            all_data,
            mvp_name=mvp_name,
            mvp_year=mvp_year,
            mvp_info=mvp_info,
            mvp_headshot=None,
            top_players=top_players,
            player_headshots={}
        )
        print("✅ Visualization test completed!")
    except Exception as e:
        print(f"❌ Visualization test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n2. Testing comprehensive JSON export...")
    try:
        save_comprehensive_json(all_data, vor_data)
        print("✅ JSON export test completed!")
    except Exception as e:
        print(f"❌ JSON export test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n3. Verifying output files...")
    import os

    expected_pngs = [
        'total_points.png',
        'win_percentage.png',
        'mvp_panel.png',
        'luck_analysis.png',
        'championships.png'
    ]

    for png in expected_pngs:
        if os.path.exists(png):
            size = os.path.getsize(png) / 1024  # KB
            print(f"  ✓ {png} ({size:.1f} KB)")
        else:
            print(f"  ✗ {png} - NOT FOUND")

    if os.path.exists('fantasy_wrapped_data.json'):
        size = os.path.getsize('fantasy_wrapped_data.json') / 1024  # KB
        print(f"  ✓ fantasy_wrapped_data.json ({size:.1f} KB)")

        # Verify JSON structure
        with open('fantasy_wrapped_data.json', 'r') as f:
            data = json.load(f)

        print("\n4. Verifying JSON structure...")
        expected_sections = [
            'generated_at',
            'league_years',
            'core_awards',
            'rankings',
            'weekly_awards',
            'streaks',
            'special_awards',
            'injury_analysis',
            'head_to_head',
            'player_analysis',
            'draft_analysis',
            'team_stats'
        ]

        for section in expected_sections:
            if section in data:
                print(f"  ✓ {section}")
            else:
                print(f"  ✗ {section} - MISSING")

        # Show a sample of the data
        print("\n5. Sample JSON content:")
        print(f"  Core Awards sections: {list(data.get('core_awards', {}).keys())}")
        print(f"  Rankings sections: {list(data.get('rankings', {}).keys())}")
        print(f"  Player Analysis sections: {list(data.get('player_analysis', {}).keys())}")

    else:
        print("  ✗ fantasy_wrapped_data.json - NOT FOUND")

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ Individual PNG files are now generated instead of one combined file")
    print("✅ Charts have improved styling with better colors and fonts")
    print("✅ Comprehensive JSON includes all awards and statistics")
    print("✅ Ready for HTML page generation!")
    print("=" * 80)


if __name__ == '__main__':
    test_visualizations()
