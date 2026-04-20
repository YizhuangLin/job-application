# Landing page draft — job-application v0.6.0

> **File purpose:** Copy-ready content + layout notes for the landing page at `cestduleon.dev/job-application/`. Philosophy-driven, single-page narrative (Plan A).
>
> **How to read this file:**
> - `// LAYOUT:` lines are visual / structural guidance for the React implementation. Remove at render time.
> - Everything else is finalized copy. Edit for voice, but the structure is deliberate.
> - Emoji use is intentional and minimal — three spots only (hero anchor, triage icons in §3, founder note). Strip them if the brand prefers clean.

---

## LAYOUT NOTES (top-level)

```
┌─────────────────────────────────────────┐
│ NAV          (logo · GitHub · Install)  │
├─────────────────────────────────────────┤
│                                         │
│            HERO                         │
│   (1 tagline · 2-line sub · 2 CTAs)     │
│                                         │
├─────────────────────────────────────────┤
│ §1  The problem                         │
│     (3 failure modes, one sentence each)│
├─────────────────────────────────────────┤
│ §2  Three design choices                │
│     (3 cards, vertical stack on mobile, │
│     3-up on desktop — or single-column  │
│     if you want depth > scan)           │
├─────────────────────────────────────────┤
│ §3  What it feels like                  │
│     (3 scenario vignettes, 1 per user   │
│     entry point)                        │
├─────────────────────────────────────────┤
│ §4  For developers                      │
│     (collapsible / subdued — links out  │
│     to README for depth)                │
├─────────────────────────────────────────┤
│ §5  Install                             │
│     (tabs OK here: .skill vs git clone) │
├─────────────────────────────────────────┤
│ §6  Trigger phrases to try              │
├─────────────────────────────────────────┤
│ Founder's note                          │
├─────────────────────────────────────────┤
│ Footer                                  │
└─────────────────────────────────────────┘
```

**Visual tone guidance:** honest > polished. This is an OSS skill built by someone actively job-hunting, not a SaaS product. Avoid gradient hero art, testimonial walls, and "10x your job search" hype. Typographic hierarchy > illustration. Monospace for trigger phrases and code.

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NAV
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
job-application                 Docs  GitHub  [ Install .skill ]
```

- Left: skill name, small version badge `v0.6.0`
- Right: three links — Docs (→ GitHub README), GitHub (→ repo), **[ Install .skill ]** as primary CTA (→ release download)

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HERO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// LAYOUT: centered, generous top padding. Tagline in display-size serif or heavy sans.
// LAYOUT: no hero image. The text is the hero.

## Job search, calibrated to your life.

A full-cycle Claude Cowork skill that adjusts its flow to your time, urgency, and headspace — instead of pushing every user through the same 11-phase pipeline.

> *Built for people who want a thoughtful partner, not a submission factory.*

**[ Install .skill ]**   **[ View on GitHub → ]**

// LAYOUT: small tertiary line under CTAs:
`Works with Claude Cowork · MIT licensed · v0.6.0 · 2026-04-17`

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# §1  Most job-search tools treat you like a pipeline.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// LAYOUT: full-width section. Heading left-aligned, body in a narrower text column (max ~680px) for readability.
// LAYOUT: the three failure modes below can be three small cards, or three indented bullets with bold leaders. Prefer cards on desktop.

They assume everyone is looking full-time. They optimize for application volume. They stop at "submitted" and leave you alone with the rejection email.

This skill is built on three different defaults:

**One size doesn't fit.**
Someone casually browsing ("thinking about switching eventually, 2 hours a week") and someone in a 4-week runway career pivot need different levels of structure. The skill asks three questions up front and calibrates the rest of the flow to your actual capacity.

**Volume is the wrong lever.**
Applying to 40 jobs a week doesn't beat applying to 8 with a referral and a tailored summary. The skill discourages spray-and-pray — checks your network before cold-applying, respects the 1–2 week posting window where most commercial roles concentrate their actual hiring attention, and caps follow-ups at one.

**Rejection and burnout are part of the process, not bugs.**
Most job-search tools go silent when you get rejected or stop responding when you stop applying. This skill has a 24-hour rejection protocol, a burnout check that fires at 15+ applications per week, a pre-interview nervous-system routine, and an offer-fear reality module. All documented, all opt-in.

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# §2  Three design choices that make it different.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// LAYOUT: this is the spine of the page. Three subsections, each with:
//   - a short headline
//   - a 2-3 sentence body
//   - one concrete contrast / example in a highlighted block
//   - a small "learn more" anchor pointing to the relevant reference file on GitHub
// LAYOUT: vertical stack; don't try to fit them into a 3-up grid — depth matters more than scannability here.

---

## 2A. Capacity-matched strictness.

*Phase 0 · Reality Check*

Before anything else, the skill asks three questions: how much time per week, how clear are you on what you want, how urgent. Your answers map you to one of three tiers:

| Tier | When | What changes |
|---|---|---|
| **light** | ≤ 2 h/week · clarity ≤ 2 · casual | No master profile doc. No per-company dossier. Minimal tracker. One resume, customize only the summary per role. |
| **standard** *(default)* | 3–10 h/week · active search | Full 11-phase flow. Profile built lazily as facts surface. Dossiers for high-match companies only. |
| **deep** | 10+ h/week · career pivot or urgent | Full flow + proactive profile setup + dossier for every high / medium match + tighter change-log discipline. |

> **Why this matters:** the skill is capable of running an 11-phase execution pipeline with document sync, referral tracking, and per-company research files. That's overkill for someone with two hours a week. Phase 0 prevents the skill from pushing structural overhead at users who don't need it.
>
> You can switch tiers between phases at any time. Tier is a soft setting, not a quality gate.

*See: `SKILL.md` → Phase 0 · Reality Check*

---

## 2B. Timing and referrals over volume.

*The working thesis: applying earlier to fewer, better-matched roles beats applying to more.*

For most commercial roles, application volume concentrates in the first 1–2 weeks after a posting goes live. A referral typically converts to an interview at roughly 3–5× the rate of a cold application, varying by industry and connection strength.

The skill operationalizes this without making volume claims it can't back up:

- **Timing filter** — posting age is checked in every job search. 2+ week old roles get flagged, not hidden. Executive, government, and academic roles follow their own timelines and are treated separately.
- **Referral check** — before every cold application to a high-match company, the skill prompts you to check your network. If there's a connection, it generates a referral outreach script instead of pushing you into cold-apply mode.
- **One follow-up, ever** — 5 to 7 business days after submission, one message. Never a second. Not "following up on my following-up."
- **No fabrication** — gaps in your background get noted honestly and addressed in cover material. The skill will not invent skills you don't have to pad a keyword match.

> **Why this matters:** most AI job tools are optimized for output volume because it's the easy metric. This one is optimized for signal — fewer applications, higher response rate per application.

*See: `references/referral-strategy.md`, `references/jd-analysis.md`*

---

## 2C. Emotional pacing that actually exists.

*`references/coping.md` — added in v0.6.0*

Most job-search tools pretend the emotional layer doesn't exist. They wrap execution features in a thin "stay positive!" layer and leave you to handle rejection, burnout, interview anxiety, and offer fear alone.

This skill documents the parts everyone knows are real:

**24-hour rejection protocol.** After a high-match rejection, the skill pauses new applications for that company's segment for 24 hours. Short reflection loop. No "let's try again" energy while you're still processing.

**Burnout early warning.** If you cross 15 applications in 7 days, or mention poor sleep or low mood, the skill surfaces the burnout signal table before prescribing more volume. Sometimes the right answer is a 48-hour pause, not another 10 submissions.

**Pre-interview stabilization.** A 30-minute runbook for the window before an interview — breathing, context review, final question prep. Not a pep talk. A nervous-system regulation sequence.

**Offer-fear reality data.** When a polite counteroffer triggers the "they'll rescind" spiral, the skill surfaces the actual data: rescission rate on polite counters is under 5%, and standard response windows are 3–5 business days.

**Weekly and monthly rhythm.** How to pace a multi-week search without the "apply every day forever" guilt trap.

> **Scope:** this is pragmatic pacing, not therapy. The skill is explicit about pointing users toward a professional if symptoms persist. What it does is remove the strange silence most job tools maintain about the parts of job search that actually wear people down.

*See: `references/coping.md` · hooked into Phases 8 / 9 / 10 / 11*

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# §3  What it feels like in practice.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// LAYOUT: three vignettes. Each is a small "card" with a context line, a sample trigger, and what the skill does in response.
// LAYOUT: use a mono-font block for the trigger line to distinguish user input from narration.

Three quick scenarios to show the shape.

---

### 🧭 The casual switcher

**Context:** Mid-career marketer, 2 hours a week, might switch eventually, not urgent.

```
"I'm thinking about looking for a new job, not in a rush."
```

→ Phase 0 runs the 3 questions. Routes you to **light tier**. No master profile doc. No dossiers. Skill asks what kinds of roles look interesting, runs a light job search, tracks applications in a 5-column markdown file. You stay in light tier until you tell it otherwise.

What you *don't* get: a 45-minute onboarding interview to build a profile document you weren't going to maintain.

---

### 🎯 The mid-search applicant with an interview next week

**Context:** Already applied to 20 roles. Got an invite. Interview in 48 hours.

```
"I have an interview at Stripe on Thursday — help me prep."
```

→ Phase 10 runs directly. No detour through "let's build your profile first." The skill back-fills the facts it needs as it generates your STAR stories, question bank, and thank-you email draft. It also opens `coping.md` Part 3 — the 30-minute pre-interview runbook — because the interview is ≤ 48 hours out.

What you *don't* get: "Before I help with the interview, let's set up your SSOT."

---

### 😮‍💨 The person in a rough patch

**Context:** 18 applications last week, 2 callbacks, just got a rejection from a high-match role.

```
"I just got rejected from the one I really wanted. Should I apply to more today?"
```

→ The skill doesn't jump to "let's find 10 more." It runs `coping.md` Part 1 (the 24-hour rejection protocol), surfaces the Phase 9 response-rate diagnostic (is the issue targeting, resume, or volume?), and checks the burnout signals — 18 apps/wk is in the warning band, and the emotional context is worth naming.

What you *don't* get: "Here are 15 new roles, applying now!"

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# §4  For developers.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// LAYOUT: smaller section. Can be collapsed by default on desktop ("Read more ↓") — optional.
// LAYOUT: or render as a subdued horizontal band with 4 short columns.

If you're here to fork, adapt, or contribute:

- **11 phases + 1 pre-flight**, defined in `SKILL.md` with an explicit Reference Loading Map so each phase pulls only the references it needs.
- **13 reference files** covering resume standards, JD analysis, company research, cover letters, referrals, build scripts, interview prep, salary negotiation, post-application tracking, context-doc template, sync rules, company dossier template, and coping.
- **Eval harness** — 5 scenario-based regression tests (`evals/01` through `evals/05`) that a human reviewer can pass/fail in under 2 minutes each. Guards against known regressions like forced Phase 1 setup, keyword-density myth, and wrong tier defaulting.
- **SemVer + Keep a Changelog** — every release documents what changed and why. See `CHANGELOG.md`.
- **MIT licensed.** Fork, adapt, share improvements.

Written with the Cowork skill conventions — `SKILL.md` at the root, `references/` for on-demand loading, `evals/` for regression coverage, `CHANGELOG.md` for history. Works as a template for other Cowork skills.

**→ [Read the full README on GitHub](https://github.com/YizhuangLin/job-application)**

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# §5  Install.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// LAYOUT: this IS where tabs earn their keep. Two mutually exclusive paths, symmetric content.
// LAYOUT: Tab A default (easier path), Tab B advanced.

### Two ways to install

**Tab A — `.skill` file (recommended for most users)**

1. Download [`job-application-skill-v0.6.0.skill`](https://github.com/YizhuangLin/job-application/releases/latest)
2. Open Claude Cowork (desktop app)
3. Drag the `.skill` file into the Cowork window, or use Settings → Skills → Install from file
4. Start a new conversation. Trigger with any job-search phrase (see §6).

No terminal, no git, no config.

---

**Tab B — git clone (for contributors)**

```bash
git clone https://github.com/YizhuangLin/job-application.git ~/.claude/skills/job-application
```

The directory should contain `SKILL.md` and the `references/` subfolder. Restart Cowork.

Use this path if you plan to edit the skill, run the eval suite, or contribute changes upstream.

---

### Requirements

- **Claude Cowork** (desktop app) — available at [claude.ai](https://claude.ai)
- The **docx skill** installed alongside this one (used by Phase 5 for resume generation)
- A `.docx` master resume to work from

**No external tracker required.** The default application tracker is a flat markdown file in your workspace, maintained by Claude. Notion, Google Sheets, and Airtable are opt-in upgrades — documented in `references/post-application.md` — only used if you explicitly ask.

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# §6  Try a phrase.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// LAYOUT: a grid of 6-8 mono-font cards. Each is a trigger phrase + one-line hint of what happens.
// LAYOUT: click-to-copy would be nice here if cheap.

After installing, start a Cowork conversation and try any of these:

```
"I want to look for jobs."
```
*→ Phase 0 · Reality check. Assigns your strictness tier.*

```
"Review my resume for ATS and red flags."
```
*→ Phase 2 · 1-page compression, compliance check, honest red-flag callout.*

```
"Find me jobs in [city] for [role]."
```
*→ Phase 3 · Live job search with timing filter.*

```
"Help me apply to this role: [URL or JD]"
```
*→ Phases 4–7 · Company research, referral check, tailored resume, cover material, submission guide.*

```
"I'm not getting callbacks — what's wrong?"
```
*→ Phase 9 · Response-rate diagnostic + burnout check.*

```
"Prepare me for my interview at [Company] tomorrow."
```
*→ Phase 10 · STAR prep, question bank, thank-you email, pre-interview stabilization.*

```
"I just got rejected and I'm spiraling."
```
*→ `coping.md` · 24-hour rejection protocol. No "let's try more" until the protocol runs.*

```
"I got an offer — help me evaluate and negotiate."
```
*→ Phase 11 · Package breakdown, counter scripts, anchoring, offer-fear reality check.*

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FOUNDER'S NOTE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// LAYOUT: small, honest, no headshot needed. Left-aligned, italic or serif-bodied.

I built this while actively job-searching myself.

Every phase came out of a specific moment where the existing tools failed me — the rejection that tanked my week and left me spiraling for two days, the interview I walked into under-prepared because I was burnt out, the counteroffer I was too scared to send. The skill codifies what I wish I'd had, and what I built for myself along the way.

The v0.6.0 release (Phase 0 tiers + `coping.md`) came directly from catching myself getting pushed through a heavy-structure flow when I had three hours of capacity and no urgency — and realizing a good skill should catch that before the user has to.

If you use it and something misses, [open an issue](https://github.com/YizhuangLin/job-application/issues). I maintain this actively.

— *Leon*

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FOOTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
job-application  v0.6.0  ·  MIT  ·  github.com/YizhuangLin/job-application
                                     cestduleon.dev
```

Three columns (or a single centered line on mobile):
- Left: skill + version + license
- Middle: GitHub / CHANGELOG / Issues
- Right: author site

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# END OF DRAFT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Implementation checklist for the React port

- [ ] Hero: no image, typography-forward
- [ ] §2 spine is vertical stack, not 3-up grid (depth > scannability)
- [ ] §3 scenario cards use monospace for trigger phrases
- [ ] §5 tabs for install paths only — do not tab anything else
- [ ] §6 phrase cards support click-to-copy if cheap
- [ ] Founder's note keeps human voice — resist rewriting into marketing tone
- [ ] Footer links: GitHub repo, CHANGELOG.md, Issues, cestduleon.dev
- [ ] Responsive: all sections collapse cleanly to single column on mobile
- [ ] Meta / OG tags: title = "job-application — a Claude Cowork skill calibrated to your job search", description = hero sub

## Content diffs vs. old landing page

If the previous landing mirrored the README structure (install-first, phase table, file tree), the main shifts are:

1. **Philosophy moved to the top.** §1 + §2 are the spine; install is §5.
2. **Phase table removed.** Replaced by §3 scenarios, which communicate the same thing without requiring readers to parse 11 rows.
3. **Emotional layer surfaced.** `coping.md` gets equal billing with capacity-matched and referral-first — in v0.5.0 it was a subsection of the README and largely invisible.
4. **Founder's note added.** The current landing page doesn't have a voice; the skill is built by a person in the situation it's solving for, and that's a trust signal worth making explicit.
