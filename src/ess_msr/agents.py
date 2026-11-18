"""Agent detection shared by P1 and P2: which agent tool opened a PR, from provenance signals only (no AI-text classifiers).

Signals mirror what identifies AIDev's agents: bot author accounts, PR body footers/links, and branch prefixes
(branch is not in AIDev, so it only adds recall on P2).
"""

import re

BOT_AUTHORS = {  # agent -> account that opens the PR and authors its commits
    "Copilot": "Copilot",
    "Devin": "devin-ai-integration[bot]",
    "Google_Jules": "google-labs-jules[bot]",
}
BODY_SIGNALS = {
    "Claude_Code": r"Generated with \[?Claude Code|claude\.ai/code",
    "OpenAI_Codex": r"chatgpt\.com/codex",
    "Cursor": r"cursor\.com",
    "Devin": r"app\.devin\.ai",
}
BRANCH_PREFIXES = {"copilot/": "Copilot", "codex/": "OpenAI_Codex", "cursor/": "Cursor", "claude/": "Claude_Code", "devin/": "Devin"}


def detect_agent(author, body="", branch=""):
    """Agent tool name, or None for a (probably) human PR. Bot account wins, then PR body, then branch prefix."""
    body = body if isinstance(body, str) else ""  # missing body is NaN in pandas, null in the API
    branch = branch if isinstance(branch, str) else ""
    for agent, login in BOT_AUTHORS.items():
        if author == login:
            return agent
    for agent, pattern in BODY_SIGNALS.items():
        if re.search(pattern, body, re.IGNORECASE):
            return agent
    for prefix, agent in BRANCH_PREFIXES.items():
        if branch.startswith(prefix):
            return agent
    return None


if __name__ == "__main__":  # uv run python -m ess_msr.agents  -> recall on AIDev P1 (branch unknown there)
    from ess_msr.data import aidev

    prs = aidev("pull_request", ["agent", "user", "body"])
    prs["detected"] = [detect_agent(u, b) for u, b in zip(prs.user, prs.body)]
    print("recall per agent (detected as the right tool):")
    print((prs.detected == prs.agent).groupby(prs.agent).mean().round(3))
    print("detected as a different tool:", ((prs.detected != prs.agent) & prs.detected.notna()).sum())
