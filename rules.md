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

The checker accepts any type word (`^[\w,-]+(\(.+\))?!?: .+`, repos add their own types) after dropping a leading `[tag]` and a leading emoji (`🐛 fix: ...`, emoji conventional commits).

## 2. Required tests

| | |
|---|---|
| Rule says | "add / write tests for new code" |
| Applies to | PRs that change source files (not only docs/config) **and** fall in the rule's scope (see below) |
| Violated if | no test file changed (`test_*`, `*_test.*`, `*.test.*`, `*.spec.*`, `*_Tests.cs`, files under `test/`, `tests/`, `__tests__/`, `Foo.UnitTests/`; lockfiles never count) |

---

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
| Applies to | PRs that change source files **and** fall in the rule's scope (see below) |
| Violated if | no `CHANGELOG*` / `.changeset/` file changed (or `README.md`, when the rule says the changelog lives there) |

---

## Scope of tests and changelog rules

Added after hand validation showed most "violations" of these two rules were false (see `RESULTS.md`).

**Lines that do not count as a rule** (rule is then not detected for that file):
- under a heading about releasing / publishing / deploying (release procedure, not a per-PR rule)
- conditional or optional: "if the user asks", "if applicable", "when appropriate", "consider", "for doc changes"
- about *where* tests go ("same directory", "named", "located"), not *that* they are needed
- about the PR description's changelog section, or links to `/changelog/` pages

**PR kind** comes from the title: Conventional Commit type (`feat` = feature, `fix` = fix, `docs` = docs, others = other), else docs words (docs, docstring, JSDoc, documentation, typo, README, "Document …"), else the first word (Fix…, Refactor/Update/Remove…, Add/Implement/Support…). Anything else is `unknown`.

**A rule sentence covers a PR when:**
- the PR is not docs-only, and
- if it names a language ("tests for new Python functions"), the PR changes files of that language, and
- if it is limited to new things ("new features / functionality / endpoints", "significant", "user-facing"), the PR is a feature (or a fix, when the sentence also mentions bugs/fixes), and
- (changelog) if it says "whenever `file.py` is modified", that file changed.

If no sentence covers the PR, the label is `not_applicable`. Unclear cases (e.g. `unknown` kind under a "new features" rule) are `not_applicable`, in line with the lenient design.

---

## Later (harder to extract or check)

| Rule | Violated if | Why later |
|---|---|---|
| Forbidden paths ("don't edit `generated/`") | a changed file matches the forbidden path | pulling the path out of free text is error-prone |
| Banned code patterns ("no `console.log`", "no `any`") | an added (`+`) diff line matches the pattern | needs a per-pattern list |
| Lint / format ("run ruff format") | rerunning the formatter at head changes files | needs checkout and tool runs per PR |

## Out of scope
Vague or style rules ("write clean code", "prefer composition").
