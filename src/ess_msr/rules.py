"""Which rules a context file states, and whether a PR complied with them (see `README.md` §2).

Each checker gets one (PR, rule) row and returns `not_applicable`, `complied` or `violated`.
Checkers are lenient on purpose: we would rather miss a violation than invent one.
"""

import re
from functools import cache

from ess_msr import data
from ess_msr.data import context_text

# ---------------------------------------------------------------------------------------------------------------------
# Rule detection: simple keyword regexes per rule. They have false positives; validated by hand (validation.ipynb).

MANAGER = r"`?(pnpm|yarn|bun|uv|poetry)`?(?:\s*\([^)]*\))?"  # optional "(v9+)" after the name
PACKAGE_MANAGER_PHRASES = [
    rf"\b(?:use|using|prefer)\s+{MANAGER}\s+(?:as|for)\s+(?:the\s+|our\s+|your\s+)?(?:package|dependenc|js\b|javascript|node|python)",  # use pnpm as the package manager
    rf"\b(?:use|using)\s+{MANAGER}\s+(?:only|exclusively)\b",  # use yarn exclusively
    rf"\bonly\s+use\s+{MANAGER}",  # only use bun
    rf"\b(?:use|run)\s+`?(pnpm|yarn|bun|uv|poetry)\s+(?:install|add|sync)\b",  # use `pnpm install`
    rf"package\s+manager\b[\s*:`_-]*(?:is\s+|use\s+)?{MANAGER}",  # **Package manager**: uv
    rf"package\s+manager,\s+use\s+{MANAGER}",  # ...need a package manager, use pnpm
    rf"{MANAGER}[\s*:_-]+package\s+manager",  # **PNPM**: Package manager
    rf"{MANAGER}\s+is\s+(?:the|our)\b[^.\n]{{0,20}}package\s+manager",  # pnpm is the project's package manager
]

# `^(?!.*X)` means "the line does not contain X"
RULE_PATTERNS = {
    "commit_format": r"^(?!.*\b(do not|don't|never|consider|encouraged|optional|when possible|if possible|when reasonable)\b).*conventional commits?",
    "required_tests": (
        r"\b(must|should|always|required?)\b[^.\n]*\b(add|write|include|accompanied)\b[^.\n]{0,30}\btests?\b"
        r"|\b(add|write|include)\b[^.\n]{0,30}\btests?\b[^.\n]*\b(whenever|for (any|every|all|new))\b"
    ),
    "package_manager": "|".join(PACKAGE_MANAGER_PHRASES),
    "changelog": r"^(?!.*\brelease).*\b(update|add|edit)\b[^.\n]{0,40}\bchangelog\b",
}

# Lines that match a pattern but are not a rule for every PR (found in hand validation)
RELEASE_HEADING = r"\b(releas\w*|publish\w*|deploy\w*|version bump)\b"
NOT_A_RULE = (
    r"\b(if the user|if applicable|where applicable|when applicable|if needed|if necessary|when appropriate"
    r"|if possible|consider|for doc(umentation)? changes)\b"
    r"|same directory|next to|alongside|\bnam(ed|ing)\b|\blocated\b"  # where tests go, not that they are required
    r"|\b(pr|pull request) (description|template|body)\b"  # changelog section of the PR text, not a file
    r"|/changelog/"  # link to a changelog page, e.g. "[Update Indicator](/changelog/2024-06-10-...)"
)
FILTERED_RULES = {"required_tests", "changelog"}


@cache
def rule_units(hashes, rule):
    """Matching lines of `rule` (joined with the lines they continue), minus release steps and conditional lines."""
    units, heading, previous = [], "", ""
    for line in context_text(hashes).splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped
        unit = f"{previous} {stripped}" if stripped[:1].islower() else stripped  # wrapped sentence
        previous = unit if stripped else ""
        if not re.search(RULE_PATTERNS[rule], stripped, re.IGNORECASE):
            continue
        if rule in FILTERED_RULES and (
            re.search(RELEASE_HEADING, heading, re.IGNORECASE) or re.search(NOT_A_RULE, unit, re.IGNORECASE)
        ):
            continue
        units.append(unit)
    return tuple(units)


def stated_rules(hashes):
    hashes = tuple(hashes)
    return [rule for rule in RULE_PATTERNS if rule_units(hashes, rule)]


# ---------------------------------------------------------------------------------------------------------------------
# Commit / PR title format: complied if the PR title or any commit message follows Conventional Commits.

# "type(scope)!: description" - the spec allows any type word (repos add their own, e.g. "k8s:")
CONVENTIONAL_TITLE = r"^[\w,-]+(\(.+\))?!?: .+"


def follows_format(text):
    text = re.sub(r"^\[[^\]]*\]\s*", "", text.strip())  # "[alpha_factory] feat: ..."
    text = re.sub(r"^[^\w(\[]+", "", text)  # emoji conventional commits: "🐛 fix: ..."
    return re.match(CONVENTIONAL_TITLE, text, re.IGNORECASE) is not None


def check_commit_format(pr):
    if follows_format(pr.title) or any(follows_format(m) for m in pr.commit_messages):
        return "complied"
    return "violated"


# ---------------------------------------------------------------------------------------------------------------------
# Package manager
# 1. Read which manager(s) the context file asks for (e.g. `pnpm`).
# 2. The rule applies only if the PR changed a lockfile of the same ecosystem (JS or Python).
# 3. Violated if the PR *added a new* lockfile of a different manager (e.g. a new `package-lock.json` when pnpm is
#    required). Editing a wrong lockfile that already existed is not counted: some sub-packages legitimately use another.
# 4. Lockfiles inside `test/`, `fixtures/`, `examples/` folders are ignored (sample projects).

LOCKFILE_MANAGER = {
    "package-lock.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "bun.lock": "bun",
    "bun.lockb": "bun",
    "uv.lock": "uv",
    "poetry.lock": "poetry",
}
ECOSYSTEM = {"npm": "js", "pnpm": "js", "yarn": "js", "bun": "js", "uv": "python", "poetry": "python"}

IGNORED_FOLDERS = {"test", "tests", "fixtures", "__fixtures__", "example", "examples"}


def required_managers(text):
    found = set()
    for phrase in PACKAGE_MANAGER_PHRASES:
        found |= {name.lower() for name in re.findall(phrase, text, re.IGNORECASE)}
    return found


def in_ignored_folder(path):
    folders = path.lower().split("/")[:-1]
    return any(folder in IGNORED_FOLDERS for folder in folders)


def lockfile_managers(file_paths, ecosystems):
    managers = {LOCKFILE_MANAGER.get(path.split("/")[-1]) for path in file_paths if not in_ignored_folder(path)}
    return {m for m in managers if m and ECOSYSTEM[m] in ecosystems}


def check_package_manager(pr, required=None):
    """`required` overrides the managers read from the PR's context files (RQ2 passes the repo's rule)."""
    required = required_managers(context_text(pr.context_hashes)) if required is None else required
    ecosystems = {ECOSYSTEM[m] for m in required}

    changed = lockfile_managers(pr.changed_files, ecosystems)
    added = lockfile_managers(pr.added_files, ecosystems)

    if added - required:
        return "violated"
    if changed and changed <= required:
        return "complied"
    return "not_applicable"


# ---------------------------------------------------------------------------------------------------------------------
# Required tests: applies if the PR changed a source file (and the rule's scope covers the PR);
# complied if it also changed a test file, otherwise violated.

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb", ".php",
    ".cs", ".c", ".cpp", ".h", ".swift", ".scala", ".dart", ".vue", ".svelte",
}

TEST_PATH = (
    r"(?i:(^|/)([\w-]+\.)*(unit|integration|e2e|functional)?(tests?|__tests__|specs?)/)"  # test folder: tests/, src/test/, Build.UnitTests/
    r"|(^|/)test_[^/]*$"  # test_ prefix:            test_foo.py
    r"|(?i:[._-](test|spec)s?\.[a-z]+$)"  # test/spec suffix:        foo_test.go, foo.test.ts, Foo_Tests.cs
    r"|[a-z0-9]Tests?\.[a-z]+$"  # CamelCase suffix:        FooTest.java, FooTests.cs
)

LOCKFILES = r"(^|/)([^/]+\.lock|package-lock\.json|pnpm-lock\.yaml|bun\.lockb)$"


def is_test_file(path):
    return re.search(TEST_PATH, path) is not None and re.search(LOCKFILES, path) is None


def is_source_file(path):
    extension = "." + path.split(".")[-1].lower() if "." in path else ""
    return extension in SOURCE_EXTENSIONS and not is_test_file(path)


CONVENTIONAL_KIND = {"feat": "feature", "fix": "fix", "docs": "docs"}  # other types (refactor, chore, ...) -> "other"
DOCS_WORDS = r"\b(docs?|docstrings?|jsdoc|documentation|typos?|readme)\b"
FIRST_WORD_KIND = {
    "fix": r"fix\w*|resolve\w*|bug\w*|correct\w*|patch\w*|prevent\w*|handle\w*",
    "other": r"refactor\w*|renam\w*|move\w*|clean\w*|remov\w*|delet\w*|bump\w*|upgrad\w*|updat\w*|chore|revert\w*"
             r"|migrat\w*|convert\w*|format\w*|lint\w*|optimi[sz]\w*|improv\w*|simplif\w*",
    "feature": r"add\w*|implement\w*|support\w*|introduc\w*|creat\w*|enabl\w*|allow\w*|new|feat\w*|build\w*",
}


def pr_kind(title):
    """feature / fix / docs / other / unknown, from the PR title only."""
    title = re.sub(r"^\[[^\]]*\]\s*|^[^\w(\[]+", "", title.strip()).lower()
    conventional = re.match(r"^(\w+)(\(.+?\))?!?:", title)
    if conventional:
        return CONVENTIONAL_KIND.get(conventional.group(1), "other")
    if re.search(DOCS_WORDS, title) or title.startswith("document"):
        return "docs"
    for kind, words in FIRST_WORD_KIND.items():
        if re.match(rf"({words})\b", title):
            return kind
    return "unknown"


LANGUAGE_EXTENSIONS = {
    "python": {".py"}, "typescript": {".ts", ".tsx"}, "javascript": {".js", ".jsx"}, "rust": {".rs"},
    "java": {".java"}, "kotlin": {".kt"}, "ruby": {".rb"}, "php": {".php"}, "swift": {".swift"},
}


def applies_to(unit, kind, changed_files):
    """Does one rule sentence cover this PR? Lenient: unclear cases do not apply."""
    languages = [lang for lang in LANGUAGE_EXTENSIONS if re.search(rf"\b{lang}\b", unit, re.IGNORECASE)]
    if languages:
        extensions = set().union(*(LANGUAGE_EXTENSIONS[lang] for lang in languages))
        if not any(("." + f.rsplit(".", 1)[-1].lower()) in extensions for f in changed_files if "." in f):
            return False
    if kind == "docs":
        return False
    only_new = re.search(r"\bnew\s+(\w+\s+)?(features?|functionality|code|endpoints?|algorithms?|apis?|modules?|components?|functions?|logic)\b|\bfeatures?\b|\bfunctionality\b|\bsignificant\b|\bnotable\b|user[- ]facing", unit, re.IGNORECASE)
    covers_fixes = re.search(r"\bbugs?\b|\bfix", unit, re.IGNORECASE)
    if only_new:
        return kind == "feature" or (kind == "fix" and covers_fixes is not None)
    return True


def rule_applies(pr, rule, units=None):
    units = rule_units(tuple(pr.context_hashes), rule) if units is None else units
    kind = pr_kind(pr.title)
    return any(applies_to(unit, kind, pr.changed_files) for unit in units)


def check_required_tests(pr, units=None):
    """`units` overrides the rule sentences read from the PR's context files (RQ2 passes the repo's rule)."""
    if not any(is_source_file(f) for f in pr.changed_files):
        return "not_applicable"
    if not rule_applies(pr, "required_tests", units):
        return "not_applicable"
    if any(is_test_file(f) for f in pr.changed_files):
        return "complied"
    return "violated"


# ---------------------------------------------------------------------------------------------------------------------
# Changelog: applies if the PR changed a source file (and the rule's scope covers the PR); complied if it changed a
# changelog file (`CHANGELOG.md`, `docs/changelog/...`) or a changeset (`.changeset/*.md`), otherwise violated.

CHANGELOG_PATH = r"changelog|(^|/)\.changeset/|(^|/)changes\.md$"


def only_when_file_changes(unit, changed_files):
    """'Whenever `foo.py` is modified, ... changelog' -> applies only if foo.py changed."""
    if not re.search(r"\b(whenever|when|if)\b", unit, re.IGNORECASE):
        return True
    files = re.findall(r"`([\w./-]+\.\w+)`", unit)
    files = [f for f in files if not re.search(CHANGELOG_PATH, f, re.IGNORECASE)]
    return not files or any(path.endswith(f) for f in files for path in changed_files)


def check_changelog(pr, units=None):
    if not any(is_source_file(f) for f in pr.changed_files):
        return "not_applicable"
    units = rule_units(tuple(pr.context_hashes), "changelog") if units is None else units
    units = [u for u in units if only_when_file_changes(u, pr.changed_files)]
    if not rule_applies(pr, "changelog", units):
        return "not_applicable"
    changelog_path = CHANGELOG_PATH + ("|(^|/)readme\\.md$" if any(re.search(r"readme", u, re.IGNORECASE) for u in units) else "")
    if any(re.search(changelog_path, f, re.IGNORECASE) for f in pr.changed_files):
        return "complied"
    return "violated"


# ---------------------------------------------------------------------------------------------------------------------

CHECKERS = {
    "commit_format": check_commit_format,
    "package_manager": check_package_manager,
    "required_tests": check_required_tests,
    "changelog": check_changelog,
}


def label(prs):
    """One row per (PR, stated rule) with the checker's `label`. PRs without file info are dropped."""
    pr_rule = prs.explode("rules", ignore_index=True).dropna(subset=["rules"])
    pr_rule = pr_rule[pr_rule.rules.isin(CHECKERS) & pr_rule.changed_files.notna()].copy()
    pr_rule["label"] = [CHECKERS[row.rules](row) for row in pr_rule.itertuples()]
    return pr_rule


def load_labeled():
    """`prs` (P1 agent PRs + the `rules` their context files state) and `pr_rule` (every labelled (PR, rule) pair)."""
    prs = data.load_prs()
    prs["rules"] = prs.context_hashes.apply(stated_rules)
    return prs, label(prs)


if __name__ == "__main__":  # uv run python -m ess_msr.rules
    from types import SimpleNamespace as PR

    assert check_commit_format(PR(title="[alpha_factory] add x", commit_messages=["feat: add x"])) == "complied"
    assert check_commit_format(PR(title="🐛 fix: crash", commit_messages=[])) == "complied"
    assert check_commit_format(PR(title="Add sidebar", commit_messages=["Initial plan"])) == "violated"

    assert required_managers("Use pnpm as the package manager. Run `uv sync` first.") == {"pnpm", "uv"}
    assert required_managers("Use `yarn validate` before pushing") == set()
    pnpm_pr = PR(changed_files={"package-lock.json"}, added_files={"package-lock.json"})
    assert check_package_manager(pnpm_pr, {"pnpm"}) == "violated"
    assert check_package_manager(PR(changed_files={"examples/a/package-lock.json"}, added_files={"examples/a/package-lock.json"}), {"pnpm"}) == "not_applicable"

    assert [is_test_file(f) for f in ["tests/test_app.py", "pkg/x_test.go", "src/FooTest.java", "Foo.UnitTests/A.cs", "tests/uv.lock"]] == [True] * 4 + [False]
    assert [is_source_file(f) for f in ["src/app.py", "tests/test_app.py", "README.md"]] == [True, False, False]
    assert [pr_kind(t) for t in ["feat: x", "Fix crash", "Update docs", "Add login", "Bump deps", "Hello"]] == ["feature", "fix", "docs", "feature", "other", "unknown"]

    new_features_only = ("Always add tests for new features",)
    assert check_required_tests(PR(title="Add login", changed_files={"src/app.py"}), new_features_only) == "violated"
    assert check_required_tests(PR(title="Fix crash", changed_files={"src/app.py"}), new_features_only) == "not_applicable"
    assert check_changelog(PR(title="Add x", changed_files={"src/a.ts", "CHANGELOG.md"}), ("Update CHANGELOG.md",)) == "complied"
    print("ok")
