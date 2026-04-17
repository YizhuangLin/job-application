# {{Candidate Name}} — Context Master (SSOT)

> **🔒 SSOT (Single Source of Truth)** — all candidate facts live here first.
> Last updated: {{YYYY-MM-DD}}
> Purpose: cross-session context recovery · single reference for all derived documents
> Contains: personal profile · work history · resume state · career plan · project pipeline
> Change rule: any fact change must begin in this document, then propagate (see Change Log at bottom). See `references/sync-rules.md` for the full propagation protocol.

---

## 1. Identity & Contact

| Field | Value |
|---|---|
| Full Name | {{Full Name}} |
| Preferred Name | {{Preferred}} |
| Email | {{email}} |
| Phone | {{phone}} |
| Location | {{City, Province/State, Country}} |
| Work Authorisation | {{citizen / PR / work permit / requires sponsorship}} |
| Languages | {{e.g. English (fluent), Mandarin (native)}} |

---

## 2. Work History

| Title | Company | Dates | Location | Type |
|---|---|---|---|---|
| {{Current Title}} | {{Company}} | {{YYYY.MM – present}} | {{City}} | {{FT / PT / Contract}} |
| {{Prior Title}} | {{Company}} | {{YYYY.MM – YYYY.MM}} | {{City}} | {{type}} |
| … | … | … | … | … |

> ⚠️ If the resume omitted any past role, note it here so all derivatives include it.

---

## 3. Core Projects & Quantified Achievements

> These are the metrics that appear on the resume. Edit numbers only here; all resumes inherit from this list.

| Project / Role | Period | Weight | Key Outcome |
|---|---|---|---|
| {{Project}} | {{YYYY.MM–}} | ⭐⭐⭐ / ⭐⭐ / ⭐ | {{quantified result: X% increase, $Y revenue, Z× traffic}} |
| … | … | … | … |

**Top 3 metrics for cover letters / interviews:**

1. {{metric 1}}
2. {{metric 2}}
3. {{metric 3}}

---

## 4. Education

| Credential | Institution | Dates | Field |
|---|---|---|---|
| {{Degree / Diploma}} | {{School}} | {{YYYY – YYYY}} | {{Major}} |

---

## 5. Skills — Tiered

| Domain | Level | Notes |
|---|---|---|
| {{e.g. SEO}} | Advanced | core selling point |
| {{e.g. WordPress}} | Intermediate+ | commercial projects |
| {{e.g. React}} | Beginner+ | needs one portfolio project |
| … | … | … |

Order matters — the resume skill line should match this priority.

---

## 6. Resume Files (Tier 2 Derivatives)

### Master
- `{{path to master .docx}}`
- `{{path to master .pdf}}`

### Customised per-JD
- `{{applications-folder}}/APP{{id}}_{{Company}}_{{Role}}_{{YYYY-MM-DD}}.docx` / `.pdf`

### Generation script variants (if applicable)
- `hybrid` — {{describe}}
- `web` — {{describe}}
- `seo` — {{describe}}
- …

---

## 7. Competitive Positioning

> One-line self-positioning the candidate will use in LinkedIn headline, About, and cover letter openings.

**Positioning statement:** {{one sentence}}

**Recommended LinkedIn Headline:**
> *{{Headline}}*

**Avoid labels like:** {{e.g. "Junior", "Former", misaligned titles}}

---

## 8. Career Plan (3–5 Years)

| Milestone | Target | Salary Reference |
|---|---|---|
| {{period}} | {{first-goal role}} | {{range}} |
| {{period}} | {{mid-term role}} | {{range}} |
| {{period}} | {{long-term role}} | {{range}} |

### Priority Target Roles

1. {{Role type 1}}
2. {{Role type 2}}
3. {{Role type 3}}

### High-Opportunity Industries / Geographies

- {{industry 1}}
- {{industry 2}}
- …

---

## 9. External Mirrors (Tier 3 — Manual Sync)

List all places a hiring manager could fact-check against the resume. Any Tier 1 change may require a manual edit here — the Change Log tracks which ones are still pending.

| Mirror | URL / Handle | Last synced |
|---|---|---|
| LinkedIn | {{url}} | {{YYYY-MM-DD}} |
| Personal site / Portfolio | {{url}} | {{YYYY-MM-DD}} |
| GitHub | {{url}} | {{YYYY-MM-DD}} |
| Notion tracker | {{url}} | {{YYYY-MM-DD}} |
| Indeed profile | {{url}} | {{YYYY-MM-DD}} |

---

## 10. Pipeline & Task Status

Short board of what's in flight. The full application table lives in the progress tracker (Notion or local Markdown); this section only captures *candidate-level* TODOs.

| Task | Status | Note |
|---|---|---|
| {{task}} | ✅ done / ⏳ pending / 🚫 dropped | {{reason}} |

---

## 11. Change Log

> Audit trail for all Tier 1 fact changes. Append new rows; never delete old ones.
> Follow the rules in `references/sync-rules.md`.

### Document tiers (reference)

| Tier | Files | Sync mechanism |
|---|---|---|
| **Tier 1 · SSOT** | This document | All fact changes start here |
| **Tier 2 · Derived** | Master resume · customised resumes · progress tracker · cover letters | Claude auto-syncs after Tier 1 edit |
| **Tier 3 · External** | LinkedIn · Notion · personal site · GitHub | Candidate syncs manually; Claude only flags ⏳ |

### Change records

| Date | Field / Change | Old → New | Tier 2 synced | Tier 3 status |
|---|---|---|---|---|
| {{YYYY-MM-DD}} | Initial creation of Master doc | — | {{files created}} | {{LinkedIn ⏳ · Portfolio ⏳}} |

**Legend:** `✅` synced · `⏳` pending manual sync · `—` no mirror exists.

---

*Template from `job-application` skill · adapt freely to fit your workflow.*
