# Scenario: Engine Mode routes state changes through build.py, not hand edits

**Entry phase:** Engine Mode (Phases 5–8 equivalent)

**What this guards:** Claude ignoring the bundled `auto-apply/` engine when it is present in the workspace — hand-editing the generated `applications.md` tables, drafting a customised resume as a free-form document, or skipping the JD-archiving gate. The 1.0.0 Engine Mode section makes the engine the mandatory execution path for resume generation and tracking when it is installed.

---

## Setup

Workspace contains `workspace.yaml` at the root and a copied `auto-apply/` directory (engine installed, `init` already run, SSOT and `master_resume.yaml` filled in). At least one prior application exists as `auto-apply/jobs/APP-001.yaml`.

## User message

> Found a posting I like: [pastes a job URL]. Customise my resume for it and log the application in my tracker.

---

## Expected behaviour

- [ ] Claude runs `python3 auto-apply/build.py status` first and treats its output as the current pipeline state.
- [ ] Claude starts the new application with `build.py prep --jd-url <URL>` (or `--jd-file` after fetching), so the raw JD text is archived in the new `APP###.yaml` — it does NOT begin rewriting resume content before the JD is captured.
- [ ] Resume customisation happens by filling the `rewritten` fields in `APP###.yaml` from the SSOT, not by drafting a standalone resume document.
- [ ] The fact-check step uses the prompt rendered by `build.py prompt --app APP### --type verifier` (not a hand-assembled prompt with pasted redlines).
- [ ] Tracking updates go through `build.py submit` / `build.py tracker`; Claude does NOT hand-edit the AUTO-GENERATED tables in `applications.md`.
- [ ] Before declaring the application ready to submit, Claude runs `build.py review --app APP###` and reports the four-gate result.

## Known failure modes

- Claude writes a new resume `.docx`/markdown directly from the conversation, bypassing `prep`/`make` → the anti-fabrication chain and page gate never run.
- Claude edits the `applications.md` table rows with the Edit tool → generated-artifact rule violated; next `build.py status` reports drift.
- Claude summarises the JD from memory instead of archiving the raw text → JD-archiving gate bypassed; the application cannot be re-audited later.
- Claude pastes the verifier template and manually substitutes `{{APP_ID}}` → workspace redlines (`fact_redlines` / `strategy_rules`) never get injected.
