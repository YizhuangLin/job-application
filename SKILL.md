---
name: job-application
version: 0.6.0
description: "End-to-end job application workflow: candidate profile intake, resume red-flag detection, ATS-compliant optimisation, company research, targeted job search, per-JD resume and cover letter customisation, timed submission, active follow-up, and response-rate diagnostics. Use this skill whenever the user wants to search for jobs, prepare or update a resume, generate customised resumes or cover letters for specific postings, track applications, diagnose low response rates, or manage the full job hunting pipeline. Trigger on phrases like 'apply for jobs', 'find me jobs', 'customise my resume', 'job search', 'help me apply', 'update my resume for this role', 'track my applications', 'I'm not getting callbacks', 'why am I not hearing back', or any variant of job hunting or career workflow."
---

# Job Application Workflow

A full-cycle job-search skill covering a brief Phase 0 reality check plus 11 execution phases from candidate intake through salary negotiation. This file is a **router** — it holds the workflow structure, triage logic, and the 8 hard rules. Every phase delegates depth to a `references/` file so this top-level document stays readable and token-efficient.

**Phases:** [0. Reality Check](#phase-0--reality-check) · [1. Candidate Intake](#phase-1--candidate-intake) · [2. Resume Assessment](#phase-2--base-resume-assessment) · [3. Job Search & Timing](#phase-3--job-search--timing) · [4. Company Research & Referral](#phase-4--company-research--referral-check) · [5. Per-JD Customisation](#phase-5--per-jd-resume-customisation) · [6. Cover Material](#phase-6--cover-material) · [7. Submission & Follow-up](#phase-7--submission--follow-up) · [8. Tracking](#phase-8--application-tracking) · [9. Response Diagnostics](#phase-9--response-rate-diagnostics) · [10. Interview Prep](#phase-10--interview-preparation) · [11. Offer & Negotiation](#phase-11--offer--salary-negotiation)

---

## Reference Loading Map

Load only the references relevant to the current phase. All references live under `references/`.

| Phase / Trigger | Load these references |
|---|---|
| **Phase 0** — reality check | *(none — the 3 questions live in this file)* |
| **Phase 1** — intake | `context-doc-template.md` · `sync-rules.md` · `resume-standards.md` |
| **Phase 2** — resume assessment | `resume-standards.md` |
| **Phase 3** — search & timing | `jd-analysis.md` |
| **Phase 4** — research & referral | `company-research.md` · `referral-strategy.md` · `company-dossier-template.md` (High Match only) |
| **Phase 5** — per-JD customisation | `jd-analysis.md` · `resume-standards.md` · `build-script.md` |
| **Phase 6** — cover material | `cover-letter.md` |
| **Phase 7** — submission & follow-up | `post-application.md` (follow-up template) |
| **Phase 8** — tracking | `post-application.md` (tracker fields) |
| **Phase 9** — response diagnostics | `resume-standards.md` · `post-application.md` · `coping.md` (if ≥ 15 apps in last 7 days or candidate reports burnout) |
| **Phase 10** — interview prep | `interview-prep.md` · `company-dossier-template.md` · `coping.md` (if interview in ≤ 48h, load Part 3) |
| **Phase 11** — offer & negotiation | `salary-negotiation.md` · `company-dossier-template.md` · `coping.md` (if candidate expresses offer anxiety, load Part 4) |
| Any rejection received for a High Match role | `coping.md` (Part 1 — 24-hour protocol) |
| Any Tier 1 fact change | `sync-rules.md` (always) |

---

## Phase 0 — Reality Check

Before routing to a phase, gauge the user's current capacity. The full 11-phase flow is designed for a candidate with real time, clear targets, and structural patience. A user applying in a 3-week emergency does not need an 11-section Tier 1 SSOT. A user with 2 hours per week should not be pushed through a dossier template for every High Match company. Match the skill's strictness to the user's situation.

**Three quick questions** (ask only the ones not already obvious from context):

1. **Time commitment.** Roughly how many hours per week can you put into this search?
2. **Target clarity** (1–5). How clearly can you describe the role / industry / level you want?
3. **Urgency.** Casual browse, active but flexible, or urgent (< 4 weeks runway)?

**Map to a strictness tier:**

| Strictness tier | When it applies | How the rest of the skill changes |
|---|---|---|
| **light** | ≤ 2 h/week · clarity ≤ 2 · or clearly casual | Skip Phase 1 SSOT setup. Skip company dossiers. Use a minimal tracker (just `Company · Role · Applied date · Stage`). Keep one master resume, customise only Summary per JD. Skip cover letters for Medium / Low Match. |
| **standard** *(default)* | 3–10 h/week · clarity 3–4 · active search | Full flow as written below. SSOT created lazily on first Tier 1 write. Dossier for High Match only. Cover letter when JD asks or for High Match. |
| **deep** | 10+ h/week · clarity 4–5 · urgent or career-pivot | Full flow + proactive SSOT + dossier for every High / Medium Match + full Phase 4a referral check before every application + tighter change-log discipline. Short deliberate rhythm (see `coping.md` Part 5). |

**Declare the tier to the user** once chosen, in one sentence: *"Running in **light** mode — I'll skip the full profile setup and keep tracking minimal. Tell me if you want to switch to standard later."* The tier is a soft setting; the user can upshift or downshift between phases.

**Tier is not a quality gate.** A light-tier application to a well-chosen role can out-perform a deep-tier application to a poorly-matched one. Strictness is about how much process the candidate can sustain, not about how "serious" they are.

**Skip Phase 0 if:**

- The user arrives with a specific, narrow request (e.g. "customise this resume for this JD") — treat as **standard** and route directly. Re-offer Phase 0 if they return with a broader ask.
- The user has used this skill before and a `{{Name}}_Context_Master.md` already exists in the workspace. Assume continuity, but re-ask urgency if they mention a change in circumstances.

---

## Entry Triage — Route the User Before Starting

After (or alongside) Phase 0's strictness check, route the user to the phase that matches their situation. **Do not default to Phase 1.**

**First question to ask** (if not already clear from context):
> "Where are you in your job search right now?"

Route based on their answer:

| User situation | Start at |
|---|---|
| First time job-searching / career transition / no resume | Phase 1 |
| Have a resume, haven't started searching | Phase 2 |
| Want to find suitable postings | Phase 3 |
| Have a specific JD to apply to | Phase 4 → 5 → 6 → 7 |
| Already applied, managing pipeline | Phase 8 |
| Applied to many roles, no replies | Phase 9 |
| Received an interview invitation | Phase 10 |
| Received an offer / in negotiation | Phase 11 |
| Just wants tracking structure (no active search) | Phase 8 only |

**Triage rules:**

1. **SSOT is lazy — applies to every phase, not just entry.** Only create `{{Name}}_Context_Master.md` on the first commit of a Tier 1 fact (employer, title, dates, metric, degree, contact). Phases 2 / 3 / 5 / 10 / 11 must run without an SSOT if the user has not yet written one; back-fill missing fields inline as they come up. Never block a downstream phase on "the SSOT doesn't exist yet."
2. **Dossiers are lazy too.** Only create `{{workspace}}/companies/{{Company}}.md` at Phase 4 (High Match, before cold-applying) or Phase 10 (interview invitation). Do not create empty dossiers for Medium / Low Match cold applies.
3. **Do not force-read earlier phases.** Back-fill missing context inline; earlier phases are prerequisites only when a specific fact is actually needed downstream.
4. **If the user is unsure,** ask 1–2 clarifying questions, then route. Never guess silently.
5. **After completing the entry phase,** suggest the natural next phase without enforcing it.
6. **Light-tier users skip most of Phases 1, 4, 8.** See Phase 0 for the per-tier differences.

---

## Phase 1 — Candidate Intake

Run Phase 1 only when the user is building a profile from scratch or explicitly asks to. Users entering later phases do not need to complete Phase 1 first — back-fill Tier 1 facts as they surface downstream.

When Phase 1 is the right entry, the authoritative source is the candidate's own resume file; never rely on platform profiles (LinkedIn, Indeed) — they're often outdated.

**Steps:**

1. **Get the resume.** Ask the user to upload or share it. Extract text: `pandoc resume.docx -t plain`.
2. **Confirm key facts** with the candidate, covering the sections in `references/context-doc-template.md` (identity · work history · projects & metrics · education · skills · target roles · work authorisation · LinkedIn URL).
3. **LinkedIn gap check.** Confirm titles, dates, and companies match the resume. Flag any mismatch — HR cross-references, and discrepancies raise doubts.
4. **Create the Tier 1 SSOT on first commit.** The first time the candidate confirms a hard fact in this session (or any later phase), create `{{CandidateName}}_Context_Master.md` by copying `references/context-doc-template.md` to the workspace, write the confirmed facts in, and follow `references/sync-rules.md` from that point (Tier 1 first, propagate to Tier 2, flag Tier 3 as ⏳, append Change Log row). If the user is only browsing or exploring, do **not** create the file — conversation-only is fine until a real Tier 1 write happens.

**Light tier:** Steps 1–3 only. Skip Step 4 unless the candidate explicitly asks for a persistent profile doc.

---

## Phase 2 — Base Resume Assessment

Read `references/resume-standards.md` before making any changes.

1. **ATS compliance check.** Run the technical checklist in `resume-standards.md`. Fix failures before proceeding.
2. **Red flag scan.** Identify signals that cause automatic or instinctive rejection (employment gaps, job hopping, title regression, over-qualification, resume ≠ LinkedIn, no metrics anywhere). Full list + mitigations live in `resume-standards.md`. Surface any flags to the candidate and agree on a mitigation strategy.
3. **Content & length.** Check page count against Hard Rule 1. Compression order: older roles → short-tenure roles → Summary trim → Skills row overflow.

---

## Phase 3 — Job Search & Timing

### Application timing — matters for most roles, not all

For commercial, high-demand roles (engineering, marketing, sales, ops, early-career analyst/associate), application volume concentrates in the first 1–2 weeks and early applicants get more recruiter attention. Practical rule:

> Submit within 48 hours of posting when possible; still worth applying for 2–3 weeks after.

**Exceptions** — time pressure eases substantially for exec / VP / C-suite, government and public sector (fixed windows), academic / research, and deliberately-paced hires. For these, check the posting's stated deadline or typical timeline rather than reflexively deprioritising. When flagging a posting, note both its age **and** its role category.

### Search and filter

Use `search_jobs` with `country_code` and `job_type` matching the candidate's targets. Run parallel searches across 2–3 categories with multiple keyword variants. Fetch full JDs with `get_job_details`.

Filter per `references/jd-analysis.md` Step 2 (exclusion rules + flag-for-confirmation list). Present results as a table: `# | Title | Company | Location | Posted | Type | Match | Notes`. Flag anything posted > 14 days (with role-category caveat above). Get candidate confirmation before proceeding.

---

## Phase 4 — Company Research & Referral Check

### 4a. Referral check (first)

Before cold-applying to any High Match company, read `references/referral-strategy.md` and ask:

> "Do you know anyone who works at [Company], or who might be connected to someone there?"

A referral typically converts to an interview at roughly **3–5× the rate** of a cold application (varies by industry, seniority, and strength of the connection). If a connection exists, draft the referral request per `referral-strategy.md` and send before or alongside the application.

### 4b. Company research

Read `references/company-research.md` for the full framework (stage, recent signals, why-this-role-exists, pain points). Do this **before** customising the resume — company context shapes Summary tone, which achievements to surface, and the cover note's angle.

**Open a dossier for High Match companies** (standard + deep tiers). Copy `references/company-dossier-template.md` to `{{workspace}}/companies/{{Company}}.md` and fill sections 1–5 as you research. For Medium/Low Match, skip the dossier until they respond — an empty file per cold apply is overhead.

**Light tier:** skip the dossier entirely. Keep company research in-chat; only create a dossier if the candidate reaches Phase 10 for this company.

---

## Phase 5 — Per-JD Resume Customisation

Read `references/jd-analysis.md` for the full keyword, gap, and placement framework; `references/resume-standards.md` for content standards; `references/build-script.md` for generation.

**Does not require Phase 1 to be complete.** If the candidate goes straight to Phase 5 with a JD and a resume, customise against what's in the resume. Back-fill any missing Tier 1 fact (e.g., a metric or date inconsistency you catch) into `{{Name}}_Context_Master.md` — creating the file if this is the first Tier 1 commit.

1. **Gap analysis + keyword matrix.** Map every JD requirement to the candidate's resume. Never add skills the candidate doesn't have.
2. **Keyword placement (natural, not stuffed).** Modern ATSs (Workday, Greenhouse, Lever, Ashby) parse into fields — real screening is done by recruiters. Keyword-density scoring is largely a myth. Confirm each top keyword appears **at least once in the Summary or a work bullet**. Do not force the same keyword into every section — that reads as stuffing.
3. **Job category → Skills row order.** Technical/Dev → technical row first; Marketing/SEO → marketing row first; Mixed → whichever is more prominent in the JD.
4. **Per-version edits.** Rewrite Summary using the formula in `jd-analysis.md` Step 4; reorder Skills rows; adjust bullets to incorporate JD terminology naturally without fabrication.
5. **File management.** Name: `APP[NNN]_[CompanySlug]_[RoleSlug]_[YYYY-MM-DD].docx/.pdf`. Always generate both formats (see `build-script.md`).

---

## Phase 6 — Cover Material

Read `references/cover-letter.md` for full format decision table, templates, red-flag addressing language, and per-stage tone guidance.

**Core principle:** cover material is a reason to open the resume, not a restatement of it. Open with something specific about the company (from Phase 4 research). Map the strongest relevant achievement to the company's evident need. End with one clear ask.

Never open with "I am writing to express my interest in…" — the most common opening, signals no effort.

---

## Phase 7 — Submission & Follow-up

**Submission steps:**

1. Open job URL in browser.
2. Identify application method — platform Easy Apply / company ATS (Greenhouse / Workday / Lever) / email.
3. If login or registration required, open the page and ask the candidate to complete before continuing.
4. Map profile to form fields. For `Sponsorship required?`, answer based on the candidate's authorisation status.
5. Show preview → wait for candidate confirmation → submit.
6. Record in tracker immediately.

**Follow-up:** schedule one follow-up for 5–7 business days after submission if no reply. Template and reactive-follow-up guidance in `references/post-application.md` Part D. Hard Rule 7: one follow-up maximum.

---

## Phase 8 — Application Tracking

**Default backend: flat markdown at `{{workspace}}/applications.md`.** Create the file on first submission using the column set in `references/post-application.md` Part E. Claude maintains it directly with the Edit tool — no external tool setup required, no connector prompt.

Update Stage and Outcome immediately after each action. A stale tracker is useless for Phase 9 diagnostics ("applied 3 weeks ago, no stage update" is indistinguishable from "rejected silently and forgot to log").

**Do not prompt the candidate to connect Notion, Google Sheets, or Airtable.** Only route to an adapter if the candidate **explicitly** asks for one — see `post-application.md` **Part E.1 (Notion adapter)** and **Part E.2 (Google Sheets adapter)**. These are opt-in upgrades, not defaults.

**Light tier:** keep tracker columns minimal — `Company · Role · Applied date · Stage · Notes`. Skip Match Level, Apply Method, Follow-up dates, and Resume File path unless the candidate asks for them later.

**On receiving a rejection for a High Match role (any tier):** load `references/coping.md` Part 1 and run the 24-hour protocol before queuing a replacement application.

---

## Phase 9 — Response Rate Diagnostics

Trigger when the candidate has applied to **10+ roles with fewer than 2 responses**, or when they say "I'm not hearing back." Re-read `references/resume-standards.md` Red Flags section and work through the 4-step framework in `references/post-application.md`:

1. **Targeting** — genuine match to experience level? consistent late applications? right platforms?
2. **Resume** — ATS compliance? Summary signals role type? Keywords in Summary/bullets (not just Skills)? Unaddressed red flags?
3. **Volume / mix** — High / Medium / Low breakdown? Enough High Match? Too narrow or too diluted?
4. **Other filters** — work authorisation knock-outs? Salary expectations above budget? Location / commute mismatches?

Output: 1–2 resume fixes, any targeting adjustment, any timing adjustment, any red flag to address proactively.

**Burnout check before prescribing more volume.** If the candidate has submitted ≥ 15 applications in the last 7 days, or reports low sleep / emotional flatness / inability to describe why they want the target role, load `references/coping.md` Part 2 and run the burnout check first. Do not recommend "apply to more" when the signal is fatigue, not targeting.

---

## Phase 10 — Interview Preparation

Trigger on interview invitation. Read `references/interview-prep.md` for STAR framework, per-interview-type question banks, and thank-you email template. Do **not** route this phase back to Phase 1 if no SSOT exists — back-fill any missing facts inline as they come up.

**Open the company dossier first.** If one doesn't exist, copy `references/company-dossier-template.md` to `{{workspace}}/companies/{{Company}}.md` and fill sections 1–5 from existing research. Every round and every subsequent touchpoint logs there. If it exists, re-read sections 4 (JD excerpt) and 5 (research notes) so prep stays anchored.

**If interview is in ≤ 48 hours:** also load `references/coping.md` Part 3 (pre-interview stabilization) and run it with the candidate at T–30 minutes. Preparation quality has diminishing returns past a point; nervous-system regulation often doesn't.

**Within 24 hours of invitation:** confirm logistics; re-read the exact JD and the resume version submitted; prepare 5–6 STAR stories mapped to the JD's top requirements; research interviewers on LinkedIn (add to dossier section 6); prepare 3 questions to ask.

**During / immediately after the interview:** capture the round in dossier section 7 within 2 hours — verbatim questions, answer strategy used, what they revealed about team/scope, red/green flags, self-assessment.

**After:** send a thank-you email within 24 hours referencing one specific thing from the conversation. Update tracker to Interview stage. Log the thank-you send in dossier section 7.

---

## Phase 11 — Offer & Salary Negotiation

Trigger on verbal or written offer. Read `references/salary-negotiation.md` for full anchoring principles, counter scripts, and non-salary negotiation paths.

Phase 11 does not require a pre-existing SSOT — if one doesn't exist, capture the offer details directly in the dossier (section 8 Offer Log) and back-fill Tier 1 only if a fact from the offer (e.g., new salary baseline) is worth preserving for the next negotiation.

**If the candidate expresses anxiety about countering or fear of rescission:** load `references/coping.md` Part 4 before writing the counter. The fear is usually over-calibrated relative to the actual rescission rate; the candidate deserves the numbers.

**Immediate actions on receiving an offer:**

1. Express genuine enthusiasm — do not negotiate in the same breath.
2. Ask for the offer in writing if not already provided.
3. Request time to review (3–5 business days is standard).
4. Evaluate the full package — not just base.

**Before countering:** is base below target (not floor)? Is there room in this type of role/company/sector? What is the candidate's priority (base / bonus / flex / title / remote)?

**Standard counter:** state enthusiasm, name your anchor, ask about flexibility. If base is firm, negotiate other elements. Full scripts in `salary-negotiation.md`.

**Log every exchange in dossier section 8 (Offer Log)** — initial breakdown, every counter, every response, final accepted package. This becomes the baseline for the candidate's next negotiation. Once resolved, fill in dossier section 9 (Closure & Lessons Learned).

---

## Hard Rules

The eight non-negotiables. Implementation details (XML escaping, three-tier sync protocol, dossier creation, triage routing, salary-negotiation specifics) live in their respective reference files and in-phase instructions — do not hoist them up here.

1. **1 page preferred** — compress before extending. Senior / exec roles, academic CVs, and UK / EU CV traditions may legitimately run to 2 pages; do not forcibly compress a 15+ year career into 1 page just to hit the rule.
2. **Both formats** — always deliver `.docx` + `.pdf`.
3. **ATS-safe format** — no tables, text boxes, images, or critical content in headers/footers. Engine-level validations (character escaping, XML balance) are enforced in `references/resume-standards.md` and `references/build-script.md`.
4. **No fabricated skills** — note gaps honestly; never add unclaimed tools, certifications, or years of experience.
5. **Check referral path first** — before cold-applying to any High Match company, check if the candidate has a connection.
6. **Apply early when timing matters** — for most commercial roles (engineering, marketing, sales, ops), submit within 48 hours of posting and treat postings > 2 weeks old as deprioritised. For exec, government, academic, or deliberately-paced hires, follow that category's typical timeline — early application matters less.
7. **One follow-up maximum** — after 5–7 business days, once only.
8. **Resume = LinkedIn** — if they diverge on titles, dates, or companies, fix LinkedIn before applying.
