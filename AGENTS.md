# AGENTS.md

## Role

Codex acts as a deterministic compiler/renderer of the architecture model.
Codex is NOT the architecture decision authority.

## Source of Truth

- Architecture SSOT: `model/architecture.yml`
- Database SSOT: `model/db.dbml` when present.
- Generated artifacts: `build/` and `out/`.

Never edit generated files manually.

## Architecture Rules

- Never invent architecture.
- Never add, remove, rename or reinterpret architectural elements unless explicitly requested.
- Never resolve `open_questions`.
- Never convert candidates or implementation options into confirmed technologies.
- Never change `status`, `source`, `conflicts`, architectural invariants or governance rules unless explicitly requested.
- If required information is absent or ambiguous, fail clearly and report it.
- Architecture changes are model-first and require explicit instruction.
- Never modify the architecture model merely to make a validator or renderer succeed.

## Validation

Use the repository Makefile as the canonical execution interface.

Before generation run:

`make validate`

If validation fails, fix only files that are explicitly within the scope of the current task, or report the failure.

Do not change architectural facts to satisfy validation.

## Views

- Render only views declared in `model/architecture.yml`.
- `views[].elements` is the authoritative membership list for each view.
- Maximum architectural nodes per view is defined by `architecture.view_constraints.max_nodes_per_view`.
- Never insert undeclared architectural nodes into a view.
- Graphical stubs and legends are presentation artifacts, not architecture.
- Final views must not contain elements with `status: open_question`.
- If `collapse` is absent, do not collapse architectural elements implicitly.
- Respect `include_external` exactly as declared by the view.

## Generated Artifacts

- Never hand-edit `build/` or `out/`.
- Fix generators, not generated SVG/PDF files.
- Output must be reproducible from the same model and dependency versions.
- Do not treat generated artifacts as architecture source files.

## Icons

- Prefer classes available in the installed `diagrams` package.
- Verify classes programmatically before referencing them.
- Never invent icon class names.
- Never download third-party icons without explicit approval.
- `assets/icons/` is reserved for explicitly approved local icons.
- Use a generic fallback when no approved icon exists and report the fallback.

## Technology Decisions

Do not infer concrete technologies from generic capabilities.

Examples:

- `container_orchestrator: open_question` does not authorize choosing AKS or Azure Container Apps.
- LogBERT is a candidate, not a confirmed detector.
- An unspecified observability platform must remain unspecified.
- An unspecified LLM provider must remain unspecified.
- An unspecified object-storage implementation must remain unspecified.

## Workflow

Keep changes small and scoped to the requested task.

Before completion:

1. Run `make validate`.
2. Run the relevant generator or build target.
3. Run `make all`.
4. Report remaining warnings, fallback icons and unresolved visual issues.

If `make all` fails, correct only files authorized by the task.

Never modify `model/architecture.yml` merely to make generated output succeed.