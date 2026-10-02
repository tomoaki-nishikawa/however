# Report template

Write in the user's language and in plain business terms. Put technical detail in the appendix.

```markdown
# however: <idea name>

## Verdict
<One of: Don't build / Build thin on top of plain models / Build — the part only you can provide is X>
<Two or three sentences on why.>

## The idea and its core value
- Idea: <who, situation, outcome>
- Core value (testable): Given ..., the product delivers ... within ...
- Requirements that decide it: <speed / error tolerance / cost / boundaries / change>, with thresholds

## What a plain AI setup already delivers
| Variant | First words | Finished | Serious errors | Declines (answerable) | Ignored | Cost / use |
|---|---|---|---|---|---|---|
| <top model, text, reasoning off> | | | | | | |
| <fast model, text, reasoning off> | | | | | | |
| <…> | | | | | | |

<Two or three transcript excerpts: one where the baseline shines, one where it fails.>

## What gap remains
<The specific cases the baseline still fails, why (diagnosis), and whether a later round closed them.>

## Value as models improve
- Value that compensates for model weaknesses (shrinks): ...
- Value that rides model strength (grows): ...
- Frontier proxy: today's top model, plain setup → <result>, so cheap models will likely do this in ~6–12 months.
- Trend datapoint (if run): the model from ~6 months ago → <result>
- Answer to "2× smarter, 10× cheaper, 2× faster in six months": <more / less valuable, and why>

## Limits of this check
- <N> cases, <N> runs each; simulated users; a judge model grading another model
- Materials and models tried; what was not tested
- Measured vs assumed

## Appendix
- Rounds: what changed in each round and what happened
- Prompts used, settings, total spend
```
