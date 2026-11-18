# Do AI coding agents obey AGENTS.md?

More and more repositories contain agent context files: `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md` or `.cursorrules`. They are plain text instructions for AI coding agents, such as "use pnpm" or "add tests for new features".

We check whether agents that open real pull requests on GitHub follow the rules written in these files.

| | Question | Status |
|---|---|---|
| RQ1 | How often do agent PRs break a checkable rule from the repo's context file? | done for P1 |
| RQ2 | Do agents follow a rule because it is written down? | done for P1 |
| RQ3 | What happens to PRs that break a rule: rejected, fixed, or merged as is? | done for P1 |
| RQ4 | Did compliance change between 2025 (P1) and 2026 (P2)? | P2 PRs counted, details not fetched yet |

All numbers in this file are for P1, the AIDev dataset of agent PRs up to 2025-08-01.

The full study design is in `../project-details.md`. Detailed results, in Slovak, are in `RESULTS.md`.


## 1. How the dataset is built

Two modules do all the data work. Every notebook starts with `prs, pr_rule = load_labeled()`.

```
AIDev (Hugging Face)          GHAgentFiles (instruction-data/)
pull_request, pr_commits,     context_metadata.csv = every commit that touched a context file
pr_commit_details             context_content/<hash> = file text at that commit
        │                                   │
        └──────────────┬────────────────────┘
                 data.load_prs()                         → prs      (one row per agent PR)
                       │
     rules.stated_rules() + rules.label()                → pr_rule  (one row per (PR, rule), labelled)
```

### Step 1: agent PRs

`data.aidev(table)` downloads an AIDev parquet table once into `~/.cache/huggingface` and reads it locally after that.

AIDev v4 has 71,677 agent PRs from Codex, Copilot, Devin, Cursor, Claude Code and Jules. AIDev already says which tool opened each PR.

### Step 2: the context files the agent could see

For each PR, `data.context_files_at(repo, created_at)` rebuilds the repo's context files as they were when the PR was opened. It takes every GHAgentFiles change to the repo committed before the PR and keeps the latest version of each file path.

Files that were deleted by then are dropped. So are the old paths of renamed files, and symlinks, which only point to another context file.

We keep a PR only if its repo had at least one context file at that moment. That leaves 23,422 PRs in 1,326 repos.

The lookup uses the date the PR was opened, not its base commit. This is an approximation we know about.

### Step 3: the rules those files state

`rules.rule_units(hashes, rule)` reads the files line by line with one keyword regex per rule type. It returns the matching sentences, which we call rule units. A sentence that wraps onto the next line is joined back together.

For the tests and changelog rules, hand validation showed that many matching lines are not real rules for every PR. We drop:

- lines under a heading about releasing, publishing or deploying, since those describe a release procedure
- conditional lines such as "if the user asks", "if applicable" or "consider"
- lines about where tests go ("same directory", "named …") rather than whether they are needed
- lines about the changelog section of the PR description, and links to `/changelog/` pages

### Step 4: what each PR changed

`pr_commit_details` and `pr_commits` give us the changed files, the newly added files, and the first line of each commit message. 590 PRs have no file information and are dropped when labelling.

### Step 5: labels

Each (PR, stated rule) pair gets one label from that rule's checker:

- `complied`: the rule applies and the PR follows it
- `violated`: the rule applies and the PR breaks it
- `not_applicable`: the PR could not have broken the rule, for example a docs-only PR under "add tests"

When a checker is unsure, it returns `not_applicable` or `complied`. A missed violation makes our rates a bit too low, which we prefer to reporting violations that did not happen.

### Example

This one is made up to show the steps. The repo's `AGENTS.md` at the time of the PR says:

```
- Use Conventional Commits for PR titles.
- Always add tests for new features.
```

A Copilot PR titled "Add CSV export", with the commits `Initial plan` and `Add export`, changes only `src/export.py`.

| Rule | Why | Label |
|---|---|---|
| commit_format | neither the title nor any commit has the form `type: description` | violated |
| required_tests | the title starts with "Add", so it counts as a feature PR and the rule covers it; a source file changed but no test file did | violated |

Had the same PR been titled "Fix crash in export", the tests rule would not apply, because it only asks for tests on new features. The label would be `not_applicable`.


## 2. The four rule types

| Rule | Real example from a context file | Applies when | Violated when |
|---|---|---|---|
| commit_format | "Use Conventional Commits: `type(scope): description`" | always, since every PR has a title | neither the title nor any commit matches `word(scope)!: text`. A leading `[tag]` or emoji is ignored, and any type word is accepted |
| required_tests | "Always add tests for new functionality" | the PR changed a source file and a rule sentence covers it (see below) | no test file changed (`tests/…`, `test_*.py`, `*_test.go`, `*.test.ts`, `FooTest.java`, `Foo.UnitTests/…`; lockfiles never count) |
| changelog | "Update `CHANGELOG.md` under Unreleased" | as for tests; a rule like "whenever `foo.py` changes" applies only if `foo.py` changed | no `CHANGELOG*`, `.changeset/` or `changes.md` file changed (or `README.md`, if the rule says the changelog lives there) |
| package_manager | "Use `pnpm add` instead of `npm install`" | the PR touched a lockfile from the same ecosystem (JS or Python) | the PR added a new lockfile of another manager, such as a new `package-lock.json` in a pnpm repo. Editing an existing lockfile of another manager does not count, because some sub-packages use one on purpose. `test/`, `fixtures/` and `examples/` are ignored |

### When a tests or changelog sentence covers a PR

First we guess the kind of PR from its title. A Conventional Commit type decides it if there is one: `feat` is a feature, `fix` is a fix, `docs` is docs. Otherwise we look for docs words, and then at the first word ("Fix…", "Add…", "Refactor…").

A sentence covers the PR only if:

- the PR is not docs-only
- the PR changes files in the language the sentence names, if it names one ("tests for new Python functions")
- the PR is a feature, if the sentence is about new things ("new features", "significant", "user-facing"). A fix also counts when the sentence mentions bugs.

Anything unclear is `not_applicable`.


## 3. RQ1: how often are rules broken?

Notebook: `rq1.ipynb`

### Method

We drop `not_applicable` pairs and compute

```
violation rate = violated / (complied + violated)
```

in two ways. The pooled rate counts all PRs together. The repo-averaged rate is the mean of each repo's own rate, which keeps a few repos with thousands of agent PRs from dominating.

### Example

Repo A has 100 labelled PRs and 10 of them are violations. Repo B has 4 PRs and 2 violations.

The pooled rate is 12 / 104 = 11.5 %. The repo-averaged rate is (10 % + 50 %) / 2 = 30 %. The pooled number mostly describes repo A.

### Result

| Rule | PRs | Repos | Pooled | Repo-avg |
|---|---:|---:|---:|---:|
| changelog | 514 | 31 | 38 % | 50 % |
| required_tests | 1,050 | 125 | 25 % | 26 % |
| commit_format | 2,043 | 139 | 12 % | 20 % |
| package_manager | 267 | 61 | 9 % | 18 % |

Agents mostly get the title format and the package manager right. They often leave out tests and changelog entries, the rules that mean extra work.

By tool, Claude Code has the lowest rates on most rules, and Devin and Cursor the highest.


## 4. RQ2: do agents follow the rule because it is written down?

Notebook: `rq2.ipynb`

A high compliance rate on its own does not show that the rule had any effect. An agent may use pnpm just because it sees `pnpm-lock.yaml` in the repo. So we look inside one repo at a time and compare agent PRs opened before the rule was added with those opened after.

### Method

1. Every agent PR gets one row per rule we study. `rule_active` says whether the rule was in the context file when the PR was opened.
2. We keep repos with at least 5 agent PRs on each side.
3. We label all rows, including PRs opened before the rule existed. Those are checked against the repo's first version of the rule (the same sentences for tests, the same required manager for package_manager), so both sides face the same rule.
4. We keep repos with at least 3 labelled PRs on each side and compute each repo's violation rate without and with the rule.
5. We test the change three ways:
   - a Wilcoxon signed-rank test over repos, one paired point per repo
   - a conditional logistic regression grouped by repo, which uses every PR but only compares PRs within the same repo
   - a human control (difference-in-differences). If human PRs in the same repos changed too, the drop could come from the project as a whole and not from agents reading the rule. AIDev v3 human PRs only have titles, so this works for commit_format only.

### Example

This one is real. In `rnwood/smtp4dev`, 44 % of agent PRs had a non-conventional title before the commit format rule was added, and 0 % after. It is one of the 9 repos (out of 16) where the rate went down.

### Result

| Rule | Repos | Median rate without / with rule | Improved / worse / same | Odds ratio (within repo) | p |
|---|---:|---|---|---:|---:|
| commit_format | 16 | 28 % / 4 % | 9 / 5 / 2 | 0.32 | < 0.001 |
| required_tests | 11 | 33 % / 13 % | 6 / 2 / 3 | 0.68 | 0.26 |
| package_manager | 7 | 0 % / 0 % | 3 / 1 / 3 | 0.40 | 0.46 |

For commit_format, the human control supports the effect. Agent violations went from 41 % to 15 %, while humans did not improve (3 % before, 16 % after). The interaction odds ratio is 0.067 (p = 0.001), but it rests on only 151 human PRs, so we treat it as preliminary.

The tests effect goes in the same direction but is not significant. For the package manager we see no effect: agents already copy the lockfile that is in the repo, with or without the rule.


## 5. RQ3: what happens to PRs that break a rule?

Notebook: `rq3.ipynb`

### Method

1. Outcome of each PR: `merged` if it has a `merged_at`, `rejected` if it was closed without merging, `open` if there is no outcome yet. Open PRs are left out.
2. What the agent itself submitted. The RQ1 label looks at all commits, so a human who adds the missing test hides the violation. Copilot, Devin, Cursor and Jules commit under their own bot accounts, so we rerun the checker on the bot's commits only (`agent_label`) and compare it with the final label. Claude Code and Codex commit as the user, which means we cannot see human fixes for them (`fixes_visible = False`).
3. Fate of each PR where the agent broke the rule: `rejected`, `fixed_then_merged` (the final PR complies), `merged_as_is`, or `open`.
4. Merge effect. Among closed PRs, we test whether violating PRs are merged less often than complying ones, with the same within-repo regression as in RQ2. Grouping by repo matters here because some repos merge almost everything and others almost nothing.
5. Whether reviewers notice. We search reviews, comments and inline comments from humans (not the PR author, not bots) with a keyword regex per rule, such as "missing tests" or "changelog".

### Example

Made up for illustration. A Copilot PR changes `src/api.ts` without adding a test, so `agent_label` is `violated`. A maintainer then pushes `test/api.test.ts` and merges.

The final label is `complied` and the fate is `fixed_then_merged`. If we only looked at the final PR, we would count it as a clean, compliant PR.

### Result

Humans fix the violation before merging in only 8 to 11 % of cases. Most violating PRs are either rejected (25 to 50 %) or merged with the violation still there (29 to 66 %).

PRs that break the commit format (odds ratio 0.19) or skip the changelog (0.34) are merged noticeably less often. Missing tests make no difference (0.90, not significant). This is a correlation: a PR with a sloppy title may also be worse in other ways.

Reviewers almost never point out the violation. It is mentioned in only 2 to 3 % of violating PRs.


## 6. Validation

We checked labels by hand against the actual PRs. The files are in `validation/`.

| What we checked | Result |
|---|---|
| all 23 package_manager violations | 19 correct, 3 wrong, 1 unclear, so precision is 86 % |
| 100 random (PR, rule) pairs, original checkers | 19 of 20 commit_format violations were correct. For tests and changelog only about 30 to 35 % were, which led to the scope rules in section 2 |
| 30 new tests and changelog violations, final checkers | tests 8 of 10 (80 %), changelog 10 of 12 (83 %) |

Claude proposed these labels. They still need a human pass, ideally by two people so we can report how often they agree.


## 7. P2: collecting 2026 PRs

This part is in progress.

### Agent detection

`agents.py` has one detection function for both periods. It uses provenance signals only: the bot account that opened the PR (Copilot, Devin, Jules), a footer or link in the PR body (Claude Code, Codex, Cursor), and the branch prefix (`codex/`, `cursor/`, `claude/` …).

On P1, using only author and body, it finds 100 % of Copilot, Devin and Jules PRs, 91 % of Claude Code, 84 % of Codex and 57 % of Cursor. AIDev has no branch names. GitHub does, so the branch prefix should catch most of the missing Codex and Cursor PRs in P2.

### Listing 2026 PRs

`p2_prs.py` takes the 50 P1 repos with the most labelled PRs and fetches all their PRs since 2026-01-01 through the GitHub GraphQL API (`gh`). Each repo is saved in `data/p2/raw/pulls/`, so a rerun continues where it stopped.

### Usable window

GHAgentFiles history ends on 2026-07-01, and earlier for some repos (see `data.crawled_until`). We only use PRs from January to June 2026 that were opened before the repo's crawl date, because for later PRs we don't know what the context file said.

### How many 2026 agent PRs there are

We fetched all 50 core repos (run on 2026-11-18). In the usable window they have 12,095 agent PRs, almost four times the 3,114 labelled P1 PRs from the same repos.

| Tool | P2 agent PRs | Under one of our 4 rules | P1 labelled PRs, same repos |
|---|---:|---:|---:|
| Claude Code | 4,146 | 3,795 | 171 |
| Devin | 3,124 | 2,924 | 318 |
| Cursor | 2,402 | 2,401 | 279 |
| Codex | 1,275 | 1,271 | 1,141 |
| Copilot | 1,148 | 900 | 1,205 |
| Total | 12,095 | 11,291 | 3,114 |

34 of the 50 repos have at least 10 agent PRs under a rule, and all five tools appear in both periods, so RQ4 can compare each tool with itself in the same repos.

"Under a rule" only means the repo's context file states one of the four rules at that time. As in P1, many of these pairs will turn out `not_applicable` once labelled, so the usable number will be in the thousands, not 11,000.

Claude Code grew the most: 171 labelled PRs in P1, over 4,000 in P2.

### What to keep in mind

Devin is concentrated in one repo. `fern-api/fern` has 2,502 of its 3,124 PRs. The repo-averaged rates keep fern from dominating the overall numbers, but Devin's own numbers will mostly describe that one repo.

Two repos are very large. `fern-api/fern` (2,706 agent PRs) and `crewaiinc/crewai` (1,132) are about a third of all P2 agent PRs. We plan to cap the number of PRs per repo when fetching details.

The detection signals differ from P1. Most Codex PRs are now caught by the `codex/` branch (1,085 of 1,275), not the link in the PR body. Most Devin PRs are caught by an `app.devin.ai` link in the body (2,560), not the bot account (543). This looks right, but a hand check of about 100 detected PRs, plus some PRs marked as human, should confirm it before we rely on the numbers.

Three repos have many 2026 agent PRs but no usable ones: `azure/azure-sdk-for-python`, `dotnet/maui` and `yamadashy/repomix`. Their context files no longer state any of our four rules in 2026. For azure-sdk-for-python this is a real change: the changelog rule was removed from its context file.

### Next steps

1. Hand-check a sample of detected agent PRs and PRs marked as human.
2. Fetch changed files, commits and reviews for the P2 agent PRs, capped per repo, and label them with the same checkers.
3. Compare P1 and P2 per rule and per tool within the same repos (`rq4.ipynb`).


## Files and commands

| File | What it does |
|---|---|
| `src/ess_msr/data.py` | loads AIDev and GHAgentFiles, finds the context files at a date, `load_prs()` |
| `src/ess_msr/rules.py` | rule regexes, checkers, `label()`, `load_labeled()` |
| `src/ess_msr/agents.py` | agent detection for P1 and P2 |
| `src/ess_msr/p2_prs.py` | lists and counts 2026 PRs in the core repos |
| `src/ess_msr/rq1.ipynb`, `rq2.ipynb`, `rq3.ipynb` | analysis and statistics for one research question each |
| `src/ess_msr/validation.ipynb` | regex precision check, export of package_manager violations for hand labelling |
| `validation/` | hand-labelled CSVs |
| `RESULTS.md` | detailed results, in Slovak |

```bash
uv sync                                    # Python 3.13 + dependencies
uv run python -m ess_msr.rules             # checker self-test, no data needed
uv run python -m ess_msr.agents            # detection recall on P1
uv run python -m ess_msr.p2_prs            # 2026 PR counts (needs `gh auth login`)
uv run --with nbconvert jupyter nbconvert --to notebook --execute --inplace src/ess_msr/rq1.ipynb
```

`instruction-data/` (GHAgentFiles) has to be downloaded separately. AIDev, about 1.6 GB, downloads on the first run.


## Limitations

- Context files are matched by the date the PR was opened, not its base commit.
- Rules are found with keyword regexes, and checkers look at file names and titles, not at the diffs.
- The human control in RQ2 is small: 151 PRs in 5 repos.
- In RQ3 we only see human fixes for tools with a bot account, and the mention regexes are rough.
- The validation sample is small and has not been checked by a person yet.
