# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Mining Software Repositories study: do AI coding agents that open GitHub PRs obey the rules written in the repo's agent context files (AGENTS.md, CLAUDE.md, copilot-instructions.md, .cursorrules)? Full study design (RQ1–RQ4, causal design, P1=2025/AIDev vs P2=2026/self-mined, threats to validity) is in `../project-details.md` (outside this git repo). The rules currently checked, and the label semantics, are in `rules.md`.

Current state: RQ1, RQ2 (`rq2.ipynb`) and RQ3 (`rq3.ipynb`) on P1 (AIDev) are implemented; RQ2/RQ3 notebooks exec `fetch_data.ipynb` up to its section 8.

## Commands

Python 3.13, managed with **uv** (not conda/pip, despite the parent `.vscode/settings.json`).

```bash
uv sync                      # install deps incl. dev group (ipykernel)
uv run --with jupyterlab jupyter lab   # jupyterlab is not a dependency; or use VS Code with the .venv kernel
# headless run of one notebook (from src/ess_msr, so relative paths resolve):
uv run --with nbconvert jupyter nbconvert --to notebook --execute --inplace rq2.ipynb
```

There is no test suite, linter config, or CLI yet (`ess_msr:main` is a placeholder). Checkers are sanity-checked by small inline example calls at the end of their notebook cells.

## Architecture

The RQ1 pipeline lives in `src/ess_msr/fetch_data.ipynb`; `rq2.ipynb` and `rq3.ipynb` build on it. Run notebooks top to bottom; relative paths (`../../instruction-data`, `../../package_manager_violations.csv`) assume the notebook's own directory as CWD.

Pipeline:
1. **Load** AIDev PRs straight from Hugging Face (`hf://datasets/hao-li/AIDev@v4`, parquet via pandas) and GHAgentFiles context-file history from `instruction-data/context_metadata.csv`. Repo names are lowercased to join the two; symlinked context files are dropped.
2. **Effective rule set**: `context_files_at(repo, when)` picks, per file path, the latest version committed before the PR's `created_at` (date-based, not base SHA), dropping deleted files and old paths of renames. Returns content hashes.
3. **Rule detection**: `RULE_PATTERNS` keyword regexes run line by line over the concatenated context text (`read_file(hash)` reads `instruction-data/context_content/<file_hash>`). `rule_units(hashes, rule)` returns the matching sentences; for tests/changelog it drops lines under release headings, conditional lines, etc. Section 5 of the notebook prints matching lines for manual precision checks.
4. **Changed files / commit messages** from AIDev `pr_commit_details` and `pr_commits` parquet tables.
5. **Checkers** (`CHECKERS` dict): one function per rule type, taking a PR row and returning `not_applicable` / `complied` / `violated`. Tests/changelog checkers also check the rule's scope against `pr_kind(title)` (feature/fix/docs/other/unknown) and take optional `units` so RQ2 can pass the repo's rule text for PRs opened before the rule existed. They are lenient by design: prefer missing a violation over inventing one (e.g. package manager only counts a *newly added* wrong lockfile; commit format passes if title *or any* commit matches).
6. **RQ1 rates**: violation rate = violated / (complied + violated), reported both pooled and repo-averaged (each repo weighted equally), and per agent.
7. **Hand validation**: `package_manager_violations.csv` (all PM violations), `validation_sample.csv` (100 random pairs, labelled against the original checkers) and `validation_sample_v2.csv` (30 fresh tests/changelog violations; `label_final` = label from the current checkers). Results are in `RESULTS.md`.

Coupling to watch:
- `rq2.ipynb` / `rq3.ipynb` load `fetch_data.ipynb` as JSON and `exec` every code cell until the markdown cell starting with `## 8.`. Renumbering or renaming that heading, or adding cells with side effects before it, silently changes RQ2/RQ3.
- Section 9 of `fetch_data.ipynb` overwrites `package_manager_violations.csv`, wiping any hand-filled `correct` labels. Don't run it after labelling has started.
- RQ2 uses its own repo-level checker variants (`RQ2_CHECKERS`, e.g. `check_package_manager_for_repo`) instead of the RQ1 ones; changes to an RQ1 checker may need mirroring there.
- RQ2's human control loads `AIDev@v3`, while everything else uses `AIDev@v4`.

`RESULTS.md` (in Slovak) is the written summary of RQ1–RQ3 numbers and rule examples; update it when results change.

When adding a rule type: add a detection regex to `RULE_PATTERNS`, a checker to `CHECKERS`, and document it in `rules.md`.

## Data

`instruction-data/` (GHAgentFiles: `context_metadata.csv`, `repositories.csv`, ~185K content files named by hash) is gitignored and must be downloaded separately. AIDev is streamed from Hugging Face on each run, so the first load is slow and needs network.

Study constraints from `project-details.md` worth honoring: never use AI-generated-code classifiers for attribution; agent detection must be one shared module reused for P1 and P2; cache GitHub API responses and keep mining resumable; keep raw / intermediate / results data separated by period.
