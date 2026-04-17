# Sync Rules — Keeping Candidate Data Consistent Across Documents

> **Purpose:** Prevent silent divergence between the candidate context document, resume files, application tracker, and external profiles (LinkedIn, Notion, etc.). Without rules, each document drifts on its own and no one knows which version is authoritative.

---

## Three-Tier Document Model

| Tier | What it is | Examples | How it syncs |
|---|---|---|---|
| **Tier 1 — SSOT** | The *single source of truth* for all candidate facts | `{{candidate}}_Context_Master.md` (from `context-doc-template.md`) | Every fact change must start here |
| **Tier 2 — Derived** | Files generated or populated from Tier 1 data | Master resume (`.docx` / `.pdf`), customised per-JD resumes, progress tracker, cover letters | Claude updates these automatically when Tier 1 changes |
| **Tier 3 — External Mirrors** | Profiles on systems Claude cannot directly edit | LinkedIn, Indeed profile, Notion database, personal website, GitHub README | Claude can only draft the updated text and flag as "⏳ pending manual sync" |

The rule is strict: **never edit a Tier 2 or Tier 3 document to represent a fact change without also updating Tier 1 first**. Otherwise Claude (or the candidate) won't know next time which file is current.

---

## The Two Core Rules

### Rule 1 — Tier 1 is the only place facts originate

Any change to a "hard fact" (job title, dates, employer name, metrics, degree, certifications, skills, contact info) **must begin by editing the context document**. Then the change propagates outward.

A "hard fact" is anything a hiring manager could fact-check against LinkedIn, a reference, or a transcript.

Soft content (resume *phrasing*, cover letter paragraphs, headline copy) can be drafted in derived documents without touching Tier 1 — but any underlying **fact** they reference must already be in Tier 1.

### Rule 2 — Every Tier 1 change triggers three actions, in order

When Claude or the candidate modifies a Tier 1 field:

1. **Update the Master doc** — change the field, bump the "last updated" date at the top.
2. **Propagate to Tier 2** — grep all Tier 2 files for the old value; update each occurrence. If the old value is hard to grep (e.g. a re-phrased achievement), open each file and check manually.
3. **Log the change** — append one row to the Change Log table at the bottom of the Master doc. The row records: date, field, old → new, Tier 2 files touched, Tier 3 sync status.

Tier 3 gets a status flag, not an automatic edit:
- `⏳` — candidate must manually sync (e.g. edit LinkedIn About)
- `✅` — candidate has confirmed they've synced it
- `—` — no Tier 3 mirror exists for this field

---

## Change Log Format

The Change Log lives at the bottom of the Master doc. Each row:

```markdown
| YYYY-MM-DD | Field / Change | Old → New | Tier 2 files synced | Tier 3 status |
```

Example (generic):

```markdown
| 2026-05-12 | Current employer start date | 2024.11 → 2024.09 | Master resume · 3 customised resumes · progress tracker | LinkedIn ⏳ |
| 2026-05-14 | Top metric: website traffic | "3× growth" → "5× growth (20 → 100+/week)" | Master resume · all per-JD resumes | LinkedIn ✅ · Portfolio ⏳ |
```

**Never delete old rows.** The log is the audit trail that lets a future session spot whether a file might be stale.

---

## Workflow: When the Candidate Updates a Fact

Claude should follow this checklist whenever the candidate mentions a factual update:

1. **Ask which Tier 1 field this touches.** If the candidate just says "fix my resume", clarify: is this a *fact* change (updates Tier 1) or a *phrasing* change (Tier 2 only)?
2. **Edit the Master doc.** Update the field. Update the "last updated" date.
3. **Find all Tier 2 dependencies.**
   - For greppable strings (dates, numbers, company names): use grep and update each hit.
   - For paraphrased content (achievement bullets): open each resume file and verify.
4. **Update Tier 2 files.** Regenerate resumes if the template is script-driven; otherwise edit in place.
5. **Flag Tier 3.** Check the candidate's Tier 3 list (LinkedIn, Notion, portfolio). For each affected mirror, remind the candidate what needs manual updating, and mark `⏳` in the Change Log.
6. **Append Change Log row.** One line, no skipped columns.
7. **Confirm to the candidate.** Briefly summarise: "Updated field X in Master; synced to N resume files; you need to manually update LinkedIn and Portfolio."

---

## Common Failure Modes (and How to Catch Them)

**Failure 1 — Candidate edits the resume `.docx` directly without updating the Master.**
→ Claude's defence: when asked to customise a resume next time, re-read the Master and diff against the latest resume. If they disagree, ask the candidate which is correct, then reconcile both.

**Failure 2 — Different per-JD resumes carry different versions of the same metric.**
→ Claude's defence: the metric should live in a single field in the Master doc. Customisation varies *phrasing*, never the underlying number.

**Failure 3 — LinkedIn says Senior Manager but resume says Manager.**
→ Claude's defence: during Phase 1 Candidate Intake, explicitly ask "are LinkedIn title/dates identical to the resume?" If not, pick the accurate one, update Master, and log the LinkedIn sync as a task.

**Failure 4 — Change Log never gets written because Claude forgets.**
→ Claude's defence: treat the log row as non-optional. If a turn ends with Tier 1 touched but no log entry, the change is incomplete.

---

## How This Connects to the Rest of the Skill

- **Phase 1 — Candidate Intake:** the candidate's first action is copying `context-doc-template.md` to their workspace as their Tier 1 SSOT. All subsequent phases read from there.
- **Phase 5 — Per-JD Resume Customisation:** customised resumes are Tier 2. They inherit all facts from Tier 1; only phrasing varies per JD.
- **Phase 8 — Application Tracking:** the progress tracker (Notion or local file) is Tier 2 for candidate-level fields (salary target, contact info) and primary storage for application-level data (status, dates).
- **Phase 9 — Response Rate Diagnostics:** when low response rate triggers a resume revision, the revision changes Tier 1 fields (e.g. a reworded summary, a metric recalculation) — the Change Log captures this so diagnostics can correlate "what changed" with "what response rate improved".

---

## Minimal Setup (First-Time User)

1. Copy `references/context-doc-template.md` to the user's workspace, rename to `{{Name}}_Context_Master.md`.
2. Fill in Tier 1 fields from the candidate's current resume.
3. Note the workspace paths for Tier 2 files (master resume, applications folder, progress doc).
4. List Tier 3 mirrors the candidate uses (LinkedIn URL, Notion URL, personal site, etc.).
5. Add the first Change Log row: "Initial creation" with today's date.

From this point forward, every hard-fact change follows Rules 1 and 2.
