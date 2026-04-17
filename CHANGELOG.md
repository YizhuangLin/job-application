# Changelog

All notable changes to the `job-application` skill are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/) loosely; versioning is [SemVer](https://semver.org/) (minor bumps = new phases or references; patch bumps = fixes or doc clarifications).

---

## 0.5.0 — 2026-04-17

### Changed (default behaviour)
- **Application tracker default changed from "user picks (Notion / Sheets / Airtable / Markdown)" to "flat markdown at `{{workspace}}/applications.md`".** Claude no longer prompts the candidate to connect Notion or any external tool for tracking — it creates and maintains the markdown file directly with the Edit tool. Notion, Google Sheets, and Airtable are now **opt-in adapters**, only routed to if the candidate explicitly asks for one.
- **Phase 8 rewritten** in SKILL.md: lead paragraph is now the default-backend declaration; removed "Notion, Google Sheet, or Airtable work equally well" phrasing that gave external tools equal billing and caused Claude to read Phase 8 as "pick whatever the candidate has."
- **`post-application.md` Part E restructured**: flat-markdown backend is the lead section; field-definition table remains tool-agnostic; new sub-sections **Part E.1 Notion adapter** and **Part E.2 Google Sheets adapter** hold the opt-in paths with setup checklists and "when is this a good fit" guidance. New closing section **Why flat markdown is the default** documents the three reasons (zero friction, portable/greppable, good-enough for realistic volumes).
- **README.md Requirements section** clarified: explicit "No external tracker required" callout; Notion MCP moved from "Optionally" list to "Opt-in upgrades" sub-point. **"Tracking without Notion"** section renamed to **"Upgrading past the default Markdown tracker"** and inverted: markdown is the baseline; Notion/Sheets are the upgrades, not fallbacks.

### Added
- `evals/04-tracker-default-markdown.md` — guards against regression: Claude auto-prompting for a Notion/Sheets connector instead of writing directly to `{{workspace}}/applications.md` when the candidate says "log this application."

### Why
Previous v0.4.0 framing said "Storage defaults to flat markdown table in the workspace; Notion, Google Sheet, or Airtable work equally well." The phrase "work equally well" is technically true but operationally ambiguous — it let Claude read Phase 8 as "ask the candidate where they want to track." In practice this showed up as Claude calling `search_mcp_registry` or asking "would you like to connect your Notion?" on first tracking action, which is a zero-to-one friction for OSS users who don't have Notion. Making the default unambiguous and relocating Notion/Sheets into named opt-in adapters removes that friction while keeping the upgrade paths documented for power users.

### Not changed
- Leon's personal workflow continues to use Notion (via `Job_Search_Progress.md` as Tier 1 SSOT + Notion as Tier 3 external mirror). This change affects the OSS default only — existing Notion users lose nothing.

---

## 0.4.0 — 2026-04-16

### Changed (correctness)
- **Hard Rules trimmed 14 → 8.** Implementation-level rules (XML escaping, three-tier sync protocol, per-company dossier creation, Entry Triage routing, salary-negotiation specifics) moved out of the hard-rules list and into their respective reference files and in-phase instructions. Top-level rules are now memorable.
- **Keyword density myth removed.** Phase 5b and `jd-analysis.md` Step 5b rewritten. Modern ATSs (Workday, Greenhouse, Lever, Ashby) parse resumes into structured fields rather than scoring on keyword density. New guidance: each top keyword appears naturally at least once in the Summary or a work bullet — do not force the same keyword into every section.
- **Timing and referral claims softened.** "60–80% of applications in first 3 days" replaced with "application volume concentrates in first 1–2 weeks for commercial roles, different timelines for exec / government / academic / deliberately-paced hires." "Referral converts at 5–10×" replaced with "roughly 3–5×, varies by industry and strength of connection."
- **Geographic and seniority variables added to page-count and timing rules.** Hard Rule 1 now permits 2 pages for senior / exec / academic / UK-EU CV traditions. Hard Rule 6 acknowledges exec / government / academic roles follow their own timelines.

### Changed (architecture)
- **SKILL.md slimmed 482 → ~225 lines.** Red flag table, cover-letter decision table, follow-up email template, and tracker field table were duplicated in `references/`; removed from SKILL.md. Each phase now holds routing logic + 3–5 key bullets and delegates depth to its reference file.
- **Reference Loading Map added** (new section after the phase list). Tells the model exactly which references to load per phase — replaces the flat 12-item bullet list and enables MVP-style tier loading.
- **Entry Triage Rule 1 changed to Lazy SSOT.** Previously "always confirm SSOT exists before running any phase, even Phase 10." Now: create `Context_Master.md` lazily on first Tier 1 write. Users entering at Phase 10 / 11 no longer forced through Phase 1 setup.
- **Follow-up email template + tracker fields moved to `post-application.md`** as new Part D and Part E. SKILL.md Phase 7 and Phase 8 now point to them.

### Added
- `CHANGELOG.md` (this file).
- `evals/` directory with 3 minimal test cases covering the most common entry points.
- Skill frontmatter now declares `version: 0.4.0`.

---

## 0.3.0 — 2026-04-16 (morning)

### Added
- **Entry Triage section** in SKILL.md routes users to the correct phase based on their situation (9-row table + 4 triage rules). Previously all users defaulted to reading Phase 1 linearly.
- **Quickstart table in README.md** mirrors the Entry Triage for external-facing users browsing the repo.
- **Per-company dossier template** (`references/company-dossier-template.md`). Every active-pipeline company gets a dedicated file at `{{workspace}}/companies/{{Company}}.md` — 10 sections covering quick facts, fit rationale, JD excerpt, research notes, contacts, interview log (one entry per round), offer log, closure and lessons learned.
- **Phases 4, 10, 11 updated** to open or update the dossier at the right trigger points.

### Changed
- Hard Rules expanded to 14 with Rule 13 (dossier for active-pipeline companies) and Rule 14 (triage before running phases). *Both removed in 0.4.0 — see above.*

---

## 0.2.0 — 2026-04-16 (early)

### Added
- **Three-tier document sync model** (`references/sync-rules.md`). Tier 1 SSOT → Tier 2 derivatives (auto-synced by Claude) → Tier 3 external mirrors (manual sync, status tracked). Change-log format standardised.
- **Context master template** (`references/context-doc-template.md`). 11-section SSOT template: identity, work history, projects & metrics, education, skills, resume file paths, positioning, career plan, external mirrors, pipeline, change log.
- Hard Rule 12 (three-tier sync) added to enforce propagation. *Absorbed into `sync-rules.md` in 0.4.0.*

---

## 0.1.0 — 2026-04-15

### Added
- Initial 11-phase workflow covering candidate intake → resume assessment → job search → company research → per-JD customisation → cover material → submission & follow-up → tracking → response diagnostics → interview prep → salary negotiation.
- References: `resume-standards.md`, `jd-analysis.md`, `company-research.md`, `cover-letter.md`, `referral-strategy.md`, `build-script.md`, `interview-prep.md`, `salary-negotiation.md`, `post-application.md`.
- 11 Hard Rules, `.docx` + `.pdf` dual output, ATS-safety validation.

---

## Versioning guide

- **Major** (1.0+) — reserved for breaking changes to SKILL.md phase structure or reference filenames
- **Minor** — new phases, new reference files, new hard rules, or significant workflow additions
- **Patch** — doc corrections, clarifications, template tweaks, link fixes
