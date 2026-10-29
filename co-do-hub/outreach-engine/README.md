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

## v0.2 research cognition runtime

`runtime.py research <name-or-official-HTTPS-homepage> --run-id <id>` autonomously
reads public source pages and Crossref metadata, asks GPT-6.1 Sol Low through the
existing OpenClaw gateway to interpret findings, generates falsification searches,
compares competing work, and may reject a match. A supported candidate receives
an English invitation and Chinese review draft, then a semantic revision using
relevant persisted human feedback. There is no sender, SMTP client, mail tool or
contact permission. All drafts require human factual and editorial review.

Use `--state /private/persistent/directory` BEFORE the subcommand. Default is
`/var/lib/co-do`; do not use a public checkout as private state. `learn` reuses the
original public seed and private `feedback.jsonl`, storing semantic lessons keyed
by the original revision digest. `feedback --researcher ID --before FILE --after
FILE --note TEXT` records actual human edits; do not feed model edits as human.
Run IDs are immutable input bindings and completed stages are reused after
restart. Errors persist as FAILED; invoke the same task to resume. No automatic
retries of failed model requests, fallback model, schedule or open network port.

For a paired evidence-controlled run, execute A with `--no-learning`, then B with
`--evidence-from A_RUN_ID`. The same discovery, interpretation and competition
bundles are reused byte-for-byte. This controls sources, not model randomness;
quality and novelty remain for human evaluation. `checks.json` reports only URL
membership and source digest, never semantic correctness or learning success.

On the existing host, a dedicated `co-do` user can invoke a root-owned fixed-model
adapter (`deploy/model_bridge.py`) via a single sudo rule; it accepts prompt text
on stdin, fixes gateway/model/thinking, and cannot execute arbitrary commands or
mail tools. This reuses existing OAuth and gateway credentials without copying
them into Co-Do or changing other applications. Model usage/cost metadata is
retained privately; it is not a cash billing receipt. Deploy code root-owned,
state co-do-owned mode 0700. Optional `co-do-research@RUN.service` is an explicit
oneshot worker, not a daemon or scheduler. Queue JSON under state/tasks and start
the instance manually; rerun the same instance to resume checkpoints.

Retrieval limitations: Crossref deposits may omit abstracts, and not every recent
paper is indexed; raw DOI pages can reject automated readers. The runtime reads linked original research pages, uses the public OpenReview API for submitted records, and can extract bounded PDFs with an already installed `pdftotext`; no dependency is automatically installed. It falls back to deposited Crossref DOI metadata where a publisher refuses access. Full retrieved text is retained privately; bounded source excerpts enter the model context. Metadata-only
sources must not support detailed result claims. URL membership cannot prove
entailment. Scholarly novelty, researcher interest and improved writing quality
are not automatically established. No contacts occur.

The existing entrypoint now exposes the new runtime directly:

```sh
python3 engine.py cognition --state /var/lib/co-do research https://juhokim.com/ --run-id study-a --no-learning
python3 engine.py cognition --state /var/lib/co-do research https://juhokim.com/ --run-id study-b --evidence-from study-a
python3 engine.py cognition --state /var/lib/co-do status study-b
```

The older `draft` command remains a v0.1 curated-template regression tool. It is
not research cognition and its scores are not scientific quality estimates.

Deployment uses a pinned checkout of this same repository under
`/srv/co-do/source`, an `outreach-engine` symlink to its existing engine directory,
root-owned code and `/var/lib/co-do` owned by a nologin system user `co-do`.
Install the model bridge root-owned at `/usr/local/libexec/co-do-model`; validate
this isolated sudoers rule with `visudo -cf` before use:

```text
co-do ALL=(root) NOPASSWD: /usr/local/libexec/co-do-model ""
```

Install the template unit from deploy/, then `systemctl daemon-reload` (does not
restart other services). Queue a private file `/var/lib/co-do/tasks/RUN.json`:

```json
{"researcher":"https://juhokim.com/","learning":false}
```

Start explicitly with `systemctl start --no-block co-do-research@RUN`. The unit
becomes inactive after successful completion by design; inspect `Result` and
`ExecMainStatus`, plus `state.json`. It is not enabled as an autonomous recurring
job. After a process or host restart, starting that same instance reuses its
persisted stages. No host-wide reboot is required or performed for validation.
Never expose private state or logs through the public repository or web server.
