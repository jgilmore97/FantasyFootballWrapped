# Tenure-adjusted Best Draft Picks Plan

Goal: keep rewarding draft foresight while ensuring VOR credit stays with the manager who rostered the player during the relevant seasons (draft year plus keeper years). All seasons have equal weight; we only limit credit to the tenure on the drafting team.

## Data to gather per drafted player
- Draft metadata: year, round, drafting manager.
- Season-level VOR by manager tenure: for each subsequent season, collect VOR only for games while rostered by the drafting manager (including keeper seasons) and stop counting once traded/dropped.
- Round-average baselines per season: keep or compute the round-average VOR for the original draft round for each season to normalize cross-year value.

## Metric computation
1. **Identify on-team seasons**: From the draft season onward, build a list of seasons where the player remained on the drafting manager's roster; exclude seasons after a permanent trade/drop. For mid-season moves, use only the portion of VOR accrued while on the original roster.
2. **Season surplus**: For each on-team season, compute `season_surplus = player_season_VOR - round_avg_for_round_and_season` (no diminishing weights; each season counts equally).
3. **Tenure-adjusted surplus**: Sum all on-team `season_surplus` values. This becomes the ranking key for "Best Draft Picks".
4. **Tie-breakers and display**: Break ties via total on-team VOR, then earlier draft year. Show both draft-year surplus and total tenure-adjusted surplus in the report to clarify when value accrued.

## Edge cases and rules
- **No games while rostered**: If a player never produces VOR while on the drafting team (e.g., injured then dropped), their contribution is zero.
- **Traded/waived players**: After leaving the drafting team, subsequent VOR does not count toward that manager's draft pick. If they are reacquired later, only the reacquired span counts from that point forward.
- **Keepers**: Keeper seasons are treated the same as the draft year—full credit while on the original roster, no weighting changes.
- **Missing data**: If season VOR is unavailable, treat that season's surplus as zero rather than estimating.

## Reporting changes
- Update the "BEST DRAFT PICKS" section to display tenure-adjusted surplus and annotate when a breakout occurred after the player left the drafting team.
- Document the new methodology in the README/report so users understand why some historical best picks may move down when their value materialized on another roster.

## Testing
- Add tests for scenarios: early bust/late breakout on another team, immediate star kept multiple years, mid-season trade, and steady mid-round producer. Verify tenure-adjusted surplus aligns with expectations and that report output reflects the new fields.
