# Scenario: Interview prep does not force Phase 1 SSOT setup

**Entry phase:** Phase 10

**What this guards:** Lazy SSOT. A user entering at Phase 10 with an interview in 48 hours must not be dragged through Phase 1 candidate-intake setup before getting interview prep. This was Triage Rule 1 in 0.3.0 ("always confirm SSOT exists before any phase") and was explicitly reversed in 0.4.0.

---

## User message

> I have an interview with Stripe on Thursday for a Senior Product Manager role. It's a 45-min video screen with the hiring manager. Can you help me prep? I've never used this skill before.

---

## Expected behaviour

- [ ] Claude routes to **Phase 10 — Interview Preparation**, reads `references/interview-prep.md` and `references/company-dossier-template.md`.
- [ ] Claude offers to create a dossier file for Stripe at `{{workspace}}/companies/Stripe.md` using the dossier template.
- [ ] Claude helps with Phase 10 immediate actions: confirm logistics, ask what the user knows about the hiring manager, offer to help with 5–6 STAR stories, surface 3 questions to ask.
- [ ] Claude does NOT force the user to first complete Phase 1 (Context Master setup) or walk through `context-doc-template.md` before helping with prep.
- [ ] Claude does NOT insist on reading the user's full resume and mapping every work history section to a Tier 1 SSOT file before prep begins.
- [ ] If Claude needs a Tier 1 fact during prep (e.g. the user's core quantified achievements for STAR stories), Claude asks about just that fact and may mention it can optionally save to a SSOT for future reuse — but does not block prep on it.
- [ ] Claude suggests Phase 11 (offer negotiation groundwork) as optional follow-on, not mandatory.

## Known failure modes

- Claude responds with "Before we prep, let's first set up your Candidate Intake — please share your resume so we can build the Context Master" → regression of Lazy SSOT (Triage Rule 1 post-0.4.0).
- Claude reads all 11 sections of `context-doc-template.md` front-to-back before touching interview prep → violates Reference Loading Map (Phase 10 should load `interview-prep.md` + `company-dossier-template.md`, not `context-doc-template.md`).
- Claude refuses to help until the user has completed Phase 1 → regression of "Do not force-read earlier phases" (Triage Rule 2).
