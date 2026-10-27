# Complete project setup before implementation

This gate applies until `.agents/PROJECT.md` and `.agents/ARCHITECTURE.md` are
complete. It does not block answering questions, reading code, or preparing the
setup documents. Missing setup does block product-code changes, installing
dependencies, migrations, app/server launches, and unrelated configuration edits.

1. Read existing README, agent guidance, manifests, relevant source entry points,
   and test configuration without executing project code. Reuse existing docs
   through links instead of creating competing architecture descriptions.
2. Replace required placeholders with verified facts and source paths. Clearly
   distinguish observed behavior, explicit user requirements, and proposed design.
   Do not guess business purpose, desired scope, secrets, or architectural consent.
3. Ask one concise batch of questions for missing purpose, scope, stack, constraints,
   or design decisions. Existing authorization and explicit preferences remain
   valid; do not ask for information already established by the user or source.
   For a new project, agree on the proposed architecture before marking it ready.
4. If questions cannot be asked or answered, report each unresolved field with its
   file path and the input needed. Leave status pending and do not implement the
   requested feature. In read-only tasks, propose documentation text in the reply
   instead of writing files without authorization.
5. Mark each document `Status: ready` only after all its required fields are
   resolved, evidence is cited, and no required placeholders remain. Record
   unavailable or inapplicable checks explicitly with a reason, rather than
   inventing commands or results. Then resume the authorized task.

`contextrivet project status` checks the scaffold's required sections, markers,
and files. It cannot verify the truth of documentation or enforce agent behavior.
If docs later become inaccurate, correct them from evidence; ask only about
decisions that materially affect the current task.
