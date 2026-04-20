# Scenario: Phase 0 routes a low-capacity user to light tier

**Entry phase:** Phase 0

**What this guards:** The 0.6.0 Phase 0 Reality Check. A user who shows up with low time + low urgency + modest clarity should be routed to **light** tier and spared the full 11-phase apparatus (SSOT, dossier, full tracker, cover letter per role). Regression would be Claude defaulting to standard tier and prompting for a Tier 1 SSOT + company dossier + 16-column tracker on what is clearly a casual search.

---

## User message

> I'm a mid-career marketer thinking about making a change eventually. I've got maybe 2 hours a week to look around, not in a rush, just want to see what's out there. Can you help me find a few roles to apply to?

---

## Expected behaviour

- [ ] Claude runs **Phase 0** — asks the 3 capacity/clarity/urgency questions OR declares it has enough info from the message (2h/week, casual, modest clarity) to route directly.
- [ ] Claude names the strictness tier explicitly to the user: *"Running in light mode…"* or equivalent.
- [ ] Claude routes to **Phase 3** (job search & timing) next, not Phase 1 (candidate intake).
- [ ] Claude does **not** copy `context-doc-template.md` into the workspace. No `{{Name}}_Context_Master.md` is created on the first turn.
- [ ] Claude does **not** open a company dossier for any posting surfaced.
- [ ] If Claude proposes a tracker, it's the minimal form (Company · Role · Applied date · Stage · Notes) — not the full 16-column Part E table.
- [ ] Claude mentions once that the user can upshift to standard tier later if they get serious.

## Known failure modes

- Claude runs full Phase 1 intake (asks for resume upload, walks through all sections of context-doc-template, creates `Context_Master.md`) → regression of Lazy SSOT + Phase 0. The user explicitly signalled casual; full intake is wrong tier.
- Claude creates a company dossier for the first High Match surfaced → regression. Light tier skips dossiers entirely.
- Claude never asks the 3 questions and never declares a tier → regression. Even if it behaves correctly, an undeclared tier means the user can't correct it.
- Claude pushes the user into Phase 8 tracker setup with all 16 Part E fields → regression. Minimal tracker only for light tier.
- Claude refuses to proceed without a complete SSOT → hard regression of Lazy SSOT; the whole 0.4.0 + 0.6.0 line is to make the skill usable at every entry point.
