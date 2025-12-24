#!/usr/bin/env python3
"""
Diagnostic script to investigate why Tyreek Hill shows only 4 seasons.
"""

from espn_api.football import League

LEAGUE_ID = 778135041
YEARS = [2021, 2022, 2023, 2024, 2025]
ESPN_S2 = "AECZk7m5ZiOXfGwzOnbj7p3EoalPIV2RCeA%2BjgMiZfLTu731Pjk1h%2FkbHIVTCJ7QD0vd4XlZ%2FVezppPxysurKT6DFjtS2U6hF5XJUmHcjvHewmCbPaWv1YNI0FpLdBEADn3N1xKN9ert4%2BA9pljrcO3v9zrPV9h0h7u9%2ByCKJDEYxAoZjIWQTHD2qHdY4EOhi%2F0Y8iZYlrMp1BRmI8HDmYcZjtUwXTL%2Bx3H70FZtE1bfXPyqxs1n5zgFc0X7tRu3I2GfdTazuworr3VflODY9fVi8Hsf9ttxlat1slyF5zBGng%3D%3D"
SWID = "{CFD648CA-1223-407F-8E12-A5F773A4C738}"

def find_tyreek_on_rosters():
    """Check if Tyreek Hill appears on any team roster for each year."""
    print("=" * 80)
    print("Checking for Tyreek Hill on team rosters")
    print("=" * 80)
    
    for year in YEARS:
        print(f"\n{year}:")
        try:
            league = League(
                league_id=LEAGUE_ID,
                year=year,
                espn_s2=ESPN_S2,
                swid=SWID
            )
            
            found = False
            for team in league.teams:
                if hasattr(team, 'roster'):
                    for player in team.roster:
                        name = getattr(player, 'name', '')
                        if isinstance(name, dict):
                            name = name.get('fullName', str(name))
                        if 'tyreek' in str(name).lower() or 'hill' in str(name).lower():
                            player_id = getattr(player, 'playerId', 'N/A')
                            points = getattr(player, 'total_points', 0)
                            position = getattr(player, 'position', 'N/A')
                            print(f"  FOUND on roster: {name} (ID: {player_id}, Points: {points}, Pos: {position})")
                            print(f"    Team: {team.team_name}")
                            found = True
            
            if not found:
                print("  NOT FOUND on any team roster")
                
        except Exception as e:
            print(f"  Error: {e}")


def find_tyreek_in_box_scores():
    """Check if Tyreek Hill appears in any box scores for each year."""
    print("\n" + "=" * 80)
    print("Checking for Tyreek Hill in weekly box scores")
    print("=" * 80)
    
    for year in YEARS:
        print(f"\n{year}:")
        try:
            league = League(
                league_id=LEAGUE_ID,
                year=year,
                espn_s2=ESPN_S2,
                swid=SWID
            )
            
            total_weeks = league.settings.reg_season_count
            tyreek_weeks = []
            tyreek_info = {}
            
            for week in range(1, total_weeks + 1):
                try:
                    box_scores = league.box_scores(week)
                    for matchup in box_scores:
                        for lineup in [matchup.home_lineup, matchup.away_lineup]:
                            if lineup:
                                for player in lineup:
                                    name = getattr(player, 'name', '')
                                    if isinstance(name, dict):
                                        name = name.get('fullName', str(name))
                                    if 'tyreek' in str(name).lower():
                                        points = getattr(player, 'points', 0)
                                        player_id = getattr(player, 'playerId', 'N/A')
                                        tyreek_weeks.append((week, points))
                                        tyreek_info = {
                                            'name': name,
                                            'player_id': player_id,
                                            'position': getattr(player, 'position', 'N/A')
                                        }
                except Exception as e:
                    pass  # Skip weeks that fail
            
            if tyreek_weeks:
                total_pts = sum(pts for _, pts in tyreek_weeks)
                print(f"  FOUND in {len(tyreek_weeks)} weeks")
                print(f"  Name: {tyreek_info.get('name')}, ID: {tyreek_info.get('player_id')}")
                print(f"  Total points: {total_pts:.1f}")
                print(f"  Weeks played: {[w for w, _ in tyreek_weeks]}")
            else:
                print("  NOT FOUND in any box scores")
                
        except Exception as e:
            print(f"  Error: {e}")


def check_free_agents():
    """Check if Tyreek Hill is in free agents for 2025."""
    print("\n" + "=" * 80)
    print("Checking 2025 Free Agents")
    print("=" * 80)
    
    try:
        league = League(
            league_id=LEAGUE_ID,
            year=2025,
            espn_s2=ESPN_S2,
            swid=SWID
        )
        
        # Try to get free agents
        if hasattr(league, 'free_agents'):
            try:
                # This might be a method or property
                fa = league.free_agents(size=200, position='WR')
                print(f"\nSearching {len(fa)} WR free agents...")
                for player in fa:
                    name = getattr(player, 'name', '')
                    if isinstance(name, dict):
                        name = name.get('fullName', str(name))
                    if 'tyreek' in str(name).lower():
                        player_id = getattr(player, 'playerId', 'N/A')
                        points = getattr(player, 'total_points', 0)
                        print(f"  FOUND: {name} (ID: {player_id}, Points: {points})")
            except Exception as e:
                print(f"  Could not fetch free agents: {e}")
        else:
            print("  No free_agents method available")
            
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    find_tyreek_on_rosters()
    find_tyreek_in_box_scores()
    check_free_agents()