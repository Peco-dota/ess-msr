# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Mining Software Repositories study: do AI coding agents that open GitHub PRs obey the rules written in the repo's agent context files (AGENTS.md, CLAUDE.md, copilot-instructions.md, .cursorrules)? Full study design (RQ1–RQ4, causal design, P1=2025/AIDev vs P2=2026/self-mined, threats to validity) is in `../project-details.md` (outside this git repo). How the dataset is built, the rule definitions, label semantics and RQ1–RQ3 methods are in `README.md`.

Current state: RQ1–RQ3 on P1 (AIDev) are implemented (`rq1.ipynb`, `rq2.ipynb`, `rq3.ipynb`); P2 (2026) collection has started (`agents.py`, `p2_prs.py`); RQ4 is not started.

## Commands

Python 3.13, managed with **uv** (not conda/pip, despite the parent `.vscode/settings.json`).

```bash
uv sync                      # install deps incl. dev group (ipykernel)
uv run --with jupyterlab jupyter lab   # jupyterlab is not a dependency; or use VS Code with the .venv kernel
# headless run of one notebook:
uv run --with nbconvert jupyter nbconvert --to notebook --execute --inplace src/ess_msr/rq2.ipynb
uv run python -m ess_msr.rules   # assert-based self-check of the checkers (no data needed)
```

There is no test suite, linter config, or CLI yet (`ess_msr:main` is a placeholder).

## Architecture

Data fetching/preparation and rule checking live in plain modules; the notebooks only do the analysis of one question each and call `prs, pr_rule = load_labeled()`. Paths are resolved from the module location, so notebooks work from any CWD.

- `src/ess_msr/data.py` – fetching and preparing data
  1. **Load**: `aidev(table, columns, version)` downloads one AIDev parquet table into the Hugging Face cache once (`hf_hub_download`), then reads it locally. GHAgentFiles context-file history from `instruction-data/context_metadata.csv`. `with_repo()` lowercases repo names to join the two; symlinked context files are dropped.
  2. **Effective rule set**: `context_files_at(repo, when)` picks, per file path, the latest version committed before the PR's `created_at` (date-based, not base SHA), dropping deleted files and old paths of renames. Returns content hashes; `read_file(hash)` / `context_text(hashes)` read `instruction-data/context_content/<file_hash>`.
  3. `load_prs()`: agent PRs that had a context file, with `context_hashes`, `changed_files`, `added_files`, `commit_messages` (from `pr_commit_details` / `pr_commits`).
- `src/ess_msr/rules.py` – rule detection and checkers
  1. **Rule detection**: `RULE_PATTERNS` keyword regexes run line by line over the concatenated context text. `rule_units(hashes, rule)` returns the matching sentences; for tests/changelog it drops lines under release headings, conditional lines, etc.
  2. **Checkers** (`CHECKERS` dict): one function per rule type, taking a PR row and returning `not_applicable` / `complied` / `violated`. Tests/changelog checkers also check the rule's scope against `pr_kind(title)` (feature/fix/docs/other/unknown) and take optional `units`, the package manager checker optional `required`, so RQ2 can pass the repo's rule for PRs opened before the rule existed. They are lenient by design: prefer missing a violation over inventing one (e.g. package manager only counts a *newly added* wrong lockfile; commit format passes if title *or any* commit matches).
  3. `label(prs)` → `pr_rule`; `load_labeled()` = `load_prs()` + `stated_rules` + `label`.
- `src/ess_msr/agents.py` – `detect_agent(author, body, branch)`: shared P1/P2 agent detection from bot accounts, PR body signals and branch prefixes. `python -m ess_msr.agents` prints recall on AIDev.
- `src/ess_msr/p2_prs.py` – lists 2026 PRs of the 50 core repos via `gh api graphql` (GraphQL bot logins are mapped to the REST/AIDev spelling), caches one JSON per repo in `data/p2/raw/pulls/` (resumable; `data/` is gitignored), and prints agent PR counts. Usable P2 window is Jan–Jun 2026 and before `data.crawled_until(repo)` (GHAgentFiles crawl date per repo).
- `rq1.ipynb`: PRs per rule, violation rate = violated / (complied + violated), pooled and repo-averaged (each repo weighted equally), and per agent.
- `rq2.ipynb`: before/after the rule within a repo (Wilcoxon, conditional logit, human-control DiD). `rq3.ipynb`: fate of violating PRs, merge effect, reviewer mentions.
- `validation.ipynb`: prints random lines matched by each rule regex (precision check) and exports `validation/package_manager_violations.csv` (only if it does not exist yet, so hand labels are kept). Hand-labelled files in `validation/`: `package_manager_violations.csv`, `validation_sample.csv` (100 random pairs, labelled against the original checkers), `validation_sample_v2.csv` (30 fresh tests/changelog violations; `label_final` = label from the current checkers). Results are in `RESULTS.md`.

Coupling to watch:
- RQ2's human control loads `AIDev@v3`, while everything else uses `AIDev@v4`.
- `rq3.ipynb` has its own `BOT_AUTHORS` = **commit** author per tool (e.g. Cursor commits as `cursoragent`), unlike `agents.BOT_AUTHORS` = PR opener. Keep both in mind when changing detection.

`RESULTS.md` (in Slovak) is the written summary of RQ1–RQ3 numbers and rule examples; update it when results change.

When adding a rule type: add a detection regex to `RULE_PATTERNS`, a checker to `CHECKERS`, and document it in `README.md` §2.

## Data

`instruction-data/` (GHAgentFiles: `context_metadata.csv`, `repositories.csv`, ~185K content files named by hash) is gitignored and must be downloaded separately. AIDev tables are downloaded to `~/.cache/huggingface` on first use (~1.6 GB for v4), so the first run is slow and needs network.

Study constraints from `project-details.md` worth honoring: never use AI-generated-code classifiers for attribution; agent detection must be one shared module reused for P1 and P2; cache GitHub API responses and keep mining resumable; keep raw / intermediate / results data separated by period.
