# Co-Do Outreach Learning Engine v0.1

**Executable prototype, not an email campaign.** The user-facing principle is: **their research first; identify a real, testable shared question; enable on-demand cooperation among independent people and AI; learn from corrections and real outcomes.**

This lives inside the existing [Co-Do hub](../README.md). It neither sends email nor creates calendar events, contacts researchers, or autonomously changes research Issue text. It prepares **review-only drafts**. It uses no paid service and only the Python 3.10+ standard library.

## Actually run it

From this directory:

```bash
python3 engine.py status
python3 engine.py match qing-xiao
python3 engine.py match aneesh-pappu
python3 engine.py draft qing-xiao
python3 engine.py draft aneesh-pappu
python3 engine.py draft aneesh-pappu --untrained  # before learning comparison
python3 engine.py learn                          # refit saved preference model
python3 -m unittest discover -s tests -v
```

A draft writes `state/drafts/<researcher>.json` and prints subject, body, supporting source links, match reasoning and `send_authorized: false`. **There is no send-email command or SMTP client.**

## Where recurrence actually happens

1. `data/researchers.json` keeps **grounded** public research facts, specific hypotheses, competing questions and source URLs. It is **not** a live academic search result, and a theoretical gap is not automatically verified or novel.
2. `data/feedback.jsonl` contains **public, de-identified seed examples** of editorial corrections and an issue-choice correction. Actual new feedback is appended to **`data/feedback.local.jsonl`**, which is gitignored and never automatically published. The seed examples are **paraphrases of observed discussion**, not complete verbatim original emails and not real external replies.
3. `python3 engine.py learn` (or the **next `draft`/`match` command automatically**, when feedback has changed) fits a pairwise preference model from revisions; it also learns per-person research-question choices and separately records real external outcomes, **only if a human explicitly supplies them**. The output is saved in `state/learned.json` and used by the next draft. The model stores actual numeric weights, not just another instruction document.
4. `draft` ranks the research intersections, builds four distinct narrative candidates, applies the learned preference scores and saves the selected draft for review. It does not confuse a higher style score with scientific correctness.
5. Repeat. New feedback changes the saved model and subsequent draft choice. No dependency on ChatGPT chat memory.

Record a new correction (the two files must contain the complete rejected and human-preferred text):

```bash
python3 engine.py feedback qing-xiao --rejected /path/to/rejected.txt --preferred /path/to/preferred.txt --note 'reason for correction'
python3 engine.py draft qing-xiao  # retrains automatically after changed feedback
```

Record a better issue selection:

```bash
python3 engine.py choose aneesh-pappu --preferred-issue ORG-03 --rejected-issue ORG-02
python3 engine.py match aneesh-pappu # detects new choice automatically
```

Record an **actual** answer when it exists (never pretend a draft is a reply):

```bash
python3 engine.py outcome qing-xiao --issue ORG-01 --kind interested --note 'Human-reviewed reply summary' --source-ref 'private-email-id'
python3 engine.py draft qing-xiao # detects new outcome automatically
```

To add a new person, prepare a JSON researcher profile using `data/researchers.json` as a shape example, with dated public research evidence, two-sided question hypotheses and links. Then run `python3 engine.py import-researcher /path/to/new-person.json`. Profiles are **curated inputs**, not fabricated by a profile-name search.

Feedback is intentionally not scraped from Gmail. New real corrections go to gitignored `data/feedback.local.jsonl`; generated drafts go to gitignored `state/drafts/`. **Never publish actual unsent emails, raw replies, private source references or local feedback** to this public repository. Publishing changed learned weights is a separate review decision.

## What has been demonstrated (2026-10-29)

- Two **in-conversation** editorial preference pairs were converted into de-identified text comparisons; one provisional choice correction prefers `ORG-03` rather than `ORG-02` for Aneesh.
- The model fits both **training** preference pairs, and match selection changes for Aneesh from `ORG-02` (before feedback) to `ORG-03` (after feedback). Qing remains `ORG-01`. The two new generated emails differ and explicitly relate to their research. Results are available in `examples/`.
- There are **zero externally observed researcher replies**, no proof of out-of-sample writing improvement or increased collaboration rates, and **no scientific novelty verification**. These are future empirical measurements, not claimed successes.

## Current limitations

- Profiles/intersections are evidence-curated and do not automatically fetch new papers. Strong research matching still requires fresh literature verification for each new person; stale or unsupported interests must not be upgraded to facts.
- Generation is a **deterministic, data-driven baseline** that creates multiple personalized editorial structures and learns which to choose. It is not an LLM that autonomously discovers new concepts or rewrites arbitrary text. Connecting a local or approved model can extend that later, but is not claimed implemented here.
- Two preference pairs support only a first calibration. A real test needs **new researchers, blinded editorial assessment and eventual reply/research outcomes**, not more model-generated labels.

The project is intentionally small: one runtime, two JSON/JSONL inputs, one persistent learned model and executable tests. The objective is a progressively better research-collaboration process, not more governance artifacts.

## Optional locally generated candidate (explicitly invoked)

The offline draft above is a deterministic baseline. To let an installed, user-controlled **OpenAI-compatible local model** actually compose a new email from the research record and retrieved preference examples, use an endpoint you run yourself (for example an Ollama-compatible local server exposing `/v1/chat/completions`):

```bash
python3 engine.py draft qing-xiao --model-endpoint http://127.0.0.1:11434/v1/chat/completions --model-name <your-installed-model>
```

This returns both the deterministic draft and `model_candidate`. The model candidate is **not automatically promoted**, sent, or treated as fact-checked. The engine rejects model-invented URLs, but that cannot detect every invented claim. The command has no default model calls; there is no required paid API. HTTPS remote model endpoints require the extra `--allow-external-model` flag and must be explicitly authorized; private preference text is withheld from remote prompts. Use `CO_DO_API_KEY` only for the remote endpoint if needed. **No model endpoint was available in this execution environment, so model-based writing quality has not been validated.**
