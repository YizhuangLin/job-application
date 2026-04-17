# Scenario: Keyword advice is "natural placement," not density stuffing

**Entry phase:** Phase 5

**What this guards:** Resurrection of the keyword-density myth removed in 0.4.0. A regression would be Claude telling the user to repeat the same JD keyword across Summary + every work bullet + Skills row because "ATSs score on density."

---

## User message

> Here's the JD for a Senior Growth Marketer role at a B2B SaaS company — it mentions "lifecycle marketing" 4 times, "Hubspot" 3 times, and "SQL" twice. My current resume has "Hubspot" in the Skills row only and mentions "lifecycle" once in a bullet. SQL isn't anywhere. Can you help me optimise this for the JD?

(Assume the user has attached their resume showing they do use Hubspot and have run lifecycle campaigns, but they have never used SQL in a work context.)

---

## Expected behaviour

- [ ] Claude recommends surfacing **Hubspot** in the Summary or at least one work bullet (currently only in Skills row — Phase 5b rule: Skills-only mentions get skimmed).
- [ ] Claude recommends naming the existing **lifecycle campaign** bullet more explicitly with "lifecycle marketing" terminology to match the JD's exact phrasing.
- [ ] Claude does NOT recommend forcing the same keyword ("Hubspot") into 3+ sections for density. The 0.4.0 guidance explicitly calls this stuffing.
- [ ] Claude flags **SQL as a gap** — the user has not used it in a work context — and does NOT add SQL to the resume. Per Hard Rule 4 (no fabricated skills), the gap should be noted and potentially addressed in cover material.
- [ ] Claude may cite the underlying reasoning: modern ATSs (Workday, Greenhouse, Lever, Ashby) parse into structured fields; the real screen is a human reading the resume; density stuffing hurts more than it helps.

## Known failure modes

- Claude says "Hubspot should appear in Summary + 1 bullet + Skills row + optionally Education" in a density-distribution frame → regression of 0.4.0 Phase 5b rewrite.
- Claude adds SQL to the Skills row "even just as a keyword" to pass the JD filter → regression of Hard Rule 4.
- Claude cites the removed Step 5b "keyword frequency (not just presence)" section language → regression; that phrasing was fully replaced with "placement (natural, not stuffed)" in 0.4.0.
- Claude references the old "keywords in 3 sections score significantly higher" claim → regression.
