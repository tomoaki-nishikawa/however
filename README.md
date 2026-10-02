# however

> "Sounds good, however… a plain AI setup already does most of that."

`however` is a skill for **Claude Code** and **Codex**. It reality-checks an AI product idea before you
spend months building it. The skill:

1. understands the idea;
2. pins down the core value a customer would pay for;
3. derives the non-functional requirements that value depends on (perceived speed, error tolerance,
   cost, boundaries, change);
4. builds the **strongest plain baseline** it can: whole material in context as text, reasoning off,
   streaming, top and fast model tiers. It measures that baseline, diagnoses the gaps and retries,
   up to three rounds;
5. asks: **"If models got 2× smarter, 10× cheaper and 2× faster in six months, would this product be
   worth more or less?"**;
6. reports a verdict: *don't build*, *build thin on top of plain models*, or *build — here's the part
   only you can provide*.

## Why I made this

I wanted an AI that gives sales presentations to website visitors. My first try was simple: call a model
through its API. It hallucinated too often and was too slow to be usable. So I thought there might be
demand for a web sales agent that guarantees, by design, that it never hallucinates, and that also
responds fast. I started building one and melted several months into it.

One day, with the finish line in sight, I tried a plain agent on the latest fast model. The quality was
already good enough. Once I changed how the material was passed in (plain text instead of PDF, reasoning
off, streaming), the latency was satisfyingly low too.

I made this skill to carve that lesson in: before you build, try hard to make the plain version work, and
assume models will keep getting better.

## Install

Clone the repository into your skills directory:

```bash
git clone https://github.com/tomoaki-nishikawa/however.git ~/.claude/skills/however
```

To use it from Codex as well, link the same folder:

```bash
ln -s ~/.claude/skills/however ~/.codex/skills/however
```

Then ask your agent: "Use however on this idea: …", or type `/however` (Claude Code) or `$however` (Codex).

The experiment scripts need Python 3.10+, `pip install anthropic openai` (whichever providers you use),
and API keys in the environment. The skill asks for a budget and for consent before sending any
material to a provider. Without keys, it does the analysis on paper and says that no measurement was run.

## What's inside

| Path | What it is |
|---|---|
| `SKILL.md` | The workflow the agent follows |
| `references/baseline-knobs.md` | The settings that make or break a plain baseline, with measured effects |
| `references/tools.md` | How to use the scripts and read their numbers |
| `references/report-template.md` | The report format |
| `scripts/probe.py` | Runs variants × test cases with streaming; records time to first words, total time, tokens and estimated cost; supports scripted turns and simulated users; enforces a budget cap |
| `scripts/judge.py` | Grades each transcript against the source material: serious and minor errors, declines (and whether they were answerable), ignored questions |
| `examples/` | A fictional pricing sheet, a baseline prompt and an experiment file to start from |
| `agents/openai.yaml` | Display metadata for Codex |

Try the example (it costs well under US$1):

```bash
cd ~/.claude/skills/however
python scripts/probe.py examples/experiment.example.json
python scripts/judge.py examples/experiment.example.json
```

---

## 日本語

`however` は、AI を使ったプロダクトのアイデアを、作り込む前に「素朴な AI の使い方で、もうできてしまわないか」と確かめるスキルです。Claude Code と Codex の両方で使えます。名前は「いいですね、ただ……（それ、素の AI でできちゃいますけど）」から付けました。

スキルが行うこと:

1. アイデアを理解する
2. 「買ってもらえる / 使ってもらえる」理由となる中心の価値を特定する
3. その価値が発揮されるための条件を、測れる基準にする（体感速度・許せる誤りと許せない誤り・費用・断るべきこと・資料の更新）
4. 素朴で一番強い対照を作り、何通りも小さく試して測る。資料はテキストで全文渡し、考える設定は切り、出来た順に表示し、最上位と高速の両方のモデルで試す。届かなければ原因を分析して試し直す（最大 3 回）
5. 「モデルが半年後に 2 倍賢く、10 倍安く、2 倍速くなったら、この製品の価値は上がるか、下がるか」を検討する
6. 「作らない」「素の AI の上に薄く作る」「作る（あなたにしか出せない部分はここ）」のどれかで結論をまとめて報告する

### 作った理由

「AI が Web で営業プレゼンしてくれたら……」と思い、最初は AI を API 経由で呼び出してシンプルに作ろうとしました。ところがハルシネーションは多いし、レイテンシーも高いしで、使い物になりませんでした。

そこで「ハルシネーションが起きないことが仕組み上保証されていて、しかも低レイテンシーな Web 営業担当を作れたら、需要があるかも」と思って開発を始め、数か月を溶かしました。

完成が見えてきたある日、最新の高速モデルで素朴なエージェントを試してみようと思い立ちました。すると十分な品質がすでに実現されていて、データの渡し方を工夫したら（PDF ではなくテキストで渡す、考える設定を切る、出来た順に表示する）、レイテンシーも満足のいく低さに収まってしまいました。

この経験を教訓として刻むために作ったスキルです。

導入方法は上の「Install」を参照してください。実験では資料をモデルの提供元へ送るため、事前に予算と送信の同意を確認します。
