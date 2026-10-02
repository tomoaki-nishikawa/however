#!/usr/bin/env python3
"""Run plain-baseline variants over test cases and record latency, usage and cost.

Usage:
    python probe.py <experiment.json> [--out <dir>] [--only <variant_id> ...] [--cases <case_id> ...] [--repeat N]

The experiment file is described in references/tools.md, and examples/experiment.example.json is a
starting point. For each (case, variant) the script writes <out>/<case>__<variant>.json (repeats:
<case>__<variant>__r2.json, __r3.json, ...) with the transcript, per-turn time-to-first-token and total time, token usage and estimated cost. It finishes with
a per-variant summary table. Existing result files are skipped, so a re-run resumes where it stopped.

Requires: `pip install anthropic openai` for whichever providers you use, and the matching API keys
in the environment.
"""
import argparse
import base64
import json
import os
import statistics
import sys
import time

BASE = None  # directory of the experiment file; relative paths resolve against it


def load_text(path):
    with open(os.path.join(BASE, path), encoding="utf-8") as f:
        return f.read()


def material_text(cfg):
    parts = []
    for path in cfg.get("materials", []):
        parts.append(f"## {os.path.basename(path)}\n{load_text(path)}")
    return "\n\n".join(parts)


class Spend:
    """Running total of estimated cost; stops the run at the budget cap."""

    def __init__(self, cap_usd):
        self.cap = cap_usd
        self.total = 0.0

    def add(self, usd):
        self.total += usd
        if self.cap is not None and self.total >= self.cap:
            raise SystemExit(f"Budget cap reached: ${self.total:.2f} >= ${self.cap:.2f}. Stopping.")


def cost_usd(usage, price):
    """price: USD per 1M tokens: input, output, cached_input (default 10% of input), cache_write (default = input)."""
    if not price:
        return 0.0
    p_in = price["input"]
    p_out = price["output"]
    p_cached = price.get("cached_input", p_in * 0.1)
    p_write = price.get("cache_write", p_in)
    return (usage["input"] * p_in + usage["output"] * p_out
            + usage["cache_read"] * p_cached + usage["cache_write"] * p_write) / 1e6


# ---------------------------------------------------------------- providers

def anthropic_turn(variant, system_prompt, material, history):
    import anthropic
    client = anthropic.Anthropic()
    mode = variant.get("input", "text")
    if mode == "text":
        system = [{"type": "text", "text": system_prompt + "\n\n# Material\n" + material,
                   "cache_control": {"type": "ephemeral"}}]
    else:
        system = system_prompt
    msgs = []
    for i, (role, text) in enumerate(history):
        content = text
        if i == 0 and mode == "pdf":
            with open(os.path.join(BASE, variant["pdf"]), "rb") as f:
                data = base64.standard_b64encode(f.read()).decode()
            content = [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data},
                        "cache_control": {"type": "ephemeral"}},
                       {"type": "text", "text": text}]
        msgs.append({"role": "user" if role == "user" else "assistant", "content": content})
    extra = {}
    for key in ("thinking", "output_config"):
        if key in variant:
            extra[key] = variant[key]
    t0 = time.time()
    first = None
    with client.messages.stream(model=variant["model"], max_tokens=variant.get("max_tokens", 4000),
                                system=system, messages=msgs, **extra) as stream:
        for _ in stream.text_stream:
            if first is None:
                first = time.time() - t0
        final = stream.get_final_message()
    total = time.time() - t0
    text = "".join(b.text for b in final.content if b.type == "text").strip()
    u = final.usage
    usage = {"input": u.input_tokens, "output": u.output_tokens,
             "cache_read": u.cache_read_input_tokens or 0, "cache_write": u.cache_creation_input_tokens or 0}
    return text, first if first is not None else total, total, usage


_openai_files = {}


def openai_turn(variant, system_prompt, material, history):
    from openai import OpenAI
    client = OpenAI()
    mode = variant.get("input", "text")
    sys_content = system_prompt + ("\n\n# Material\n" + material if mode == "text" else "")
    msgs = [{"role": "system", "content": sys_content}]
    for i, (role, text) in enumerate(history):
        content = text
        if i == 0 and mode == "pdf":
            path = os.path.join(BASE, variant["pdf"])
            if path not in _openai_files:
                with open(path, "rb") as f:
                    _openai_files[path] = client.files.create(file=f, purpose="user_data").id
            content = [{"type": "file", "file": {"file_id": _openai_files[path]}}, {"type": "text", "text": text}]
        msgs.append({"role": "user" if role == "user" else "assistant", "content": content})
    kwargs = {}
    if "reasoning_effort" in variant:
        kwargs["reasoning_effort"] = variant["reasoning_effort"]
    t0 = time.time()
    first = None
    parts = []
    usage = None
    stream = client.chat.completions.create(model=variant["model"], messages=msgs, stream=True,
                                            stream_options={"include_usage": True}, **kwargs)
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            if first is None:
                first = time.time() - t0
            parts.append(chunk.choices[0].delta.content)
        if chunk.usage:
            usage = chunk.usage
    total = time.time() - t0
    cached = 0
    if usage and usage.prompt_tokens_details:
        cached = usage.prompt_tokens_details.cached_tokens or 0
    u = {"input": (usage.prompt_tokens - cached) if usage else 0, "output": usage.completion_tokens if usage else 0,
         "cache_read": cached, "cache_write": 0}
    return "".join(parts).strip(), first if first is not None else total, total, u


PROVIDERS = {"anthropic": anthropic_turn, "openai": openai_turn}


# ---------------------------------------------------------------- simulated user

SIM_PROMPT = """You are role-playing an ordinary user of the product described below, chatting with it.

Who you are and what you want to find out:
{persona}

Rules:
- Write only your next single message. No preamble.
- Keep it short and natural (1-3 sentences), in the same language as the conversation.
- If the assistant did not answer your question, ask again. If it did, move on naturally.
- When you have what you came for, or have no reason to continue, reply with exactly <END>."""


def simulate(cfg, persona, history):
    sim = cfg.get("simulator")
    if not sim:
        raise SystemExit("A case uses `simulate` but the experiment has no `simulator` block.")
    convo = "\n".join(f"{'User' if r == 'user' else 'Assistant'}: {t}" for r, t in history)
    prompt = f"Conversation so far:\n{convo}\n\nWrite your next message."
    sim_variant = dict(sim, input="none")
    text, _, _, usage = PROVIDERS[sim["provider"]](sim_variant, SIM_PROMPT.format(persona=persona), "", [("user", prompt)])
    return text, usage


# ---------------------------------------------------------------- result files

def result_name(case_id, variant_id, run_no):
    """The first run keeps the plain name, so raising --repeat later reuses it."""
    suffix = "" if run_no == 1 else f"__r{run_no}"
    return f"{case_id}__{variant_id}{suffix}.json"


def result_files(out, case_id, variant_id):
    first = os.path.join(out, result_name(case_id, variant_id, 1))
    files = [first] if os.path.exists(first) else []
    prefix = f"{case_id}__{variant_id}__r"
    files += sorted(os.path.join(out, n) for n in os.listdir(out) if n.startswith(prefix) and n.endswith(".json"))
    return files


# ---------------------------------------------------------------- main

def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment")
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", nargs="*", default=None, help="variant ids to run")
    ap.add_argument("--cases", nargs="*", default=None, help="case ids to run")
    ap.add_argument("--repeat", type=int, default=None,
                    help="runs per (case, variant); overrides the experiment's `repeat` (default 1)")
    args = ap.parse_args()

    BASE = os.path.dirname(os.path.abspath(args.experiment))
    with open(args.experiment, encoding="utf-8") as f:
        cfg = json.load(f)
    out = args.out or os.path.join(BASE, cfg.get("out", "out"))
    os.makedirs(out, exist_ok=True)
    system_prompt = load_text(cfg["system_prompt_file"])
    material = material_text(cfg)
    spend = Spend(cfg.get("budget_usd"))

    repeat = args.repeat or cfg.get("repeat", 1)
    variants = [v for v in cfg["variants"] if not args.only or v["id"] in args.only]
    cases = [c for c in cfg["cases"] if not args.cases or c["id"] in args.cases]

    for variant in variants:
        turn_fn = PROVIDERS[variant["provider"]]
        for case, run_no in [(c, k) for c in cases for k in range(1, repeat + 1)]:
            path = os.path.join(out, result_name(case["id"], variant["id"], run_no))
            if os.path.exists(path):
                continue
            print(f"run {case['id']} x {variant['id']} (#{run_no})", flush=True)
            history, timing, calls = [], [], []
            scripted = list(case.get("turns", []))
            sim = case.get("simulate")
            max_turns = len(scripted) + (sim.get("max_turns", 3) if sim else 0)
            for _ in range(max_turns):
                if scripted:
                    msg = scripted.pop(0)
                else:
                    msg, u = simulate(cfg, sim["persona"], history)
                    c = cost_usd(u, cfg["simulator"].get("price"))
                    calls.append({"role": "simulator", **u, "usd": c})
                    spend.add(c)
                    if "<END>" in msg:
                        break
                history.append(("user", msg))
                text, ttft, total, u = turn_fn(variant, system_prompt, material, history)
                c = cost_usd(u, variant.get("price"))
                calls.append({"role": "product", **u, "usd": c})
                spend.add(c)
                timing.append({"ttft": round(ttft, 2), "total": round(total, 2)})
                history.append(("assistant", text))
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"case": case["id"], "variant": variant["id"], "run": run_no, "history": history,
                           "timing": timing, "calls": calls}, f, ensure_ascii=False, indent=1)

    # summary
    print(f"\nEstimated spend this run: ${spend.total:.4f}\n")
    print("| variant | runs | turns | first words (median / max) | finished (median / max) | cost per run |")
    print("|---|---|---|---|---|---|")
    for variant in cfg["variants"]:
        files = [p for c in cfg["cases"] for p in result_files(out, c["id"], variant["id"])]
        if not files:
            continue
        ttft, total, usd = [], [], 0.0
        for p in files:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            ttft += [t["ttft"] for t in d["timing"]]
            total += [t["total"] for t in d["timing"]]
            usd += sum(c["usd"] for c in d["calls"] if c["role"] == "product")
        print(f"| {variant['id']} | {len(files)} | {len(ttft)} | {statistics.median(ttft):.1f}s / {max(ttft):.1f}s | "
              f"{statistics.median(total):.1f}s / {max(total):.1f}s | ${usd / len(files):.4f} |")


if __name__ == "__main__":
    sys.exit(main())
