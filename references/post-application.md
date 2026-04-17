# Post-Application: Interview Prep, Salary Negotiation & Referral Path

---

## Part A — Interview Preparation (triggered on invitation received)

The moment a candidate receives an interview invitation, do the following before anything else.

### Immediate actions (within 24 hours of invitation)

1. **Confirm the format** — phone screen / video / in-person / panel / technical test? Each requires different preparation.
2. **Identify the interviewer(s)** — look them up on LinkedIn. Note their role, background, and any recent posts or articles. People like being asked about their own work.
3. **Re-read the JD** — with fresh eyes, after having submitted. What does the company consider the hardest part of this role? That's likely what they'll probe.
4. **Revisit Phase 4 company research** — update with anything new since you applied. Know one recent piece of news you can reference naturally.

### Preparation framework: STAR

For behavioural questions ("Tell me about a time when..."), structure answers using:

- **S**ituation — brief context (1–2 sentences)
- **T**ask — what was your specific responsibility
- **A**ction — what you did and why (this is the substance)
- **R**esult — quantified outcome, what changed

Prepare 5–6 STAR stories covering: a success with metrics, a failure and what you learned, a conflict resolved, a project you led, a decision made with incomplete information, a time you worked autonomously.

Most behavioural questions are variations of these 6 archetypes.

### Questions to prepare for every role

- "Walk me through your resume / background" — this is an opening for your best narrative, not a chronology recitation
- "Why this company specifically?" — use Phase 4 research; be specific
- "Why are you leaving / why did you leave [current/last role]?" — always forward-facing, never negative about the past employer
- "What's your biggest weakness?" — real, minor relative to the role, with evidence of managing it
- "Where do you see yourself in 3–5 years?" — align to the role's growth path at this company

### Questions to ask the interviewer

These signal seriousness and help the candidate evaluate the role:

- "What does success look like in the first 90 days?"
- "What's the biggest challenge the person in this role will face in the first 6 months?"
- "How does this team define and measure [core function of role]?"
- "What made the previous person in this role successful / what happened to them?" *(only appropriate in some contexts)*
- "What do you enjoy most about working here?" *(good for culture read)*

Never ask about salary, vacation, or benefits in a first interview unless the interviewer raises it.

---

## Part B — Salary Negotiation

### When to raise the topic

- If the application form asks for salary expectations → give a range, not a number; research market rate first
- First interview → deflect if possible: "I'm open to discussing compensation once we've both confirmed this is a good fit"
- Offer stage → this is the right time to negotiate

### Research before negotiating

Sources for market rate:
- Glassdoor salary data for the specific title and city
- LinkedIn Salary Insights
- Indeed Salary Explorer
- Industry-specific surveys (Robert Half, Hays, local tech/marketing associations)
- Ask people in your network who hold similar roles

### Anchoring principles

- **Let them make the first offer** if possible — it sets the anchor
- **Counter with a range, not a number** — put your target in the lower third of your range (e.g. target $75K → counter with $73K–$80K)
- **Justify with market data**, not personal need ("Based on comparable roles in Ottawa, the range is...")
- **Negotiate the full package**, not just base salary — vacation days, remote flexibility, signing bonus, professional development budget, title

### Negotiation language

> "Thank you for the offer — I'm genuinely excited about this role. Based on my research into comparable positions and my [specific experience/skill], I was hoping we could discuss a figure closer to [X]. Is there flexibility there?"

> "I understand if base salary is fixed. Would there be room to discuss [signing bonus / extra vacation / remote flexibility] instead?"

### When to accept without negotiating

- The offer is at or above your researched market rate
- The role offers significant non-salary value (equity, title, learning opportunity, flexibility)
- The employer has signalled the budget is firm and the offer is final

Never decline an offer without negotiating at least once — the worst they can say is no.

---

## Part C — Referral & Network Path

### Why this matters

Internal referrals typically convert to interviews at roughly **3–5× the rate** of cold applications (the often-quoted "5–10×" is closer to a best-case figure; actual averages across industries are lower). A referral doesn't guarantee the job — but it substantially raises the odds the resume gets read by a human rather than skimmed by an overloaded recruiter.

### Check before cold-applying

Before submitting any cold application to a High Match company:

1. Search your LinkedIn connections for people at that company
2. Search your broader network (former colleagues, classmates, industry contacts) for anyone connected to that company
3. If you find a connection — reach out before applying

### Referral outreach message

Keep it short and make it easy for them to say yes:

```
Hi [Name],

I noticed [Company] is hiring for [Role] and I'm genuinely interested — it aligns well with 
my background in [relevant area].

Would you be comfortable passing along my resume to the hiring team, or letting me know if 
it's a good fit from your perspective? No pressure at all if it's not the right time.

[Name]
```

Do not ask them to "put in a good word" — that's pressure. Ask them to pass along the resume or give an honest read.

### Building the referral network proactively

If the candidate has no connections at target companies:

- Engage with company employees' LinkedIn posts (genuine comments, not "Great post!")
- Attend industry events or meetups where company employees are present
- Reach out to recent alumni from the candidate's school/college who work at target companies (alumni connections have a higher response rate than cold connections)

### Referral tracking

Add a column to the application tracker: **Referral contact** — name and relationship. This helps follow up appropriately if the referral reaches out or if an interview is arranged.

---

## Part D — Active Follow-up (Phase 7)

### Proactive follow-up

If no response 5–7 business days after submission, send exactly one follow-up. Template:

```
Subject: [Job Title] Application — [Candidate Name]

Hi [Name / "the hiring team"],

I applied for the [Job Title] role on [date] and wanted to confirm my application came through. I'm very interested in [specific thing about the company from Phase 4 research] and believe my [specific skill / achievement] would be a strong fit.

Happy to share more or jump on a call.

[Name]
[Phone] | [Email]
```

Keep it short. One follow-up is professional; two or more reads as pressure. This is Hard Rule 7 — do not send a second follow-up regardless of response.

### Reactive follow-up (company reaches out asking for more detail)

- 3–5 sentences maximum
- Lead with concrete evidence: specific URLs, named projects, quantified outcomes
- Do not send a second cover letter
- End with a clear next step

### Platform nuance

- **Email** — direct to a human inbox; use the template above as-is
- **LinkedIn InMail** — shorter (under 60 words); skip the subject line
- **Company ATS / greenhouse reply** — only if there's a contact email in the rejection/auto-reply; otherwise do not fabricate an address

---

## Part E — Application Tracker (Phase 8)

### Default backend: flat markdown at `{{workspace}}/applications.md`

**This is the zero-setup path.** Claude creates the file on first submission and maintains it directly with the Edit tool. No connector, no account, no external dependency.

**Do not prompt the candidate** to connect Notion, Google Sheets, or Airtable. Do not ask "where would you like to track this?" — just write to `applications.md`. Upgrade paths (Part E.1 / E.2) are only routed to if the candidate explicitly asks.

**Minimum-viable row structure** (use this if the candidate hasn't expressed preferences):

```markdown
| # | Company | Role | Applied | Stage | Match | Notes |
|---|---|---|---|---|---|---|
| APP-001 | ... | ... | 2026-04-15 | Applied | High | referral: Jane Doe |
```

For a richer tracker (recommended once volume passes ~10 rows), use the full field set below.

### Field definitions (tool-agnostic)

These are the fields every tracker needs. They translate directly to markdown columns, Notion database properties, or Google Sheets headers.

| Field | Values / format |
|---|---|
| Position | Job title |
| Company | Company name |
| Job Category | Technical / Marketing / Mixed / (other) |
| Apply Date | ISO date (YYYY-MM-DD) |
| Platform | Indeed / LinkedIn / Company website / Email / Referral |
| JD Link | URL |
| Resume File | Filename used (follows `APP[NNN]_[Company]_[Role]_[Date].docx` convention) |
| Stage | Applied → In Conversation → Interview → Offer → Closed |
| Outcome | Pending / Rejected / Withdrawn / Offer Accepted |
| Match Level | High / Medium / Low |
| Location | City + work type (on-site / hybrid / remote) |
| Posting Date | When the JD was originally posted |
| Follow-up Date | Scheduled follow-up (Apply Date + 5–7 business days) |
| Salary Range | Offered or posted range |
| Referral Contact | Name + relationship, if applicable |
| Notes | Red flags addressed, research notes, interview feedback |

**Stage definitions:**

- **Applied** — submitted, waiting for first response
- **In Conversation** — HR screen scheduled or in progress
- **Interview** — hiring manager / panel interview confirmed or completed
- **Offer** — offer received, evaluating or negotiating
- **Closed** — role filled, rejected, withdrawn, or offer accepted

Update Stage and Outcome immediately after each action. A stale tracker is useless for Phase 9 diagnostics — "applied 3 weeks ago, no stage update" is indistinguishable from "got rejected silently and forgot to log it."

### Part E.1 — Notion adapter (opt-in)

Only route here if the candidate says "I want to track in Notion" / "connect my Notion" / equivalent.

**Setup checklist:**
1. Verify a Notion MCP connector is available in the current session. If not, tell the candidate to install one and return when ready — do not attempt to work around it.
2. Ask the candidate for a target database (existing or to-be-created). If creating: use the field definitions above, with Stage and Match Level as Select properties and dates as Date properties.
3. Migrate any existing rows from `applications.md` to the Notion database. Do not delete `applications.md` — keep it as a local mirror in case the Notion sync fails.
4. After each new application, write to both: Notion first, then append to `applications.md`. On conflict, Notion wins and the markdown file is regenerated from Notion on the next sync.

**When Notion is a bad fit:** infrequent job-searching (<5 applications / month), no existing Notion habit, or the candidate is asking "what tool should I use?" (that's the default-markdown signal, not the pick-a-database signal).

### Part E.2 — Google Sheets adapter (opt-in)

Only route here if the candidate says "I want to track in a spreadsheet" / "connect my Google Sheet" / equivalent.

**Setup checklist:**
1. Verify a Google Sheets MCP connector is available. If not, tell the candidate and stop.
2. Ask for the target sheet URL, or offer to create a new sheet titled `Job_Search_Tracker_{{YYYY}}`. First row is the full field header (Position, Company, ..., Notes).
3. After each new application, append to the sheet **and** mirror to `applications.md` (same dual-write pattern as E.1).

**When Sheets is a good fit:** the candidate wants to share the tracker with a partner, coach, or recruiter; or wants formula-based filtering (e.g. `=QUERY` for "all Interview stage + applied >14 days ago"). Otherwise default markdown is enough.

### Why flat markdown is the default

Three reasons, in priority order:
1. **Zero friction for new users.** Cloning the skill should not require signing up for anything. OSS default must work out of the box.
2. **Portable and greppable.** A markdown file survives tool churn, lives next to the rest of the workspace (Context Master, company dossiers, resume files), and is diffable in version control.
3. **Good enough for realistic volumes.** Individual job-searchers rarely exceed 100 applications per cycle. At that scale, Notion's rollup / kanban power isn't necessary — basic table filtering and grep cover 95% of diagnostic queries in Phase 9.
