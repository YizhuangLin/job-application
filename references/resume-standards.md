# Resume Standards Reference

## ATS Compliance Checklist

Run these checks on every resume before delivering:

| Check | Method | Pass condition |
|---|---|---|
| No prohibited characters | `re.search(r'[\u4e00-\u9fff]', xml)` | Returns None |
| No bare `&` in XML | `re.findall(r'&(?!amp;\|lt;\|gt;\|apos;\|quot;\|#)', xml)` | Empty list |
| No tables | `grep -c '<w:tbl>' doc.xml` | 0 |
| No text boxes | `grep -c 'txbxContent' doc.xml` | 0 |
| No images | `ls word/media/` | Empty |
| Paragraph balance | Count `<w:p>` vs `</w:p>` | Equal |
| Page count | Convert to PDF, inspect | 1 page |

---

## Document Structure

### Standard 1-page layout

```
HEADER
  Full Name (large)
  phone · email · city, province · [portfolio URL] · [linkedin]

SUMMARY
  2–3 sentences (compact) describing role + metric + differentiator

WORK EXPERIENCE
  Job Title                                        Date range
  Company Name · Employment Type                   City, Province
  • Achievement bullet with metric
  • Achievement bullet with action + outcome

  [Repeat for each role — compress older roles to 1 bullet]

EDUCATION
  Degree — Field of Study                          Date range
  Institution Name                                 City, Province

SKILLS
  Category 1:   [skill · skill · skill]
  Category 2:   [skill · skill · skill]
  Tools:        [tool · tool · tool]
  Languages:    [language (level) · language (level)]
```

### Compression rules (to fit 1 page)

Apply in this order until content fits:

1. Compress roles older than 8–10 years to 1 bullet each
2. Remove internships / unrelated short-tenure roles (< 3 months)
3. Trim Summary from 3 sentences to 2
4. Trim skill rows — remove items that don't appear in any target JD
5. Remove a whole role if it adds no relevant value

---

## Content Standards

### Summary

- **Length**: 2–3 sentences maximum
- **Sentence 1**: `[Title] with [X]+ years of [domain] experience [key achievement or differentiator].`
- **Sentence 2**: Optional — method, approach, or specific metric
- **Last sentence**: Language / location note if relevant to the market
- **Tone**: Confident, specific, no fluff ("passionate", "dynamic", "results-driven")
- **XML note**: All `&` must be `&amp;` — including "English & French"

### Work experience bullets

- Lead with a strong action verb (Delivered, Grew, Led, Built, Reduced, Increased)
- Include at least one quantified outcome per role when available
- Keep to ~100–120 characters per bullet to avoid awkward line breaks
- Use exact terminology from the target JD where truthful
- Avoid passive voice ("was responsible for")
- 2 bullets per current role minimum; 1 bullet acceptable for older / less relevant roles

### Skills section

Organise into categorical rows. Common categories:

| Row label | What belongs here |
|---|---|
| `Development:` | Languages, frameworks, CMS, tools (if technical role) |
| `SEO & Marketing:` | Channels, platforms, techniques (if marketing role) |
| `Design:` | Design tools, systems (if design role) |
| `Data & Analytics:` | BI tools, query languages, platforms (if data role) |
| `Tools:` | Software, productivity tools, platforms not covered above |
| `Languages:` | Spoken languages with proficiency level |

**Ordering rule**: Put the row most relevant to the target job first.

**Row length**: Each row should fit on 1–2 lines at the resume's font size (typically 9pt Arial = ~80–100 chars per line). If a row overflows, move less-critical items to the `Tools:` row.

---

## Red Flag Identification

Before optimising, scan the resume for signals that commonly cause automatic or instinctive rejection. Surface these to the candidate and agree on a mitigation strategy.

| Red flag | What HR instinctively thinks | Mitigation |
|---|---|---|
| **Employment gap > 6 months** | Let go? Unemployable? Health? | Address briefly in Summary or cover letter (caregiving, retraining, relocation) — 1 sentence, confident tone |
| **3+ jobs in under 4 years** | Job hopper, low commitment | Group contract/freelance roles under one heading; frame as "project-based career"; clarify in cover letter |
| **Title regression** (e.g. Manager → Coordinator) | Performance issue? Fired? | Explain context proactively — pivot, relocation, industry change |
| **Resume ≠ LinkedIn** | Dishonest, disorganised | Sync before applying — exact match on titles, dates, companies |
| **Overqualified** | Will leave as soon as something better comes along | Tailor Summary to show genuine fit; address "why this level" in cover letter |
| **No metrics anywhere** | Hasn't owned outcomes; unclear impact | Quantify at least one achievement per role — even rough numbers help |
| **Skill list of 40+ items** | Inflated; no real depth | Trim to 15–20 most relevant; use rows to show hierarchy |
| **Resume > 1 page** | Can't prioritise or communicate concisely | Compress; remove oldest / least relevant entries |
| **Outdated skills as headline** | Hasn't kept up with field | Move older/less-relevant skills to end of row or Tools row |
| **"References available upon request"** | Wastes space; assumed | Remove entirely |

**How to mitigate without fabricating:**
- Gaps → brief, factual explanation in cover material
- Job hopping → reframe as contract/project experience
- Overqualification → adjust Summary title downward only if truthful
- No metrics → coach the candidate to recall approximate numbers (percentage, volume, time saved)

---

### What not to include

- Objectives that restate the job posting back at the employer
- References / "references available upon request"
- Photos (GDPR concerns; ATS typically cannot read them)
- Reasons for leaving previous roles
- Salary expectations
- Unverifiable certifications or vague "familiar with" claims

---

## Common XML Character Escaping

In `.docx` XML, always use these encodings:

| Character | Correct XML | Common mistake |
|---|---|---|
| `&` | `&amp;` | Bare `&` — causes validation failure |
| Em dash `—` | `\u2014` | Double hyphen `--` |
| En dash `–` (dates) | `\u2013` | Single hyphen `-` |
| Bullet `•` | `\u2022` | Asterisk or hyphen |
| Middle dot `·` (skill separator) | `\u00b7` | Full stop or comma |
| × (multiplier) | `\u00d7` | Letter `x` |
| → (arrow) | `\u2192` | `->` |
