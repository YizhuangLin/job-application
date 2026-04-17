# Scenario: Tracker defaults to flat markdown, not Notion

**Entry phase:** Phase 8

**What this guards:** The 0.5.0 default-backend change. A regression would be Claude asking "do you want to track in Notion?" or calling `search_mcp_registry` / `suggest_connectors` for Notion or Google Sheets when the candidate says "log this application." The default must be: write directly to `{{workspace}}/applications.md` with no picker and no connector prompt.

---

## User message

> I just submitted my application to Stripe for the Senior Product Manager role. Can you log it? This is my first time using the skill.

---

## Expected behaviour

- [ ] Claude routes to **Phase 8 — Application Tracking** and loads `references/post-application.md` Part E (only the top section, not E.1 or E.2).
- [ ] Claude creates or appends to **`{{workspace}}/applications.md`** directly with the Edit (or Write if the file doesn't exist) tool — no external tool prompt, no connector setup step.
- [ ] If `applications.md` does not yet exist, Claude creates it with the minimum-viable table header (`# | Company | Role | Applied | Stage | Match | Notes`) or the full Part E field set — either is acceptable for a first write.
- [ ] Claude fills at minimum: Company (Stripe), Role (Senior Product Manager), Apply Date (today in ISO format), Stage (Applied). Match Level may be asked if not provided.
- [ ] Claude may mention in **one line** that Notion / Sheets adapters exist if the candidate ever wants to upgrade — but does not make this the primary prompt and does not ask the candidate to choose upfront.

## Known failure modes

- Claude's first move is to call `search_mcp_registry` or `suggest_connectors` for Notion / Google Sheets / Airtable → regression of the 0.5.0 default-backend decision. The default is flat markdown, not "pick a database."
- Claude asks "where would you like to track this — Notion, Google Sheets, Airtable, or a markdown file?" → regression. The default is markdown; there is no picker.
- Claude reads `post-application.md` Part E.1 (Notion adapter) or Part E.2 (Sheets adapter) on the default path → regression of the Reference Loading Map. Those sub-sections only load when the candidate explicitly asks for that adapter.
- Claude refuses to log because no Notion MCP is connected → regression. Markdown is the default and does not depend on any MCP.
- Claude re-creates `applications.md` from scratch on every new application instead of appending → regression; the file is an append-only log.
