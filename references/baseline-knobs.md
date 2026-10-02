# Baseline knobs: what to vary, and what each one usually does

A plain baseline is cheap to build, so its quality depends on a few settings. Before concluding that "the
model can't do it", walk through this list. The notes come from real measurements on an
answer-from-the-brochure sales task (a 73-page PDF, about 80k characters of text). Your numbers will
differ, but the direction is usually the same.

## 1. Prepare the material once, in the form the model reads best

Real material arrives as PDFs, slide decks, spreadsheets, web pages, recordings and scanned images.
Handing the raw file to the model on every call is the slowest and often the least accurate option.
**Do the conversion once, offline, and give the model the prepared version.** This is often the biggest
single lever. In the measurement, a 73-page PDF sent as a document cost about 135k tokens and 20–40 s to
the first token, even with caching. The same content as extracted text cost about 18k tokens and about
1 s, and answers stayed correct, even on pricing tables.

Typical preparations:

| Source | Prepare it as |
|---|---|
| PDF (text-based) | Extracted text with the layout kept (`pdftotext -layout`, or any extractor), page numbers kept as headings |
| Slides (pptx, Keynote, Google Slides) | One section per slide: title, body text, table contents, and speaker notes (often where the real explanation lives) |
| Spreadsheets, price lists | Markdown or CSV tables with units and tax treatment in the headers. One table per concept, not one giant sheet |
| Web pages | Main text only. Remove navigation, footers and boilerplate repeated on every page |
| Charts, diagrams, scans, photos | A one-time description written by a vision model, checked by a human if numbers matter, then stored as text |
| Audio, video, call recordings | A transcript, optionally with a short summary per section |
| Many overlapping documents | Deduplicate. Mark which version is current, and drop superseded prices and terms |

Principles:

- **Keep the structure** (headings, page or slide numbers, table rows) so answers can cite where facts
  come from, and so the judge can check them.
- **Make facts explicit.** If a rule lives only in a footnote or a chart ("+¥110,000 when the home is
  included", "about 2–3 months to contract"), make sure it survives as text.
- **Pay the cost once.** Expensive steps (vision descriptions, OCR, cleanup) belong in preprocessing,
  not in every request.
- **Measure raw vs prepared.** Run one variant on the raw format and one on the prepared version. If
  the raw format wins on accuracy (the meaning really is in the images), keep it and report its latency
  and cost honestly.

## 2. Whole material vs selected snippets

- Selecting "the relevant parts" (retrieval, hand-built context selection) is where answers silently
  lose facts. Examples: a surcharge listed on another page, a duration stated in a flow chart.
- If the material fits comfortably in context (tens of thousands of tokens), give all of it and use
  prompt caching. Retrieval comes in round 2 or 3, and only if the whole thing does not fit or costs
  too much.

## 3. Reasoning / extended thinking

- For "answer from the given material" tasks, reasoning added several seconds per turn and did not
  reduce errors in the measurement.
- Turn it off first (`reasoning_effort: "none"` on OpenAI reasoning models; on Anthropic models, omit
  `thinking` or use the model's documented "off" setting). Then run reasoning-on as a comparison, not
  the other way round.

## 4. Streaming

- Measure **time to first token** as well as total time. With streaming, users see words after about
  1 s even when the full answer takes 3–5 s. A non-streaming product that shows nothing until the end
  feels much slower at the same total time.

## 5. Model tier

- Run at least **today's top model** and **today's fastest/cheapest model**.
- Small models were fast but made arithmetic and eligibility mistakes in pricing (forgetting a
  surcharge, mixing tax-inclusive and tax-exclusive figures). Mid and top models did not.
- The top model's plain-baseline result is your proxy for what cheap models will do in 6–12 months.

## 6. Prompt shape

- A short goal ("help the visitor decide correctly; answer only from the material; say when something
  is not in it") worked better than long rule lists.
- Add boundaries one line at a time when a test case fails, for example "don't give individual
  legal/tax judgments; refer to a lawyer/tax accountant". Then re-run the failing case several times.
  One pass is not evidence.

## 7. Calls per turn

- One call per turn is the plain baseline. Chains of calls (classify → select → generate → verify)
  add latency at every step. Add a step only when a measured failure needs it.

## 8. Prompt caching

- Put stable content (instructions + material) first and mark it cacheable. After the first call, cost
  and latency drop sharply. Remember that low-traffic products often hit a cold cache. Report both the
  warm-cache and cold-cache cost.
