---
name: session-retro
description: Run a retrospective at the end of a long or substantive Claude Code session to capture reusable knowledge before it's lost. Use this whenever the user says things like "end of session", "wrap up", "anything we learned", "should we save this somewhere", or asks whether new knowledge from the session should update a skill or be recorded in CLAUDE.md. Also trigger proactively after sessions involving non-obvious debugging, discovering undocumented project conventions, working around tricky environment/tooling quirks, or repeating a multi-step workflow that isn't already documented anywhere. Decides whether each finding belongs in a Skill (reusable, project-independent procedure) vs CLAUDE.md / <module>/CLAUDE.md (project- or module-specific fact, convention, or gotcha), then writes it to the right place.
disable-model-invocation: true
---

# Session Retro

A skill for closing out a Claude Code session by harvesting knowledge gained during it, and routing each piece of knowledge to the right place: a Skill, or a CLAUDE.md file.

## When to run this

- The user explicitly asks for a retro / wrap-up / "what did we learn".
- Proactively suggest it (don't just silently do it) when the session involved:
  - Non-obvious debugging (root cause wasn't where it looked).
  - Discovering an undocumented project convention, naming scheme, or constraint.
  - Working around a tooling/environment quirk (flaky test, env var needed, version pin).
  - A multi-step workflow you'd want to repeat exactly next time.
  - Corrections from the user that changed your approach mid-session.

If none of these occurred, it's fine to say so plainly and skip the rest — don't manufacture findings.

## The core loop

### 1. Extract candidate findings

Scan back through the session (your own actions, errors hit, corrections from the user, final working solution) and list out discrete, concrete findings. Each finding should be a single sentence a future Claude session could act on. Bad: "learned about the auth system." Good: "the `/auth` middleware silently swallows 401s in dev mode unless `DEBUG_AUTH=1` is set."

Show this list to the user before writing anything — let them confirm, edit, drop, or add findings. Don't skip this confirmation step; the user's judgment on what's worth keeping matters more than completeness.

### 2. Classify each finding: Skill vs CLAUDE.md

For each confirmed finding, decide where it goes:

**→ CLAUDE.md or <module>/CLAUDE.md** if it is:
- Specific to this project/repo/module (a fact about *this* codebase, not a general technique).
- A convention, constraint, gotcha, env requirement, or "don't do X here because Y."
- Something you'd want loaded as context next time you touch this project, but isn't a multi-step procedure.

**→ A Skill** if it is:
- A reusable *procedure* — a sequence of steps that would apply across projects, or repeatedly within this one.
- Something with a clear trigger ("whenever asked to do X, do these steps") and enough structure to benefit from progressive disclosure (scripts, references, examples).
- Worth surfacing even when this exact project isn't in context.

Rule of thumb: if it's a fact, it's CLAUDE.md. If it's a *how-to*, it's a Skill. Some findings are both — a CLAUDE.md note pointing at a newly created/updated skill is fine and often the right call.

When unsure, ask the user — don't guess silently and write to the wrong place.

### 3. Write CLAUDE.md updates

- Locate the right file: root `CLAUDE.md` for project-wide facts, `<module>/CLAUDE.md` for module-scoped ones. If a module-level one doesn't exist yet but the finding is clearly module-scoped, create it.
- Keep entries short, dated optionally, and grouped under existing headings if the file has structure already — don't reorganize the whole file just to add one line.
- Read the existing file first (str_replace requires exact match) and append/insert rather than overwrite.
- Avoid duplicating something already documented — search the file for related content before adding.

### 4. Write or update Skills

If a finding warrants a skill, hand off to the **skill-creator** skill (`/mnt/skills/examples/skill-creator/SKILL.md`) for the actual authoring — it has the full create/update/eval workflow. Don't reimplement that here. Specifically:
- New reusable procedure → skill-creator's "Creating a skill" flow.
- Refinement of an existing skill → skill-creator's "Updating an existing skill" flow (preserve name, copy from read-only path before editing, etc).

### 5. Summarize

End with a short summary: what was written to which CLAUDE.md file(s), and which skill(s) were created/updated (or "no skill changes this time"). Don't pad this with a long report — a few lines is enough.

## Notes

- This skill is about *capture*, not about judging whether the session went well. Stay factual.
- Don't invent findings to seem thorough — an empty retro ("nothing new to record") is a valid and good outcome.
- If the user runs this every session as a habit, keep the confirmation step lightweight (a quick list, not a long interview) once they've established the pattern with you.
