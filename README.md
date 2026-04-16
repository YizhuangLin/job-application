# job-application — Claude Cowork Skill

**[🌐 Landing Page](https://cestduleon.dev/job-application/)**

A full-cycle job application skill for [Claude Cowork](https://claude.ai). Drop it into your `.claude/skills/` directory and Claude becomes an end-to-end job search partner: from building your candidate profile through interview prep and salary negotiation.

---

## What it does

The skill covers 11 phases in a single workflow:

| Phase | What happens |
|---|---|
| 1. Candidate Intake | Builds a complete profile from your resume; flags LinkedIn mismatches |
| 2. Base Resume Assessment | ATS compliance check, red flag identification, 1-page compression |
| 3. Job Search & Timing | Searches live job boards; flags postings older than 2 weeks |
| 4. Company Research & Referral | Researches each shortlisted company; checks your network before cold-applying |
| 5. Per-JD Resume Customisation | Keyword matrix, gap analysis, targeted summary and skills rewrite |
| 6. Cover Material | Decides format (formal / short note / none) and drafts accordingly |
| 7. Submission & Follow-up | Guides browser-based submission; schedules one follow-up at day 5–7 |
| 8. Application Tracking | Maintains a structured log with stage, outcome, and follow-up dates |
| 9. Response Rate Diagnostics | Triggers when 10+ applications return fewer than 2 replies; surfaces root cause |
| 10. Interview Preparation | STAR story framework, question prep, thank-you email |
| 11. Offer & Salary Negotiation | Package evaluation, counter scripts, anchoring principles |

---

## Requirements

- **Claude Cowork** (desktop app) — available at [claude.ai](https://claude.ai)
- The **docx skill** installed alongside this one (provides `scripts/office/pack.py` and `soffice.py` for `.docx` + PDF generation)
- A `.docx` master resume to work from
- Optionally: a **Notion MCP** connector for application tracking in a Notion database

The skill uses these Claude tools when available:
- `search_jobs` / `get_job_details` — live job board search (Indeed via job-application MCP)
- `get_company_data` — company research
- `get_resume` — reads the candidate's resume file
- Notion MCP tools — for syncing the application tracker

---

## Installation

1. Copy this folder into your Cowork skills directory:
   ```
   ~/.claude/skills/job-application/
   ```
   The directory should contain `SKILL.md` and the `references/` subfolder.

2. In a new Cowork conversation, trigger the skill with any job-search phrase — for example:
   - *"Help me find jobs"*
   - *"Customise my resume for this posting"*
   - *"I'm not getting any callbacks"*
   - *"Prepare me for my interview at [Company] tomorrow"*

3. Claude will load the skill automatically and walk you through the relevant phase.

---

## File structure

```
job-application/
├── SKILL.md                        ← Main skill definition (loaded by Claude)
└── references/
    ├── resume-standards.md         ← ATS checklist, document structure, red flags
    ├── jd-analysis.md              ← Keyword extraction, gap analysis, frequency scoring
    ├── company-research.md         ← Research framework (stage, signals, what to extract)
    ├── cover-letter.md             ← When/how to write cover material; templates
    ├── referral-strategy.md        ← Network check, referral outreach scripts
    ├── build-script.md             ← Python helpers for .docx XML editing and PDF conversion
    ├── interview-prep.md           ← STAR framework, question bank, thank-you email
    ├── salary-negotiation.md       ← Package evaluation, counter scripts, anchoring
    └── post-application.md         ← Combined post-application reference (interview + salary + referral)
```

Claude reads reference files on demand — only the ones relevant to the current phase are loaded, keeping token usage efficient.

---

## Key design principles

**Timing over volume.** Most job postings receive 60–80% of applications in the first 3 days. The skill prioritises applying within 48 hours of a posting going live and flags older postings as lower priority.

**Referral first.** Before cold-applying to any high-match company, the skill checks whether the candidate has a connection. A referral converts to an interview at 5–10× the rate of a cold application.

**No fabrication.** The skill never adds skills the candidate doesn't have. Gaps are noted honestly and addressed in cover material.

**ATS safety.** Every generated resume is validated for common ATS failure modes: no Chinese characters, no bare `&` in XML, no tables, no text boxes, no images, 1-page limit.

**One follow-up maximum.** After 5–7 business days with no response, one follow-up message. Never more.

---

## Adapting to your setup

### Tracking without Notion

Replace Phase 8 Notion references with any flat file or spreadsheet. The minimum tracking fields are defined in `SKILL.md` Phase 8 — they work equally well in a local `.md` file or a Google Sheet.

### Resume format

The `references/build-script.md` helper functions are written for `.docx` XML manipulation (the approach used by the Cowork docx skill). If you are working from a different base format, the phase logic in `SKILL.md` still applies — adapt the generation method to your tooling.

### Job board

The skill uses `search_jobs` / `get_job_details` from the [job-application MCP](https://github.com/anthropics/mcp-job-application) (Indeed connector). If you are using a different job board or connector, replace the search calls in Phase 3 — the filtering and prioritisation logic is connector-agnostic.

---

## Hard rules (enforced throughout)

1. 1-page resume maximum
2. Always generate both `.docx` and `.pdf`
3. ATS-safe format only (no tables, text boxes, images, critical content in headers/footers)
4. No fabricated skills — gaps are noted, never invented
5. Referral check before every cold application to a high-match company
6. Apply within 48 hours — flag anything older than 2 weeks
7. One follow-up only, after 5–7 business days
8. Resume must match LinkedIn before applying
9. Never disclose your salary floor — always anchor above target
10. Get any offer in writing before giving notice

---

## License

MIT — use freely, adapt to your context, share improvements.
