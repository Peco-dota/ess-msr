"""Fetch and prepare P1 data: AIDev agent PRs (Hugging Face) and GHAgentFiles context-file history (`instruction-data/`)."""

from functools import cache
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[2]
CONTEXT_DATA = ROOT / "instruction-data"


def aidev(table, columns=None, version="v4"):
    """One AIDev table, e.g. aidev("pr_reviews", ["pr_id", "body"])."""
    # ponytail: whole file goes to the HF cache (~/.cache/huggingface) on first use (~1.6 GB for v4), later runs read it locally
    path = hf_hub_download("hao-li/AIDev", f"{table}.parquet", repo_type="dataset", revision=version)
    return pd.read_parquet(path, columns=columns)


def with_repo(prs):
    """Add a lowercase `owner/name` repo column (joins with GHAgentFiles) and parse created_at."""
    prs["repo"] = prs.repo_url.str.replace("https://api.github.com/repos/", "").str.lower()
    prs["created_at"] = pd.to_datetime(prs.created_at, utc=True)
    return prs


@cache
def context_history():
    """GHAgentFiles context-file changes, one DataFrame per repo."""
    changes = pd.read_csv(CONTEXT_DATA / "context_metadata.csv", low_memory=False)
    changes["repo"] = changes.repository.str.lower()
    changes["date"] = pd.to_datetime(changes.commit_date, unit="s", utc=True)
    changes = changes[~changes.symbolic_link]  # symlinks just point to another context file
    return {repo: group for repo, group in changes.groupby("repo")}


@cache
def crawled_until():
    """repo -> last commit GHAgentFiles saw. After it the context-file state is unknown (matters for P2)."""
    repos = pd.read_csv(CONTEXT_DATA / "repositories.csv", usecols=["name", "lastCommit"])
    return dict(zip(repos.name.str.lower(), pd.to_datetime(repos.lastCommit, utc=True)))


def context_files_at(repo, when):
    """Hashes of the latest version of each context file in `repo` committed before `when`."""
    history = context_history().get(repo)
    if history is None:
        return []

    before = history[history.date < when]

    latest = before.sort_values("date").groupby("file_path").tail(1)
    latest = latest[latest.git_change_type != "D"]

    # a renamed file still shows its old path as alive -> drop old paths
    renamed_away = before.loc[before.git_change_type == "R", "previous_file_path"]
    latest = latest[~latest.file_path.isin(renamed_away)]

    return list(latest.file_hash.dropna())  # some renames have no stored content


@cache
def read_file(file_hash):
    with open(CONTEXT_DATA / "context_content" / file_hash, encoding="utf-8", errors="replace") as f:
        return f.read()


def context_text(hashes):
    return "\n".join(read_file(h) for h in hashes)


def load_prs():
    """Agent PRs whose repo had a context file when the PR was opened.

    Columns added: `context_hashes` (context files in effect), `changed_files` / `added_files` (sets, NaN / empty
    if AIDev has no file info), `commit_messages` (first line of each commit message).
    """
    prs = with_repo(aidev("pull_request", ["id", "agent", "title", "state", "created_at", "merged_at", "repo_url", "html_url"]))
    total = len(prs)

    prs["context_hashes"] = [context_files_at(repo, when) for repo, when in zip(prs.repo, prs.created_at)]
    prs = prs[prs.context_hashes.str.len() > 0].copy()
    print(f"{len(prs)} of {total} agent PRs in {prs.repo.nunique()} repos had a context file")

    # pr_commit_details has one row per (commit, changed file)
    files = aidev("pr_commit_details", ["pr_id", "filename", "status"])
    files = files[files.pr_id.isin(prs.id)].dropna()
    prs["changed_files"] = prs.id.map(files.groupby("pr_id").filename.apply(set))
    added_files = files[files.status == "added"].groupby("pr_id").filename.apply(set)
    prs["added_files"] = [added_files.get(pr_id, set()) for pr_id in prs.id]

    commits = aidev("pr_commits", ["pr_id", "message"])
    commits = commits[commits.pr_id.isin(prs.id)].dropna()
    commit_messages = commits.groupby("pr_id").message.apply(lambda msgs: [m.split("\n")[0] for m in msgs])
    prs["commit_messages"] = [commit_messages.get(pr_id, []) for pr_id in prs.id]

    print(prs.changed_files.isna().sum(), "of them have no file info")
    return prs
