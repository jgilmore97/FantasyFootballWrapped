# ESPN Fantasy Football Wrapped 🏈

A "Spotify Wrapped" style summary tool for ESPN Fantasy Football leagues. This tool extracts 5 years of historical data from your ESPN league and generates fun statistics, awards, and visualizations to celebrate your league's history.

## Features

### Core Awards
- **All-Time Scoring Leader**: Most total points scored across all years
- **Unluckiest/Luckiest Manager**: Most/least points scored against
- **Best All-Time Record**: Highest win percentage
- **Highest Single Week**: Highest individual weekly score
- **Punt God**: Manager with most combined points from Defense/ST, Kicker, and Punter (2021-2025)
- Complete rankings for all categories

### Injury Analysis
- **Most Injured Team Award**: Count of "injury-weeks" (players with OUT, IR, Doubtful, or Suspended status)
- Worst single week (most simultaneous injuries)
- Each manager's "frequent flyer" (most often injured player)

### Rivalries
- **Nemesis & Victims**: FPS-style rivalry stats for each manager
  - **Nemesis**: Opponent who scored the most points against you (average per game)
  - **Victim**: Opponent you scored the most points against (average per game)
  - Includes total points, games played, and head-to-head record

### Player Deep Dive
- **Most Valuable Player (Single Season)**: Best single-season performance based on Value Over Replacement (VOR)
  - Includes ESPN player headshot automatically downloaded and displayed
- **Most Valuable Player (5-Year Total VOR)**: Player with highest cumulative VOR across all 5 seasons
  - Rewards consistent excellence over the full league history
- **Most Valuable Player (5-Year Average VOR)**: Player with highest average VOR per season
  - Allows newer players to compete on peak performance regardless of seasons played
- **Top 10 Rankings**: Separate rankings for total VOR and average VOR
- **Best Draft Picks**: Top draft steals considering draft cost vs. value produced
- **Keeper Value Leaders**: Managers who got most value from their keeper selections
- **Draft Pick Value Leaders**: Managers who drafted best (non-keeper picks, 2022-2025)

### Visualizations
- All-time points scored (horizontal bar chart)
- Win percentage rankings
- **MVP showcase** with player headshot and stats
- Luck analysis scatter plot (points for vs points against)
- Championships and playoff appearances
- **Hall of Fame** - Top 10 most valuable player seasons with headshots in a grid layout

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Your ESPN Credentials

Since your league is private, you need to provide authentication cookies:

1. Login to your ESPN Fantasy Football league in a web browser
2. Open browser developer tools (F12 or right-click → Inspect)
3. Go to the **Application** or **Storage** tab
4. Navigate to **Cookies** → `https://fantasy.espn.com`
5. Find and copy these two values:
   - `espn_s2` (long string)
   - `SWID` (format: `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`)

### 3. Configure the Script

Supply your credentials and league info via environment variables or CLI flags (recommended so you don't have to edit the code):

```bash
# Environment variables
export LEAGUE_ID=123456
export YEARS=2021,2022,2023,2024,2025
export ESPN_S2="<your espn_s2 cookie>"
export SWID="{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"

# Or pass them on the command line
python fantasy_wrapped.py \
  --league-id 123456 \
  --years 2021,2022,2023,2024,2025 \
  --espn-s2 "$ESPN_S2" \
  --swid "$SWID"
```

Tips:
- Confirm your league ID by opening `https://fantasy.espn.com/football/league?leagueId=<your-id>` in a browser.
- Refresh the `espn_s2` and `SWID` cookies if you see authentication or "league does not exist" errors.

### 4. Run the Analysis

```bash
python fantasy_wrapped.py
```

The script will:
1. Extract data from all 5 seasons (2021-2025)
2. Calculate all statistics and awards
3. Generate visualizations
4. Create a comprehensive text report

## Output Files

- **fantasy_wrapped_report.txt**: ASCII-formatted comprehensive report with all awards, rankings, and analysis
- **fantasy_wrapped_charts.png**: Multi-panel visualization with 6 charts including MVP showcase and Hall of Fame
- **mvp_headshot.png**: ESPN headshot of the Most Valuable Player

The visualization now includes a "Hall of Fame" section displaying the top 10 most valuable player seasons with their ESPN headshots in a grid layout, creating a truly "Spotify Wrapped" style experience!

## League Details

- **Platform**: ESPN Fantasy Football
- **League ID**: 778135041
- **Duration**: 5-year keeper league (2021-2025)
- **Keeper Rules**: 6 keepers per team, kept at no round cost
- **Format**: Superflex league (OP slot for any player, usually QB)

## Technical Details

### Value Over Replacement (VOR)

The script calculates VOR for players using position-specific replacement levels:
- QB: Top 25
- RB: Top 40
- WR: Top 50
- TE: Top 15
- D/ST: Top 15
- K: Top 15

Replacement level is determined by the average points of the threshold player for each position in a given year.

### Draft Value Scoring

Best draft picks are calculated using:
- Value Over Replacement (VOR) of the player's season
- Draft cost (round number)
- Keeper vs. non-keeper status

Formula: `value_score = VOR / round_number`

### Injury Tracking

Injury-weeks are counted when a player on a roster has one of these statuses:
- OUT
- IR (Injured Reserve)
- DOUBTFUL
- SUSPENDED

## Future Enhancement Ideas

- Waiver wire stars (most points from waiver acquisitions)
- Weekly high score count per manager
- Consistency rating (lowest weekly score variance)
- Trade analysis
- Year-over-year improvement tracking

## Troubleshooting

### Network/Proxy Errors

If you see proxy or connection errors:
1. Ensure your environment has internet access to ESPN's API servers
2. Check that no firewall or proxy is blocking `lm-api-reads.fantasy.espn.com`
3. Try running from a different network if issues persist

### Authentication Errors

If you get authentication errors:
1. Make sure your `espn_s2` and `SWID` cookies are current
2. These cookies can expire - re-copy them from your browser
3. Ensure you're logged into ESPN when copying the cookies

### Missing Data

Some historical data may be incomplete for older seasons. The script will:
- Print warnings for any issues loading specific weeks/years
- Continue processing available data
- Skip calculations where data is missing

### Dependencies

If you encounter import errors, ensure all dependencies are installed:
```bash
pip install --upgrade espn-api matplotlib pandas numpy
```

## Credits

Built using:
- [espn-api](https://github.com/cwendt94/espn-api) - ESPN Fantasy API wrapper
- matplotlib - Visualization
- pandas/numpy - Data analysis

## License

MIT License - See LICENSE file for details
