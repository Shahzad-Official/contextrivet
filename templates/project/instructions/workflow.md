# Task workflow and durable knowledge

## Before and during a task

- Check the onboarding gate in the canonical instructions. Read project context
  and architecture, then search the knowledge index for the affected feature.
- Verify notes against current source and tests. Source describes observed
  implementation; explicit user requirements describe intended behavior. Resolve
  material conflicts instead of silently treating either as universally correct.
- Trace only the paths needed for the task. Use the existing architecture and
  framework conventions; implement the complete authorized change and its edge
  cases without speculative cleanup.

## Save useful findings

- During authorized implementation or documentation work, update affected feature
  notes when you discover durable, non-obvious facts, pitfalls, or changed behavior.
  During read-only analysis/review, suggest the note update in the reply unless
  documentation writes are also authorized. Do not edit memory merely to answer
  a question, or write a note for every tool call.
- Create `.agents/knowledge/features/<feature>.md` only for an actual feature.
  Use `.agents/templates/feature.md` as a starting point and add its path plus a
  one-line purpose to `.agents/knowledge/INDEX.md`.
- Cite source paths/symbols, the review date, evidence, and relevant tests. Mark
  observations, accepted decisions, open questions, and unverified assumptions
  separately. Do not record guesses as project rules.
- Update existing entries rather than accumulating contradictory duplicates.
  Remove or supersede stale claims and fix index links after renames/removals.
  Keep current behavior concise; put durable rationale in
  `.agents/knowledge/decisions.md` and link from architecture when relevant.
- Never store credentials, tokens, private user data, environment dumps, or entire
  transcripts. Knowledge files are repository content and may be committed.

## Finish

- Run only checks allowed by project instructions. State what changed, what was
  checked, what remains uncertain, and practical manual/device verification steps.
- Update architecture/context only if the task changes their documented facts.
  Do not claim that tests passed, an agent loaded a skill, or an index refreshed
  unless there is observable evidence.
