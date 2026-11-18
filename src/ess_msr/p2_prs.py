"""P2: list the 2026 PRs of the core repos (GitHub API via `gh`) and count agent PRs per tool and repo.

Core repos = P1 repos with the most labelled agent PRs, so RQ4 can compare 2025 vs 2026 within the same repos.
Usable P2 window is Jan-Jun 2026: GHAgentFiles context-file history ends 2026-07-01, and earlier for some repos
(`crawled_until`); PRs after a repo's crawl are counted as `after_crawl`, not used.

    uv run python -m ess_msr.p2_prs
"""

import json
import subprocess

import pandas as pd

from ess_msr.agents import detect_agent
from ess_msr.data import ROOT, context_files_at, crawled_until
from ess_msr.rules import load_labeled, stated_rules

CORE_REPOS = 50
P2_START, CONTEXT_END = "2026-01-01", "2026-07-01"
RAW = ROOT / "data" / "p2" / "raw" / "pulls"


# GraphQL instead of REST `/pulls`: asks only for these fields, ~7x less data per page (REST embeds 2 repo objects per PR)
QUERY = """query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 100, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { endCursor hasNextPage }
      nodes { number title body author { login __typename } headRefName baseRefOid headRefOid
              state isDraft createdAt mergedAt closedAt url }
    }
  }
}"""


def rest_login(author):
    """GraphQL bot logins -> the REST spelling AIDev and `agents.BOT_AUTHORS` use ("devin-ai-integration[bot]")."""
    if author is None:  # deleted account, REST calls it "ghost"
        return "ghost"
    if author["__typename"] != "Bot":
        return author["login"]
    return "Copilot" if author["login"] == "copilot-swe-agent" else author["login"] + "[bot]"


def trim(pr):
    return {
        "number": pr["number"], "title": pr["title"], "body": pr["body"], "user": rest_login(pr["author"]),
        "branch": pr["headRefName"], "base_sha": pr["baseRefOid"], "head_sha": pr["headRefOid"],
        "state": "open" if pr["state"] == "OPEN" else "closed", "draft": pr["isDraft"], "created_at": pr["createdAt"],
        "merged_at": pr["mergedAt"], "closed_at": pr["closedAt"], "html_url": pr["url"],
    }


def list_prs(repo):
    """Every PR of `repo` created since P2_START. Cached as one JSON file per repo, so a rerun resumes."""
    path = RAW / f"{repo.replace('/', '__')}.json"
    if path.exists():
        return json.loads(path.read_text())

    owner, name = repo.split("/")
    rows, cursor = [], None
    while True:
        args = ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"owner={owner}", "-f", f"name={name}"]
        result = subprocess.run(args + (["-f", f"cursor={cursor}"] if cursor else []), capture_output=True, text=True)
        if result.returncode:  # deleted / private repo, network or rate limit: nothing cached, a rerun retries
            print(f"  skipped {repo}: {result.stderr.strip()[:120]}")
            return []
        page = json.loads(result.stdout)["data"]["repository"]["pullRequests"]
        rows += [trim(pr) for pr in page["nodes"] if pr["createdAt"] >= P2_START]
        if not page["pageInfo"]["hasNextPage"] or page["nodes"][-1]["createdAt"] < P2_START:
            break
        cursor = page["pageInfo"]["endCursor"]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows))
    return rows


def main():
    _, pr_rule = load_labeled()
    p1 = pr_rule[pr_rule.label != "not_applicable"].groupby("repo").id.nunique().nlargest(CORE_REPOS)

    rows = []
    for i, repo in enumerate(p1.index, 1):
        repo_prs = list_prs(repo)
        print(f"{i}/{len(p1)} {repo}: {len(repo_prs)} PRs since {P2_START}")
        rows += [dict(pr, repo=repo) for pr in repo_prs]

    prs = pd.DataFrame(rows)
    prs["created_at"] = pd.to_datetime(prs.created_at, utc=True)
    prs["agent"] = [detect_agent(*signals) for signals in zip(prs.user, prs.body, prs.branch)]
    prs["window"] = (prs.created_at < CONTEXT_END).map({True: "jan_jun", False: "jul_on"})

    crawled = prs.repo.map(crawled_until())
    prs.loc[(prs.window == "jan_jun") & (prs.created_at >= crawled), "window"] = "after_crawl"  # context file at that time unknown

    agent = prs[prs.agent.notna()].copy()
    in_window = agent.window == "jan_jun"
    agent["under_rule"] = False
    agent.loc[in_window, "under_rule"] = [
        bool(stated_rules(context_files_at(repo, when)))
        for repo, when in zip(agent.loc[in_window, "repo"], agent.loc[in_window, "created_at"])
    ]

    print("\nAgent PRs per tool (jan_jun = usable window, under_rule = also under one of our 4 rules):")
    print(pd.concat({
        "jan_jun": agent[in_window].groupby("agent").size(),
        "under_rule": agent[agent.under_rule].groupby("agent").size(),
        "after_crawl": agent[agent.window == "after_crawl"].groupby("agent").size(),
        "jul_on": agent[agent.window == "jul_on"].groupby("agent").size(),
    }, axis=1).fillna(0).astype(int).assign(p1_labelled=pr_rule[pr_rule.repo.isin(p1.index)].groupby("agent").id.nunique()))

    per_repo = pd.DataFrame({
        "p1_labelled_prs": p1,
        "p2_agent_prs": agent[in_window].groupby("repo").size(),
        "p2_under_rule": agent[agent.under_rule].groupby("repo").size(),
        "p2_human_prs": prs[prs.agent.isna() & (prs.window == "jan_jun")].groupby("repo").size(),
    }).fillna(0).astype(int)
    print("\nPer repo (Jan-Jun 2026):")
    print(per_repo.sort_values("p2_under_rule", ascending=False).to_string())
    print(f"\nRepos with >= 10 P2 agent PRs under a rule: {(per_repo.p2_under_rule >= 10).sum()} of {len(per_repo)}")


if __name__ == "__main__":
    main()
