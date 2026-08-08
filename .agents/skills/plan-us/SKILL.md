---
name: plan-us
description: Use when the user wants a plan (NOT implementation) for a user story or feature — "create the plan", "plan the US/HU", "implementation plan", "crea el plan", "planea la US/HU". Drives plan mode; reads project memory, grounds the plan in the real codebase, and produces the house plan document (story understanding what/why/what-for → full-stack impact analysis database/backend/frontend → schema-level database changes → ordered create/modify plan in dependency order → use cases per acceptance criterion with verification method), asking every ambiguity instead of assuming. Leaves no loose ends: every use case must end functional and testable across all tiers it touches. Ends at an approved plan — never implements. Hands off to the `implement` skill.
argument-hint: [user story file path | ADO work item id | pasted user story text]
model: claude-fable-5
effort: xhigh
---

# Note: MANDATORY - Everything is in English: communication with the user, the plan document, and any code, schema, table/column names and identifiers.

# Plan US — house planning workflow (plan only, no implementation)

Produces an implementation plan for a user story/feature in Evalux, in the house standard format. Communicate and write everything **in English** — the plan document, code, schema, table/column names and identifiers. **This skill NEVER implements** — it stops at an approved plan.

Operate in **plan mode** for the whole run: call `EnterPlanMode` at the start and `ExitPlanMode` to present the finished plan for approval. Plan mode forbids editing files — that is intentional; the only write happens *after* approval (saving the plan document).

## Phase 0 — Intake

1. **Read project memory** (`memory/MEMORY.md` and any relevant linked notes) and the root `CLAUDE.md` (architecture, commands, gotchas, known doc inconsistencies). This is task 1 and it is mandatory — the plan must respect what memory already records (feature status, prod-migration safety, stack decisions, etc.).
2. **Locate the user story.** In priority order:
   - Path/text passed as argument.
   - An ADO work item id → fetch it with the `mcp__ado__wit_get_work_item` tool (title, description, acceptance criteria).
   - `Docs/backlog.md` if the argument is a US id (US-001…US-013) — it holds every story with its acceptance criteria.
   - `.claude/User story implementation plan.md` if it holds the story.
   - Pasted text or a plain feature description in the conversation — if no formal story exists, derive the acceptance criteria from the description and validate them with the user in Phase 3.
   Read it **fully**. Extract the description and **every acceptance criterion** verbatim — they are the backbone of the plan. Cross-reference the applicable business rules in `Docs/business-rules.md` (BR-xxx-nnn) — the plan must cite the rule ids it satisfies.
3. If more than one user story is in scope (e.g. a parent + child), plan them together but keep their criteria and use cases traceable to each story id.

## Phase 1 — Ground the plan in the real codebase

**Greenfield check first:** if the codebase does not exist yet (no `evalux.sln`, no `src/`), the plan MUST begin with a bootstrap stage that creates the entire working skeleton from scratch — git init, solution with the 7 `src/` + 4 `tests/` projects wired with only the allowed references, SharedKernel base types, `Evalux.Api` composition root, ArchUnitNET boundary rules, `docker-compose`, the Next.js frontend, CI gates — following the tech guidelines (`Docs/tech-doc.md` §4–§5, `Docs/code-standards.md`), and it must end **functional** (build clean, arch tests green, API boots, frontend renders). List these scaffold items first in the ordered implementation plan, before any US-specific item.

Before writing anything, investigate so the plan is real, not generic (task 6: do not invent). Enough to answer, not an audit:
- Which assemblies/files are touched (SharedKernel contracts, module `Domain`/`Services`/`Contracts`, EF configurations in the module's `Infrastructure/`, `Evalux.Api` endpoints/policies) — remember module boundaries: cross-module only via `Contracts/` interfaces resolved from DI, never concrete types.
- Existing entity configurations and current schema for anything you'd extend, so DB changes are additive and safe.
- The Next.js frontend surfaces that must change for the story's UI use cases.
- Reuse: existing services/patterns to extend instead of duplicating.

**Full-stack coverage is mandatory:** for every use case, determine explicitly whether it needs **database** work (tables/columns/migrations/seeds), **backend** work (SharedKernel, module Domain/Services/Contracts, Api endpoint + RBAC policy), and **frontend** work (pages, components, API integration per `Docs/UI mockups/`). "No work needed" in a tier is a valid answer only when stated and justified — never implied by omission.

## Phase 2 — Build the plan document

Write the plan in English with **these sections, in this order**:

1. **Story understanding (what, why, and what for)** — task 2. In your own words: what the story must do, why it is being requested, and what it gives the user/business. Tie it back to the acceptance criteria and the business rules (BR ids) it must satisfy.
2. **Full-stack impact analysis** — a three-row verdict table (**Database / Backend / Frontend**): whether the story needs work in each tier and what, in one or two lines per tier. Every tier gets an explicit verdict — "No work needed" is valid only with a one-line justification, never implied by omission. Anything marked "Yes" here must materialize as concrete items in sections 3–4.
3. **Database changes** — task 3. Only if tables must be created or modified. Show it at **schema level**, not just entity names: table name, columns with SQL types, nullability, keys, foreign keys, indexes, and defaults. Weights/ratings/scores are `decimal` with explicit precision (`decimal(18,4)` scores, `decimal(5,2)` weights); dates are `datetimeoffset` (UTC). If **no** DB change is needed, say so explicitly. Respect prod-migration safety from memory (additive first, `IF EXISTS` guards, idempotent seeds, backfill not wipe).
4. **Ordered implementation plan** — task 4. An ordered list of **what gets created** and **what gets modified**, in correct dependency order, each item tagged with its assembly (SharedKernel / Modules.Employees / Modules.Criteria / Modules.Evaluations / Modules.Audit / Api) and, for UI/behavior, the Next.js frontend. Backend-only changes: say so. Placement must follow the binding `.claude/rules/{sharedkernel,modules,api,tests,frontend}.md`.
5. **Use cases** — task 5. Derive the use cases that must be satisfied so that **each acceptance criterion and the story goal are met**. Present a mapping table: `use case → acceptance criterion(s) covered → tiers touched (DB / BE / FE) → verification method (API test / Playwright UI flow / both)`. Every acceptance criterion must be covered by at least one use case, and **every use case must have a verification method** — a use case that cannot be tested at the end of the implementation is a loose end in the plan.
6. **Assumptions and decisions** — any assumption you had to make explicit (kept minimal; real ambiguities go to Phase 3, not here).

**End-to-end completeness check (mandatory before presenting):** walk each use case through its full chain — DB schema → module service → API endpoint + RBAC policy → frontend surface → verification method — and add any missing link to the plan. Typical loose ends to hunt for: an endpoint with no UI that consumes it, a UI calling an endpoint the plan doesn't create, a column without its migration, a validation without its error surface in the UI, a use case with no test path. This check is binding: at the end of the implementation the story must be **functional and testable end to end**, with nothing dangling.

## Phase 3 — Resolve ambiguities (do not invent)

Task 6 is binding: **anything unclear, dual, or ambiguous → ASK the user; never invent or assume.** Collect the open questions and ask them with `AskUserQuestion` (batch related ones). Wait for the answers and fold them into the plan **before** presenting it. If a question blocks a whole section, mark that section as pending on that answer rather than guessing.

## Phase 4 — Present, approve, save (still no implementation)

1. Present the complete plan for approval with `ExitPlanMode`. Task 7 is absolute: **do not write any application code, migration, or config.**
2. On approval, the only allowed write is saving the plan document (Markdown) so the `implement` skill can consume it. Save it to `.claude/implementation plans/US-<id>-implementation-plan.md` (create the `.claude/implementation plans/` folder if missing). Only deviate from that path if the user explicitly asks for another location.
3. Close by telling the user the plan is ready and that they can run **`/implement <plan-path>`** when they want to build it. Stop there — this skill hands off to `implement`; it does not implement.
