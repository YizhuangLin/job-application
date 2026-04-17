# Scenario: Entry Triage routes user with existing resume to Phase 2

**Entry phase:** Phase 2

**What this guards:** Claude defaulting to Phase 1 Candidate Intake when the user has already stated they have a resume. The Entry Triage table (post-0.3.0) exists specifically to prevent this regression.

---

## User message

> Hi — I have a 2-page resume I've been using for the last year. I haven't actually started job-searching yet but I want to make sure the resume is solid first. Can you help?

---

## Expected behaviour

- [ ] Claude routes to **Phase 2 — Base Resume Assessment**, not Phase 1.
- [ ] Claude asks for the resume file (or reads it if the user has already attached one) and refers to `references/resume-standards.md`.
- [ ] Claude does NOT launch into a full Tier 1 SSOT setup sequence (Phase 1 Step 4) before the user has even shared the resume.
- [ ] Claude does NOT walk through all of Section 1–5 of `context-doc-template.md` before running the resume assessment.
- [ ] Claude notes the 2-page length and invokes the Hard Rule 1 nuance (2 pages may be acceptable for senior / exec / academic / UK-EU CV traditions) before reflexively demanding compression to 1 page.
- [ ] If the resume has no obvious red flags after scan, Claude suggests Phase 3 (job search) as the natural next step without enforcing it.

## Known failure modes

- Claude asks the user to "first upload your resume so we can extract your career facts into a Context Master document" → regression of Lazy SSOT rule (Triage Rule 1 post-0.4.0).
- Claude says "your resume must be 1 page" without checking seniority → regression of 0.4.0 Hard Rule 1 change.
- Claude reads `context-doc-template.md` and/or `sync-rules.md` before the user has expressed any Tier 1 fact change need → unnecessary reference loading, violates Reference Loading Map (0.4.0).
