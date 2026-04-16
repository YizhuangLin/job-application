---
name: job-application
description: "End-to-end job application workflow: candidate profile intake, resume red-flag detection, ATS-compliant optimisation, company research, targeted job search, per-JD resume and cover letter customisation, timed submission, active follow-up, and response-rate diagnostics. Use this skill whenever the user wants to search for jobs, prepare or update a resume, generate customised resumes or cover letters for specific postings, track applications, diagnose low response rates, or manage the full job hunting pipeline. Trigger on phrases like 'apply for jobs', 'find me jobs', 'customise my resume', 'job search', 'help me apply', 'update my resume for this role', 'track my applications', 'I'm not getting callbacks', 'why am I not hearing back', or any variant of job hunting or career workflow."
---

# Job Application Workflow

A full-cycle job application skill. Phases in order:

1. [Candidate Intake](#phase-1--candidate-intake)
2. [Base Resume Assessment](#phase-2--base-resume-assessment)
3. [Job Search & Timing](#phase-3--job-search--timing)
4. [Company Research & Referral Check](#phase-4--company-research--referral-check)
5. [Per-JD Resume Customisation](#phase-5--per-jd-resume-customisation)
6. [Cover Material](#phase-6--cover-material)
7. [Submission & Follow-up](#phase-7--submission--follow-up)
8. [Application Tracking](#phase-8--application-tracking)
9. [Response Rate Diagnostics](#phase-9--response-rate-diagnostics)
10. [Interview Preparation](#phase-10--interview-preparation)
11. [Offer & Salary Negotiation](#phase-11--offer--salary-negotiation)

**Reference files — read when indicated:**
- `references/resume-standards.md` — ATS rules, structure, red flags
- `references/jd-analysis.md` — keyword extraction, gap analysis, keyword frequency
- `references/company-research.md` — company research framework
- `references/cover-letter.md` — when and how to write cover letters
- `references/referral-strategy.md` — network and referral channel
- `references/build-script.md` — Python resume generation
- `references/interview-prep.md` — interview preparation on invitation
- `references/salary-negotiation.md` — offer evaluation and negotiation

---

## Phase 1 — Candidate Intake

Build a complete candidate profile before doing anything else. Never rely on platform profiles (LinkedIn, Indeed) — they are often outdated. The authoritative source is the candidate's own resume file.

### Step 1: Get the resume

Ask the user to upload or share their current resume. Extract text:

```bash
pandoc --track-changes=all resume.docx -t plain
```

### Step 2: Confirm key facts

Read the resume, then explicitly confirm these with the candidate:

**Identity & contact**
- Full name (and preferred name if different)
- Email · Phone · City / Province / Country
- Work authorisation (citizen / PR / work permit / requires sponsorship)

**Career targets**
- Target job types / titles
- Target location(s) — city, province, remote, or any combination
- Employment type — full-time / part-time / contract
- Deal-breakers — roles, industries, or companies to exclude
- Target salary range (optional)

**Online presence**
- LinkedIn URL — is it up to date? Does it match the resume's dates and titles?
- Portfolio / personal site URL
- GitHub or other work samples

**Skills not in the resume**
- Ask: "Are there tools or experiences you use regularly that aren't on your resume?"

### Step 3: LinkedIn gap check

Compare the resume to the LinkedIn profile (ask the candidate to confirm):
- Do job titles, dates, and companies match exactly?
- Is there a professional summary / headline?
- Are key achievements visible (not just job titles)?

Flag any mismatches — HR will cross-reference and discrepancies raise doubts.

### Step 4: Store the profile

Keep this structured in session:

```
Name:         [name]
Contact:      [email] · [phone] · [city, province]
Auth:         [authorisation status]
Targets:      [job types] | [locations] | [employment type]
Exclude:      [exclusions]
Salary:       [range or "not specified"]
Portfolio:    [URLs]
LinkedIn:     [URL + alignment status]
Key metrics:  [top 3 quantified achievements]
Resume file:  [path or "provided in conversation"]
```

---

## Phase 2 — Base Resume Assessment

Read `references/resume-standards.md` before making any changes.

### ATS compliance check

Run the technical checklist in `resume-standards.md`. Fix any failures before proceeding.

### Red flag identification

Before optimising, identify signals that may cause automatic or instinctive rejection. Read the **Red Flags** section in `references/resume-standards.md` for the full list. Common ones:

| Red flag | What HR thinks | Mitigation |
|---|---|---|
| Employment gap > 6 months | Unemployable? Fired? | Address briefly in summary or cover letter |
| 3+ jobs in under 4 years | Job hopper, commitment risk | Group contract roles; emphasise project-based framing |
| Title regression | Step backward = performance issue? | Explain context (relocation, pivot, family) |
| Overqualified for role | Will leave quickly | Tailor summary to show genuine fit |
| Resume ≠ LinkedIn | Dishonest or disorganised | Sync before applying |

Surface any red flags to the candidate and agree on how to address them before generating customised versions.

### Content & length assessment

Check page count (must be 1 page for most markets). Apply compression in this order:
1. Roles older than 10 years → 1 bullet or remove
2. Unrelated short-tenure roles (< 3 months) → remove
3. Summary > 3 lines → trim
4. Skills rows overflowing → trim or reorganise

---

## Phase 3 — Job Search & Timing

### Application timing — highest-impact factor

Most job postings receive 60–80% of their total applications within the **first 3 days**. HR attention and ATS ranking both favour early applicants. Instil this principle:

> "Apply within 48 hours of a job posting going live whenever possible."

When searching, note the posting date for each result. Flag any posting older than 2 weeks as lower priority (still worth applying, but deprioritise).

### Search strategy

Use `search_jobs` with `country_code` and `job_type` matching the candidate's targets.

Run parallel searches across 2–3 target categories. Use multiple keyword variants per category. Fetch full JD with `get_job_details` for every promising result.

### Filtering — flag immediately

❌ **Remove without asking:** hard skill mismatch (5+ years of unclaimed tool), eligibility restrictions the candidate fails, excluded geography.

⚠️ **Flag for confirmation:** part-time when full-time was requested, > 3-year experience gap, temporary when permanent was preferred, required relocation.

✅ **Proceed** for everything else.

### Result presentation

Table: `# | Title | Company | Location | Posted | Type | Match | Notes`

Include posting date. Mark anything posted > 14 days ago. Ask candidate to confirm target list before proceeding.

---

## Phase 4 — Company Research & Referral Check

### 4a. Referral check (do this first)

Before cold-applying to any High Match company, read `references/referral-strategy.md` and ask the candidate:

> "Do you know anyone who works at [Company], or anyone who might be connected to someone there?"

A referral message takes 5 minutes and converts 5–10× better than a cold application. If a connection exists, draft the referral request and send it before or alongside the application.

If no connection exists, proceed to cold application but apply within 48 hours and prioritise quality of customisation.

### 4b. Company research

Read `references/company-research.md` for the full framework.

Do this **before** customising the resume — company context should inform the summary tone, the achievements to surface, and the cover note's angle.

For each shortlisted company, quickly establish:

1. **Company stage & size** — startup / scale-up / enterprise / public / non-profit
2. **Recent news** — funding, launches, restructuring, new leadership (last 3–6 months)
3. **Why this role exists** — growth hire / backfill / new function? (often inferable from JD language)
4. **Culture signals** — from JD tone, Glassdoor reviews, LinkedIn team composition
5. **Pain points** — what problem is the hiring manager trying to solve?

Use this to answer: *"Why this company specifically, and what does the candidate offer that maps to their current situation?"*

This research informs:
- The Summary's angle (align to their growth stage and pain point)
- The Cover Letter's opening (reference something specific about the company)
- Application form answers ("Why do you want to work here?")

---

## Phase 5 — Per-JD Resume Customisation

Read `references/jd-analysis.md` for keyword extraction, gap analysis, and frequency guidance.

For each approved job:

### 5a. Gap analysis + keyword matrix

Map every JD requirement to the candidate's resume. Never add skills the candidate doesn't have.

### 5b. Keyword frequency (not just presence)

ATS systems score on **keyword density** — the same keyword appearing in the Summary, a work experience bullet, and the Skills section scores higher than appearing once. For the top 3–5 JD keywords, aim to place each across at least 2 sections naturally.

### 5c. Job category → Skills row order

- Technical / Dev → technical skills row first
- Marketing / SEO → marketing skills row first
- Mixed → whichever is more prominent in JD

### 5d. Per-version customisations

| Element | What to change |
|---|---|
| Summary | Match job title language; front-load most relevant metric; use JD's exact terminology |
| Skills rows | Reorder; surface JD keywords first within each row |
| Bullet phrasing | Incorporate top JD keywords naturally; move most relevant bullet first per role |

Summary formula:
```
[Role-matched title] with [X]+ years of [primary domain].
[Strongest relevant achievement: metric + method].
[Location / language note if market-relevant.]
```

### 5e. File management

Naming: `APP[NNN]_[CompanySlug]_[RoleSlug]_[YYYY-MM-DD].docx/.pdf`

Always generate both `.docx` and `.pdf`. See `references/build-script.md`.

---

## Phase 6 — Cover Material

Read `references/cover-letter.md` for the full framework and templates.

### Determine which format is needed

| Scenario | Format |
|---|---|
| JD explicitly requests a cover letter | Formal cover letter (3–4 paragraphs) |
| Application portal has a "message / note" field | Short note (< 120 words) |
| Email application (JD says "email us") | Short professional email |
| Indeed / LinkedIn Easy Apply (no field) | None |
| Competitive / senior role even without explicit request | Write one anyway |

### What good cover material does

- Opens with something specific about the company (use Phase 4 research)
- Maps the candidate's strongest relevant achievement to the company's evident need
- Does not repeat the resume — it **explains the story behind the numbers**
- Ends with one clear ask (an interview, a call), not "I look forward to hearing from you"

Never write "I am writing to express my interest in..." — this is the most common opening and signals no effort.

---

## Phase 7 — Submission & Follow-up

### Submission

1. Open job URL in browser
2. Identify application method: platform Easy Apply / company ATS (Greenhouse / Workday / Lever) / email
3. For login / registration required → open the page, ask candidate to complete, then continue
4. Map candidate profile to form fields
5. `Sponsorship required?` → answer based on candidate's authorisation status
6. Show preview → wait for candidate confirmation → submit
7. Record in tracker immediately

### Active follow-up (proactive)

After submitting, schedule a follow-up if no response in **5–7 business days**:

```
Subject: [Job Title] Application — [Candidate Name]

Hi [Name / "the hiring team"],

I applied for the [Job Title] role on [date] and wanted to confirm my application came through. I'm very interested in [specific thing about company from Phase 4 research] and believe my [specific skill/achievement] would be a strong fit.

Happy to share more or jump on a call.

[Name]
[Phone] | [Email]
```

Keep it short. One follow-up is professional; two or more is pressure.

### Reactive follow-up (company reaches out)

When a company replies asking for more detail:
- 3–5 sentences maximum
- Lead with concrete evidence: specific URLs, named projects, quantified outcomes
- Do not send a second cover letter
- End with a clear next step

---

## Phase 8 — Application Tracking

**Minimum fields per application:**

| Field | Values |
|---|---|
| Position | Job title |
| Company | Company name |
| Job Category | Technical / Marketing / Mixed |
| Apply Date | ISO date |
| Platform | Indeed / LinkedIn / Company website / Email / Referral |
| JD Link | URL |
| Resume File | Filename used |
| Stage | Applied → In Conversation → Interview → Offer → Closed |
| Outcome | Pending / Rejected / Withdrawn / Offer Accepted |
| Match Level | High / Medium / Low |
| Location | City + work type |
| Posting Date | When JD was originally posted |
| Follow-up Date | Scheduled follow-up (5–7 business days after applying) |
| Salary Range | Offered or posted range |
| Notes | Referral contact, red flags addressed, company research notes, interview feedback |

**Stage definitions:**
- **Applied** — submitted, waiting for first response
- **In Conversation** — HR screen scheduled or in progress
- **Interview** — hiring manager / panel interview confirmed or completed
- **Offer** — offer received, evaluating or negotiating
- **Closed** — role filled, rejected, withdrawn, or offer accepted

Update Stage and Outcome immediately after each action. Never let records go stale — a stale tracker is useless for diagnostics.

---

## Phase 9 — Response Rate Diagnostics

Trigger this phase when the candidate has applied to **10+ roles with fewer than 2 responses**, or when they explicitly say "I'm not hearing back."

Read `references/resume-standards.md` Red Flags section again — the issue is usually one of four root causes:

### Diagnostic framework

**Step 1 — Is the targeting right?**
- Are the roles a genuine match to the candidate's experience level?
- Is the candidate consistently applying more than 1 week after posting?
- Are they applying to the right platforms for their industry?

**Step 2 — Is the resume the problem?**
- Run the ATS compliance checklist again
- Check: does the Summary immediately signal what kind of candidate this is?
- Check: are the top JD keywords appearing in both the Skills section and at least one bullet?
- Check: are there any unaddressed red flags (gap, regression, mismatch)?

**Step 3 — Is the volume / mix right?**
- What is the breakdown of High / Medium / Low match applications?
- Are there enough High match applications?
- Is the candidate applying too narrowly (one category) or too broadly (diluted focus)?

**Step 4 — Is anything else filtering them out?**
- Work authorisation knock-out questions
- Salary expectations entered above budget
- Location / commute mismatches on application forms

### Output

After diagnosis, produce a short action list:
- 1–2 things to fix on the base resume immediately
- Targeting adjustment (if needed)
- Timing adjustment (apply earlier)
- Any red flag to address proactively in cover material

---

## Phase 10 — Interview Preparation

Trigger when the candidate receives an interview invitation. Read `references/interview-prep.md` for the full framework.

**Immediate actions (within 24 hours of invitation):**
1. Confirm logistics — format, duration, who is interviewing
2. Re-read the exact JD and the resume version submitted
3. Prepare 5–6 STAR stories mapped to the JD's top requirements
4. Research each interviewer on LinkedIn
5. Prepare 3 questions to ask (see reference file)

**Remind the candidate:** The interview is also their evaluation of the company. Note any red flags about team, scope clarity, or culture.

**After the interview:** Send a thank-you email within 24 hours referencing one specific thing from the conversation. Update the tracker to the Interview stage.

---

## Phase 11 — Offer & Salary Negotiation

Trigger when the candidate receives a verbal or written offer. Read `references/salary-negotiation.md` for the full framework.

**Immediate actions on receiving an offer:**
1. Express genuine enthusiasm — do not negotiate in the same breath
2. Ask for the offer in writing if not already provided
3. Request time to review (3–5 business days is standard)
4. Evaluate the full package — not just base salary

**Before negotiating, confirm:**
- Is the base below the candidate's target (not floor)?
- Is there room in this type of role / company / sector to negotiate?
- What is the candidate's priority — base / bonus / flexibility / title / remote?

**Standard counter approach:** State enthusiasm, name your anchor, ask if there is flexibility. If base is firm, negotiate other elements. See reference file for exact scripts.

Update tracker to Offer stage. Once resolved, mark Outcome as Offer Accepted or Withdrawn.

---

## Hard Rules

1. **1 page maximum** — compress or remove content before going to page 2
2. **Both formats** — always `.docx` + `.pdf`
3. **ATS format** — no tables, text boxes, images, or critical content in headers/footers
4. **XML `&` must be `&amp;`** — validate before packing
5. **No fabricated skills** — note gaps honestly; never add unclaimed tools
6. **Check referral path first** — before cold-applying to any High Match company, check if the candidate has a connection
7. **Apply within 48 hours** — flag any posting older than 2 weeks as deprioritised
8. **One follow-up maximum** — after 5–7 business days, once only
9. **Resume = LinkedIn** — if they diverge, fix LinkedIn before applying
10. **Never give your floor** — in salary discussions, always anchor above target; never disclose the minimum
11. **Get the offer in writing** — before giving notice or accepting verbally, confirm the written offer
12. **Sync all updates** — any information change propagates to master resume, all active PDFs, and tracking documents
