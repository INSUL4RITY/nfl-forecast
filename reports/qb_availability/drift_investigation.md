# Investigation: downward drift in start rates for Questionable QB1s (2026-09-25)

Question: is the lower recent start rate for Questionable depth-chart QB1s (2024: 9/27) caused by a data or calculation
error? Scripts: `.scratch/drift.py`, `.scratch/drift2.py` (inputs: `build_audit_table`, weekly depth charts 2016-2024).
Decision rule stated in advance: do not retune on a small recent sample; fix only genuine errors.

## Checks and findings
| Check | Result | Error? |
|---|---|---|
| Week alignment of injury reports vs games (incl. playoffs 19-22) | identical week numbering; playoff rows carry WC/DIV/CON/SB | no |
| Start target | "started" = first dropback passer of the game; 2024 cases inspected one by one (Love wk2-3, Wilson wk3-4, Richardson wk5-6, Winston wk16-18, Tua wk17, Lawrence wk10, ...) match known starters | no |
| Depth-chart duplicates (more than one QB at depth 1; code keeps the first) | 1-28 team-weeks per season (1 in 2024); only 3 Questionable/Doubtful history cases fall in such weeks | negligible; documented, not changed |
| Chart quality over time: P(start \| QB1 not on report) | 0.91-0.96 every season, no trend (2024: 0.925) | no |
| "Declared inactive" counts | 0 in 2016-2018, 5-17 afterwards: weekly-roster `INA` status is not populated before 2019 | **data artifact** in the descriptive audit column only; the start target does not use it |
| Clustering | Repeated weeks of one injury are counted separately (2024: 27 cases = 19 episodes) | not an error, but intervals computed per case overstate precision |
| Statistical evidence | Per case: 2024 9/27 vs 2016-23 103/166 (0.62), naive p = 0.002. Per episode (first listed week): 2024 7/19 vs 0.555 over 119 episodes, p = 0.08. Season rates 0.78, 0.71, 0.53, 0.65, 0.75, 0.42, 0.54, 0.68, 0.33 | no significant shift once clustering is respected |

## Conclusion
No data or calculation error explains the drift. The one artifact found (no `INA` roster status before 2019) affects only the
descriptive "declared inactive" column. The 2024 value is within the season-to-season variation seen before (2021-22 were similar)
once repeated weeks of the same injury are treated as one episode. **No retuning.** The frozen model keeps the evaluated
estimator. Research limitation for the future: the rates' intervals are per case and do not account for clustering by
injury episode, so they are somewhat too narrow for Questionable QBs; an episode-level estimator can be evaluated next season.
