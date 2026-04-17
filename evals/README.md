# Evaluation suite for `job-application`

Minimal test cases that verify the skill routes correctly and produces the right top-level shape of output. These are **prompt-level scenarios**, not unit tests — they exist to catch regressions when SKILL.md or references are edited.

## How to run

Manually, in a Claude Cowork conversation:

1. Start a fresh conversation with `job-application` installed.
2. Paste the **User message** from one of the scenario files.
3. Check Claude's response against the **Expected behaviour** section.
4. If Claude deviates, file the deviation against the current version (see `CHANGELOG.md`).

Automated harness is out of scope for v0.4. The scenarios are authored so a human reviewer can judge pass/fail in under 2 minutes each.

## Scenarios

| File | Entry point | What it guards against |
|---|---|---|
| `01-entry-triage.md` | Phase 2 (has resume, hasn't searched) | Claude defaulting to Phase 1 Candidate Intake when Entry Triage should route to Phase 2 |
| `02-interview-prep-lazy-ssot.md` | Phase 10 (interview in 2 days, no prior SSOT) | Claude forcing Phase 1 SSOT setup when user urgently needs interview prep (lazy-SSOT rule) |
| `03-keyword-placement.md` | Phase 5 (customising resume for a JD) | Claude recommending keyword-density stuffing (resurrection of the density myth removed in 0.4.0) |
| `04-tracker-default-markdown.md` | Phase 8 (first application logged) | Claude prompting for a Notion / Sheets connector instead of writing to `{{workspace}}/applications.md` (0.5.0 default-backend change) |

## Adding a new scenario

Create `NN-short-slug.md` with three sections:

```markdown
# Scenario: <one-line summary>

**Entry phase:** <Phase X>

**What this guards:** <single sentence — the regression this catches>

---

## User message

<paste the exact message the tester should send>

---

## Expected behaviour

- [ ] <bullet of observable thing Claude should do>
- [ ] <bullet of observable thing Claude should NOT do>
- [ ] ...

## Known failure modes

- <If Claude does X, that's a regression of Y>
```

Keep expected behaviours to things a human reviewer can check in 30 seconds of reading Claude's reply.
