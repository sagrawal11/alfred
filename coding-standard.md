# Alfred – Coding Standard

This document defines coding standards for the Alfred codebase. It is the single source of truth for style, structure, and maintainability. Tools (e.g. code-simplifier) and contributors should follow it.

**Stack:** Python 3 (Flask), Jinja2 templates, vanilla JavaScript (in templates), CSS, Supabase/SQL.

---

## 1. General principles

- **Preserve functionality.** Refactors and simplifications must not change behavior, outputs, or features. When in doubt, keep existing behavior.
- **Clarity over brevity.** Prefer readable, explicit code over clever or dense one-liners. Code is read more often than it is written.
- **Balance.** Simplify structure and remove redundancy, but do not over-simplify: avoid packing too many concerns into one function, and do not remove useful abstractions that improve organization.
- **Consistency.** Match existing patterns in the same layer (e.g. repositories, routes, templates). When adding something new, follow the style of the file and the module.

---

## 2. Python

### 2.1 Style and layout

- Follow **PEP 8** (line length can go to 100–120 where it aids readability).
- Use **4 spaces** for indentation. No tabs.
- Use **double quotes** for strings unless the string contains double quotes or the project file already uses single quotes consistently.
- Use a **single blank line** between top-level definitions (classes, functions). No extra blank lines between related one-liners or short blocks unless it improves readability.
- Order imports: standard library, then third-party, then local/app, each group alphabetized. One import per line for non-`from` imports when the list is long.

### 2.2 Naming

- **Modules/files:** `snake_case` (e.g. `user_repository.py`, `tool_executor.py`).
- **Classes:** `PascalCase`.
- **Functions and variables:** `snake_case`.
- **Constants:** `UPPER_SNAKE_CASE` (e.g. in `config.py`).
- **Private/internal:** leading `_` for module-private (e.g. `_first_name()`). Not required for class-private if the name is already clear.

### 2.3 Functions and methods

- Prefer **small, focused functions** that do one thing. Split long procedures into named helpers.
- Use **explicit parameter names** and **keyword arguments** for clarity when there are multiple optional parameters (e.g. `create_todo(user_id=uid, content=text, type="reminder")`).
- Use **type hints** for public function parameters and return types where they add clarity (e.g. `def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:`). Not required for trivial one-liners or obvious types.
- Prefer **early returns** to reduce nesting (e.g. guard clauses for invalid input, then main logic).

### 2.4 Error handling and validation

- **Validate at boundaries** (e.g. route handlers, tool entrypoints). Use clear error messages and appropriate HTTP status codes or tool result fields.
- Use **specific exceptions** where possible (e.g. `ToolValidationError` instead of bare `ValueError` when that’s the project convention).
- **Avoid broad `except Exception`** unless you re-raise or log and then re-raise. Prefer catching specific exceptions; if you must catch broadly, log the error and either re-raise or return a structured error to the caller.
- Do **not** use try/except purely to avoid an if-check; use it for real error cases (I/O, parsing, external calls).

### 2.5 Repositories and data layer

- Keep **repositories** focused on data access: queries, inserts, updates. No business rules or response formatting.
- Prefer **one public method per logical operation** (e.g. `get_by_date`, `create_sleep_log`). Compose in services or handlers if needed.
- Return **plain dicts or typed structures** from repositories; avoid leaking Supabase-specific types in public APIs.

### 2.6 Flask and web layer

- **Routes:** Keep handlers thin. Parse request, validate, call service/repository, return response. Move non-trivial logic into `web/`, `services/`, or `core/`.
- **JSON responses:** Use consistent shapes (e.g. `{ "success": true, ... }` or `{ "success": false, "error": "..." }`).
- **Templates:** Pass only the data the template needs; no heavy computation in the route.

---

## 3. JavaScript (templates)

- **Vanilla JS** in `<script>` blocks. No build step; no React/TypeScript/ES modules in this project.
- Use **`const` / `let`**; avoid `var`.
- Prefer **`function` declarations** for top-level or reusable logic so they are named in stack traces and in the code. Arrow functions are fine for short callbacks (e.g. `addEventListener`).
- **Naming:** `camelCase` for variables and functions.
- **Avoid nested ternaries.** Use `if/else` or a small helper. Keep conditionals readable.
- **DOM:** Prefer `document.getElementById` / `querySelector` when that’s what the rest of the file uses. Cache node references when used more than once.
- **Async:** Use `async/await` for fetch. Handle errors (e.g. show a message, re-enable a button) and avoid silent failures.
- **No inline scripts in HTML** for non-trivial logic; keep logic in the same template’s `<script>` block or a clear, small snippet.

---

## 4. CSS

- Use **existing variables** where available (e.g. `var(--bw-fg)`, `var(--bw-border)` in dashboard styles). Stay consistent with the file you’re in (landing vs dashboard vs policy).
- **Class names:** `kebab-case` or existing BEM-like patterns (e.g. `site-footer`, `prefs-status`, `dashboard-container`).
- Prefer **class-based styling**; avoid inline styles except for one-off overrides (e.g. dynamic values) or when the project already does it (e.g. oauth_done).
- **Mobile:** Add or adjust media queries so new UI works on small screens; follow the breakpoints already used in the file (e.g. 768px, 480px).
- **Specificity:** Prefer a single class or a short selector; avoid long chains unless necessary for overrides.

---

## 5. Jinja2 / HTML

- **Templates:** Use **two spaces** for indentation in HTML/Jinja. Match the indentation style of the file.
- **Reuse:** Use `{% include %}` for repeated blocks (e.g. site footer, shared form bits).
- **Logic:** Keep logic in Python; templates should only branch on passed-in data (e.g. `{% if user %}`, `{% for item in items %}`). No heavy computation.
- **URLs:** Use `{{ url_for('route_name') }}` or `url_for('route_name', arg=val)`; avoid hardcoded paths.
- **Accessibility:** Prefer semantic elements (`<main>`, `<header>`, `<footer>`, `<button>`, `<label>`). Associate labels with inputs where applicable.

---

## 6. What to avoid

- **Nested ternary operators** – use `if/else` or a switch/helper.
- **Overly clever or dense one-liners** that hurt readability.
- **Removing helpful abstractions** (e.g. a small helper or a named constant) just to reduce line count.
- **Mixing concerns** – e.g. business logic in repositories, SQL in route handlers, or heavy logic in templates.
- **Silent failures** – log or return a clear error instead of swallowing exceptions.
- **Inconsistent naming** within a file or module (e.g. mixing `get_user` and `fetchUser` in the same layer).
- **Comments that restate the code** – prefer clear names and structure; comment only when explaining “why” or non-obvious behavior.

---

## 7. Documentation and comments

- **Docstrings:** Use for public modules, classes, and non-obvious public functions (e.g. one line for purpose, plus Args/Returns if helpful). Not required for trivial getters/setters.
- **Comments:** Explain non-obvious behavior, business rules, or workarounds. Do not comment obvious code.
- **README / docs:** Update them when you add features or change setup; keep them in sync with the code.

---

## 8. Scope of changes

- When **refactoring or simplifying**, limit changes to the files or sections you’re working on unless you’re explicitly doing a broader cleanup.
- When **adding features**, follow the patterns of the existing file and the layer (e.g. new route → same structure as other routes in that blueprint).
- **Do not** change behavior, remove features, or alter external contracts (e.g. API response shape, tool names/arguments) unless that’s the stated goal of the task.

---

This standard is intended to be updated as the project evolves. New conventions (e.g. for new services or front-end patterns) should be added here so code-simplifier and contributors can stay aligned.
