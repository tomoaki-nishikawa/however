#!/usr/bin/env python3
"""Grade transcripts produced by probe.py against the source material.

Usage:
    python judge.py <experiment.json> [--out <dir>] [--truth <file> ...]

Each transcript is graded on its own, by the `judge` model in the experiment file. The source of
truth is the experiment's materials, or the files given with --truth. The judge lists:
  - wrong:    statements that contradict the source, or assert something the source does not say
              (severity high = misleads a decision, e.g. price/eligibility/legal; low = minor detail)
  - declined: questions the assistant declined, and whether the source could have answered them
  - ignored:  questions neither answered nor declined (deflected, repeated boilerplate)
Results go to <out>/judgments.json, and a per-variant summary table is printed.
Re-runs skip transcripts that are already graded.
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe  # noqa: E402  (reuses provider calls and cost math)

RUBRIC = """You review a conversation between a user and an AI assistant built for the product described in the
experiment. The ONLY source of truth is the attached material. Judge the assistant's messages.

List every instance of:
1. wrong: a statement that contradicts the material, or states as fact something the material does not
   contain. General knowledge clearly flagged as general ("in general...", "please confirm with a
   professional") is not wrong. Give severity "high" if it could make the user decide wrongly (price,
   eligibility, legal/tax judgment, safety), otherwise "low".
2. declined: the assistant declined or deferred a question ("not in the material", "a specialist will
   follow up"). Say whether the material actually answers it (answerable_from_source).
3. ignored: the assistant neither answered nor declined a question (changed the subject, repeated
   boilerplate).
{extra}
Output only this JSON, with no text before or after it:
{{"wrong": [{{"quote": "...", "why": "what the material says", "severity": "high"}}],
 "declined": [{{"question": "...", "answerable_from_source": true, "note": "..."}}],
 "ignored": [{{"question": "...", "what_assistant_did": "..."}}],
 "summary": "one or two sentences"}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment")
    ap.add_argument("--out", default=None)
    ap.add_argument("--truth", nargs="*", default=None, help="files to use as the source of truth instead of materials")
    args = ap.parse_args()

    probe.BASE = os.path.dirname(os.path.abspath(args.experiment))
    with open(args.experiment, encoding="utf-8") as f:
        cfg = json.load(f)
    out = args.out or os.path.join(probe.BASE, cfg.get("out", "out"))
    judge = cfg["judge"]
    truth = "\n\n".join(probe.load_text(p) for p in args.truth) if args.truth else probe.material_text(cfg)
    extra = cfg.get("judge_extra_criteria", "")
    rubric = RUBRIC.format(extra=("\nAlso apply these product-specific rules:\n" + extra + "\n") if extra else "")
    spend = probe.Spend(cfg.get("judge_budget_usd"))

    if not os.path.isdir(out):
        raise SystemExit(f"No results in {out}. Run probe.py first.")
    path_out = os.path.join(out, "judgments.json")
    results = []
    if os.path.exists(path_out):
        with open(path_out, encoding="utf-8") as f:
            results = json.load(f)
    done = {(r["case"], r["variant"], r.get("run", 1)) for r in results}

    for name in sorted(os.listdir(out)):
        if "__" not in name or not name.endswith(".json"):
            continue
        with open(os.path.join(out, name), encoding="utf-8") as f:
            run = json.load(f)
        if (run["case"], run["variant"], run.get("run", 1)) in done:
            continue
        convo = "\n".join(f"{'User' if r == 'user' else 'Assistant'}: {t}" for r, t in run["history"])
        judge_variant = dict(judge, input="text")
        text, _, _, usage = probe.PROVIDERS[judge["provider"]](judge_variant, rubric, truth, [("user", convo)])
        spend.add(probe.cost_usd(usage, judge.get("price")))
        m = re.search(r"\{.*\}", text, re.S)
        verdict = json.loads(m.group(0)) if m else {"wrong": [], "declined": [], "ignored": [], "summary": "PARSE ERROR: " + text[:200]}
        results.append({"case": run["case"], "variant": run["variant"], "run": run.get("run", 1), "verdict": verdict})
        with open(path_out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
        print(f"graded {run['case']} x {run['variant']} (#{run.get('run', 1)})", flush=True)

    agg = collections.defaultdict(collections.Counter)
    for r in results:
        v, a = r["verdict"], agg[r["variant"]]
        a["runs"] += 1
        a["serious"] += sum(1 for w in v.get("wrong", []) if w.get("severity") == "high")
        a["minor"] += sum(1 for w in v.get("wrong", []) if w.get("severity") != "high")
        a["declined"] += len(v.get("declined", []))
        a["declined_answerable"] += sum(1 for d in v.get("declined", []) if d.get("answerable_from_source"))
        a["ignored"] += len(v.get("ignored", []))
    print(f"\nEstimated judge spend this run: ${spend.total:.4f}\n")
    print("| variant | runs | serious errors | minor errors | declined (answerable) | ignored |")
    print("|---|---|---|---|---|---|")
    for variant, a in sorted(agg.items()):
        print(f"| {variant} | {a['runs']} | {a['serious']} | {a['minor']} | {a['declined']} ({a['declined_answerable']}) | {a['ignored']} |")


if __name__ == "__main__":
    sys.exit(main())
