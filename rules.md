# Rules we check (RQ1)

Each rule is checked per **(PR, rule)** pair, against the context file version that existed when the PR was opened.

Label for each pair:
- `not_applicable`: the PR couldn't have broken the rule (rule not in the file, or the PR doesn't touch the relevant area)
- `complied`: the rule applies and the PR follows it
- `violated`: the rule applies and the PR breaks it
- `undecidable`: data missing (e.g. no diff)

**Violation rate = violated / (complied + violated)**

---

## 1. Commit / PR title format

| | |
|---|---|
| Rule says | "Use Conventional Commits", or gives `feat:` / `fix:` examples |
| Applies to | every PR |
| Violated if | PR title (or any agent commit message) does not match `^(feat\|fix\|docs\|style\|refactor\|perf\|test\|build\|ci\|chore\|revert)(\(.+\))?!?: .+` |

## 2. Required tests

| | |
|---|---|
| Rule says | "add / write tests for new code" |
| Applies to | PRs that change source files (not only docs/config) |
| Violated if | no test file changed (`test_*`, `*_test.*`, `*.test.*`, `*.spec.*`, files under `test/`, `tests/`, `__tests__/`) |

## 3. Package manager

| | |
|---|---|
| Rule says | "use pnpm / yarn / bun / uv / poetry", "don't use npm / pip" |
| Applies to | PRs that touch a manifest or lockfile |
| Violated if | the wrong lockfile changes, e.g. `package-lock.json` when pnpm is required (`pnpm-lock.yaml`), or `requirements.txt` edits when uv/poetry is required (`uv.lock` / `poetry.lock`) |

## 4. Changelog update

| | |
|---|---|
| Rule says | "update CHANGELOG" |
| Applies to | PRs that change source files |
| Violated if | no `CHANGELOG*` file changed |

---

## Later (harder to extract or check)

| Rule | Violated if | Why later |
|---|---|---|
| Forbidden paths ("don't edit `generated/`") | a changed file matches the forbidden path | pulling the path out of free text is error-prone |
| Banned code patterns ("no `console.log`", "no `any`") | an added (`+`) diff line matches the pattern | needs a per-pattern list |
| Lint / format ("run ruff format") | rerunning the formatter at head changes files | needs checkout and tool runs per PR |

## Out of scope
Vague or style rules ("write clean code", "prefer composition").
