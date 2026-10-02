# Tools: probe.py and judge.py

Two small scripts for phase 4. They cover conversational ideas (chat, Q&A, sales, support, tutoring).
For other shapes (batch extraction, tool-using agents), write your own harness, but keep the same
measurements.

Setup: `pip install anthropic openai`, then export the API keys you were allowed to use.

## The experiment file

Copy `examples/experiment.example.json` next to the user's materials and edit it. Paths are relative to
the experiment file.

| Key | Meaning |
|---|---|
| `system_prompt_file` | The baseline prompt. Keep it short and goal-oriented (`examples/baseline_prompt.example.md`). |
| `materials` | Prepared text/Markdown files given to the model in full: PDF text, per-slide text and notes, tables from spreadsheets, descriptions of charts (see `baseline-knobs.md` §1). |
| `budget_usd` | Hard cap for probe.py's estimated spend (the product + simulated user). |
| `repeat` | Runs per (case, variant). Default 1. `--repeat N` on the command line overrides it. |
| `variants[]` | One entry per setup to compare (see below). |
| `cases[]` | Test cases: `id`, scripted `turns` (user messages sent in order), and optional `simulate: {persona, max_turns}` for a simulated user who continues after the script. |
| `simulator` | Model that plays the user (provider, model, price). Needed only if a case uses `simulate`. |
| `judge` | Model that grades transcripts (use a strong one), with price. |
| `judge_extra_criteria` | Product-specific rules for the judge, e.g. "Any individual legal or tax judgment is a high-severity error." |
| `judge_budget_usd` | Hard cap for judge.py. |

### Variants

| Field | Meaning |
|---|---|
| `id` | Short name used in file names and tables. |
| `provider` | `anthropic` or `openai`. |
| `model` | Model ID. Check current IDs and prices from the provider's docs; do not trust memory. |
| `input` | `text` (prepared materials in the system prompt, cached) or `pdf` (send the raw `pdf` as a document on the first turn, to compare raw vs prepared). |
| `pdf` | Path to the PDF when `input` is `pdf`. |
| `reasoning_effort` | OpenAI reasoning models: `none` to turn reasoning off; others to compare. |
| `thinking`, `output_config` | Passed through to Anthropic as-is (thinking off/on, effort). Use the shapes in the current model docs. |
| `max_tokens` | Default 4000. |
| `price` | USD per 1M tokens: `input`, `output`, `cached_input` (default 10% of input), `cache_write` (default = input). Used only for the cost estimate. |

## Running

```bash
python scripts/probe.py path/to/experiment.json            # all variants x all cases
python scripts/probe.py path/to/experiment.json --only fast_text --cases pricing_total
python scripts/probe.py path/to/experiment.json --only fast_text --cases refuse_legal pricing_total --repeat 5
python scripts/judge.py path/to/experiment.json            # grade everything not yet graded
python scripts/judge.py path/to/experiment.json --truth policy.txt brochure.txt   # different source of truth
```

Results go to `<out>/<case>__<variant>.json`, with repeats as `<case>__<variant>__r2.json`, `__r3.json`,
and so on. Judgments go to `<out>/judgments.json`. Both scripts skip work that is already done, so you
can add a variant, or raise `--repeat` for the deciding cases, and re-run. Tables count runs, so
"0 serious errors in 15 runs" can be read straight off them.

## Reading the numbers

- **First words** (time to first token) is what users feel in a streaming UI. **Finished** matters for
  read-aloud and for anything downstream.
- The first call of a variant pays a cold cache, so look at the median, not the first turn.
- Serious errors are the ones that decide verdicts. Declines are often acceptable; ask the user.
  "Declined but answerable" shows the baseline is too cautious, and is usually fixable with the prompt.
- Ignored questions (deflecting, repeating boilerplate) are what users notice first.
- Re-run the cases that decide the verdict 3–5 times with `--repeat`. A single pass is not a rate.
- A judge model grading another model has blind spots. Spot-check the verdict-deciding transcripts
  yourself, and quote them in the report.
