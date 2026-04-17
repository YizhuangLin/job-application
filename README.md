# job-application — Claude Cowork Skill

**[🌐 Landing Page](https://cestduleon.dev/job-application/)**

A full-cycle job application skill for [Claude Cowork](https://claude.ai). Drop it into your `.claude/skills/` directory and Claude becomes an end-to-end job search partner: from building your candidate profile through interview prep and salary negotiation.

---

## Quickstart — find your entry point

You don't need to start at Phase 1. Pick the row that matches where you are:

| You are… | Say something like… | Claude will start at |
|---|---|---|
| 🆕 **First time job-searching** or changing careers | *"Help me set up my job search"* | Phase 1 — builds your candidate profile + master context doc |
| 📄 **Have a resume**, need an honest review | *"Review my resume for ATS and red flags"* | Phase 2 — resume assessment |
| 🔍 **Want to find jobs** matching your profile | *"Find me jobs"* / *"Search for [role] in [city]"* | Phase 3 — job search + timing filter |
| 🎯 **Found a specific posting** you want to apply to | *"Help me apply to this role: [URL or JD]"* | Phase 4 → 5 → 6 → 7 — company research, referral check, per-JD resume, cover material, submission |
| 📊 **Managing an active pipeline** | *"Help me track my applications"* | Phase 8 — application tracking |
| ⚠️ **Applied to many, no callbacks** | *"I'm not getting replies — what's wrong?"* | Phase 9 — response-rate diagnostics |
| 💬 **Got an interview invitation** | *"Prepare me for my interview at [Company]"* | Phase 10 — interview prep + company dossier |
| 💰 **Received an offer** | *"Help me evaluate / negotiate this offer"* | Phase 11 — offer evaluation + negotiation |

Claude reads only the reference files relevant to your entry phase, keeping the conversation fast and focused. You can jump between phases as your situation evolves — e.g. finish Phase 5 for one role, then switch to Phase 10 for an interview at a different company.

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

**No external tracker required.** The default application tracker is a flat markdown file at `{{workspace}}/applications.md`, maintained by Claude with the Edit tool. You do not need Notion, Google Sheets, Airtable, or any account to use Phase 8.

The skill uses these Claude tools when available:
- `search_jobs` / `get_job_details` — live job board search (Indeed via job-application MCP)
- `get_company_data` — company research
- `get_resume` — reads the candidate's resume file
- *(Opt-in upgrades)* Notion MCP or Google Sheets MCP — only if you want to move past the default Markdown tracker; see `references/post-application.md` Part E.1 / E.2

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
├── SKILL.md                           ← Main skill definition (loaded by Claude)
├── CHANGELOG.md                       ← Version history (SemVer + Keep a Changelog)
├── evals/                             ← Minimal prompt-level regression tests
│   ├── README.md                      ← How to run · scenarios table · template
│   ├── 01-entry-triage.md             ← Guards Phase 2 routing for users with a resume
│   ├── 02-interview-prep-lazy-ssot.md ← Guards Phase 10 against forced Phase 1 setup
│   └── 03-keyword-placement.md        ← Guards against keyword-density stuffing
└── references/
    ├── context-doc-template.md        ← Tier 1 SSOT template — your master profile doc
    ├── sync-rules.md                  ← Three-tier document sync protocol + change log format
    ├── company-dossier-template.md    ← Per-company deep file (research · contacts · interview log · offer)
    ├── resume-standards.md            ← ATS checklist, document structure, red flags
    ├── jd-analysis.md                 ← Keyword extraction, placement, gap analysis
    ├── company-research.md            ← Research framework (stage, signals, what to extract)
    ├── cover-letter.md                ← When/how to write cover material; templates
    ├── referral-strategy.md           ← Network check, referral outreach scripts
    ├── build-script.md                ← Python helpers for .docx XML editing and PDF conversion
    ├── interview-prep.md              ← STAR framework, question bank, thank-you email
    ├── salary-negotiation.md          ← Package evaluation, counter scripts, anchoring
    └── post-application.md            ← Post-application reference (Parts A–E: referral · interview · salary · follow-up template · tracker fields)
```

Claude reads reference files on demand — only the ones relevant to the current phase are loaded, keeping token usage efficient.

---

## Key design principles

**Timing over volume.** For most commercial roles, application volume concentrates in the first 1–2 weeks after a posting goes live, so applying early raises the odds of a human reading your resume. Executive, government, and academic roles follow their own paced timelines — the skill treats timing per role category rather than applying one rule to all.

**Referral first.** Before cold-applying to any high-match company, the skill checks whether the candidate has a connection. A referral typically converts to an interview at roughly 3–5× the rate of a cold application — the exact multiplier varies by industry and the strength of the connection.

**No fabrication.** The skill never adds skills the candidate doesn't have. Gaps are noted honestly and addressed in cover material.

**ATS safety.** Every generated resume is validated for common ATS failure modes: no prohibited characters, no bare `&` in XML, no tables, no text boxes, no images, 1-page by default (2 pages allowed for senior / academic / UK-EU CV formats).

**One follow-up maximum.** After 5–7 business days with no response, one follow-up message. Never more.

---

## Adapting to your setup

### Upgrading past the default Markdown tracker

The default tracker is `{{workspace}}/applications.md` — zero setup, works immediately, good for up to ~100 applications per job-search cycle. If you want structured database views (filtering, rollups, kanban) or want to share the tracker with a partner / coach, the column set in `SKILL.md` Phase 8 + `references/post-application.md` Part E translates directly to Notion (Part E.1) or Google Sheets (Part E.2). Claude only routes to the adapter when you explicitly ask — the default behaviour is to write to the markdown file.

### Resume format

The `references/build-script.md` helper functions are written for `.docx` XML manipulation (the approach used by the Cowork docx skill). If you are working from a different base format, the phase logic in `SKILL.md` still applies — adapt the generation method to your tooling.

### Job board

The skill uses `search_jobs` / `get_job_details` from the [job-application MCP](https://github.com/anthropics/mcp-job-application) (Indeed connector). If you are using a different job board or connector, replace the search calls in Phase 3 — the filtering and prioritisation logic is connector-agnostic.

---

## Hard rules (the 8 non-negotiables)

1. **1 page preferred** — senior/exec, academic, or UK/EU CV traditions may legitimately extend to 2 pages
2. Always generate both `.docx` and `.pdf`
3. ATS-safe format only (no tables, text boxes, images, critical content in headers/footers)
4. No fabricated skills — gaps are noted, never invented
5. Referral check before every cold application to a high-match company
6. **Apply early when timing matters** — 48 hours for most commercial roles; exec / government / academic hires follow their own timelines
7. One follow-up only, after 5–7 business days
8. Resume must match LinkedIn before applying

Implementation details — XML escaping, three-tier document sync, per-company dossier creation, Entry Triage routing, salary-negotiation tactics — live in their respective reference files rather than being hoisted into the hard-rules list. This keeps the top-level rules memorable.

---

## License

MIT — use freely, adapt to your context, share improvements.
