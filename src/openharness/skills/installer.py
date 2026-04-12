"""Skill installation helpers – install from URL, GitHub repo, or popular presets."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Popular skills – each entry is (slug, raw_url_or_None, description).
# If raw_url is None the skill is synthesised from the bundled content.
# Real remote entries point at publicly accessible raw GitHub URLs.
# ---------------------------------------------------------------------------


class _PopularSkill(NamedTuple):
    slug: str          # directory name under ~/.openharness/skills/<slug>/
    raw_url: str | None  # GitHub raw content URL, or None → use bundled content
    description: str   # one-liner shown during install


# ---------------------------------------------------------------------------
# The list below is ordered: bundled-copy entries first (always available),
# then remote entries that require network access.
# ---------------------------------------------------------------------------

POPULAR_SKILLS: list[_PopularSkill] = [
    # ── Available locally (derived from bundled skills) ──────────────────
    _PopularSkill(
        slug="code-review",
        raw_url=None,
        description="Deep code-review: logic, security, style (bundled)",
    ),
    _PopularSkill(
        slug="test-writer",
        raw_url=None,
        description="Generate pytest / jest unit tests (bundled)",
    ),
    _PopularSkill(
        slug="docstring",
        raw_url=None,
        description="Add / update docstrings and type hints (bundled)",
    ),
    _PopularSkill(
        slug="refactor",
        raw_url=None,
        description="Safe, incremental code refactoring (bundled)",
    ),
    _PopularSkill(
        slug="pr-description",
        raw_url=None,
        description="Write detailed pull-request descriptions (bundled)",
    ),
    # ── Remote entries – from real public GitHub repositories ─────────────
    # (Add verified remote skill URLs here as the community grows)
]

# ---------------------------------------------------------------------------
# Synthesised SKILL.md templates for bundled-copy entries
# (written when raw_url is None)
# ---------------------------------------------------------------------------

_BUNDLED_TEMPLATES: dict[str, str] = {
    "code-review": """\
---
name: code-review
description: Deep code-review covering logic, security, and style.
---

# code-review

Perform a thorough code review.

## When to use

Use when asked to review, audit, or critique a diff or file.

## Workflow

1. Read every changed file fully – never review code you haven't read.
2. Check **logic**: off-by-one errors, null dereferences, race conditions.
3. Check **security**: injection, auth bypass, secrets in code, OWASP Top 10.
4. Check **style**: naming, duplication, dead code, overly complex expressions.
5. Check **tests**: are edge cases covered? Are there missing assertions?
6. Summarise findings grouped by severity: 🔴 critical / 🟡 warning / 🔵 suggestion.

## Rules

- Be specific: include file path and line number for every finding.
- Do not nitpick minor whitespace or personal-preference style issues.
- Suggest a concrete fix for each critical or warning finding.
""",
    "test-writer": """\
---
name: test-writer
description: Generate comprehensive unit and integration tests.
---

# test-writer

Generate well-structured tests for the given code.

## When to use

Use when asked to add tests, improve coverage, or test a specific function/module.

## Workflow

1. Read the target source file(s) completely.
2. Identify all public functions, classes, and edge cases.
3. Choose the right test framework (pytest for Python, jest/vitest for JS/TS, etc.).
4. Write tests that cover:
   - Happy path
   - Boundary values / edge cases
   - Expected errors and exceptions
   - Any async or concurrent behaviour
5. Prefer small, focused tests with descriptive names.

## Rules

- Never mock what you can test directly.
- Use fixtures / factories to avoid repetition.
- Each test should have a single assertion focus.
""",
    "docstring": """\
---
name: docstring
description: Add or update docstrings and type hints.
---

# docstring

Add clear, concise docstrings and type annotations.

## When to use

Use when asked to document code, add type hints, or improve readability.

## Workflow

1. Read the file(s) to be documented.
2. For every public function / class / method:
   - Add a one-line summary.
   - Add `Args` / `Returns` / `Raises` sections where non-obvious.
   - Add type hints to parameters and return values.
3. Follow the project's existing docstring style (Google, NumPy, or reST).
4. Do not add docstrings to trivial private helpers unless they are complex.

## Rules

- Keep summaries under 80 characters.
- Do not repeat the function name in the docstring.
- Prefer inline types over docstring-only type documentation in Python 3.9+.
""",
    "refactor": """\
---
name: refactor
description: Safe, incremental code refactoring.
---

# refactor

Improve code quality without changing observable behaviour.

## When to use

Use when asked to refactor, clean up, or simplify code.

## Workflow

1. Read the code to be refactored completely.
2. Run existing tests first to establish a baseline.
3. Apply one refactoring at a time:
   - Extract repeated logic into functions/classes.
   - Simplify conditionals (early returns, guard clauses).
   - Replace magic numbers/strings with named constants.
   - Remove dead code.
4. Re-run tests after each change to confirm nothing broke.
5. Summarise what was changed and why.

## Rules

- Never change behaviour while refactoring.
- Prefer small, reviewable commits.
- Do not refactor code that is not covered by tests without flagging the risk.
""",
    "pr-description": """\
---
name: pr-description
description: Write detailed, informative pull-request descriptions.
---

# pr-description

Generate a clear and complete PR description from code changes.

## When to use

Use when asked to write, improve, or fill in a pull-request description.

## Workflow

1. Run `git log` and `git diff` (or read the provided diff).
2. Identify the type of change: feature / bug-fix / refactor / docs / chore.
3. Write a PR description with the following sections:
   - **Summary** – one paragraph explaining *what* changed and *why*.
   - **Changes** – bullet list of specific changes.
   - **Testing** – how the change was tested.
   - **Screenshots / recordings** (if UI changes).
   - **Related issues** – link to issues if available.

## Rules

- Be specific; avoid vague descriptions like "fix bug" or "update code".
- Use present tense ("Add …", "Fix …", "Remove …").
- Mention any breaking changes explicitly.
""",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_user_skills_dir() -> Path:
    """Return (and create) the user skills directory."""
    from openharness.config.paths import get_config_dir

    path = get_config_dir() / "skills"
    path.mkdir(parents=True, exist_ok=True)
    return path


def install_skill_from_url(url: str, slug: str | None = None) -> Path:
    """Download a SKILL.md from *url* and install it into the user skills dir.

    Parameters
    ----------
    url:
        A raw HTTP(S) URL pointing to a ``SKILL.md`` file.
    slug:
        Optional directory name.  Defaults to the last non-empty path segment
        before ``SKILL.md`` in the URL, or the URL hostname fragment.

    Returns
    -------
    Path
        The installed skill directory.
    """
    import urllib.request

    if slug is None:
        slug = _slug_from_url(url)

    dest_dir = get_user_skills_dir() / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "SKILL.md"

    logger.debug("Downloading skill %r from %s", slug, url)
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "OpenHarness-SkillInstaller/1.0")
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            content = resp.read().decode("utf-8")
    except Exception as exc:
        raise RuntimeError(f"Failed to download skill from {url}: {exc}") from exc

    dest_file.write_text(content, encoding="utf-8")
    logger.info("Installed skill %r → %s", slug, dest_file)
    return dest_dir


def _install_skill_from_template(slug: str, content: str) -> Path:
    """Write a skill from an in-process template string."""
    dest_dir = get_user_skills_dir() / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "SKILL.md"
    dest_file.write_text(content, encoding="utf-8")
    logger.info("Installed bundled-template skill %r → %s", slug, dest_file)
    return dest_dir


def install_skill_from_github(
    owner: str,
    repo: str,
    path: str = "SKILL.md",
    *,
    ref: str = "main",
    slug: str | None = None,
) -> Path:
    """Install a skill from a GitHub repository path.

    Parameters
    ----------
    owner / repo:
        GitHub repository coordinates.
    path:
        Path inside the repository to the ``SKILL.md`` file.
    ref:
        Branch or tag (default: ``main``).
    slug:
        Local directory name; defaults to *repo*.
    """
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    return install_skill_from_url(url, slug=slug or repo)


def install_popular_skills(
    *,
    progress_cb=None,
) -> list[tuple[str, bool, str]]:
    """Install all skills in :data:`POPULAR_SKILLS`.

    Parameters
    ----------
    progress_cb:
        Optional callback ``(slug, success, message)`` called after each
        install attempt.

    Returns
    -------
    list[tuple[str, bool, str]]
        ``(slug, success, message)`` for every skill.
    """
    results: list[tuple[str, bool, str]] = []
    for skill in POPULAR_SKILLS:
        try:
            if skill.raw_url is None:
                # Use in-process template
                template = _BUNDLED_TEMPLATES.get(skill.slug)
                if template:
                    _install_skill_from_template(skill.slug, template)
                    msg = f"✓ {skill.slug} — {skill.description}"
                    ok = True
                else:
                    msg = f"✗ {skill.slug} — no template available"
                    ok = False
            else:
                install_skill_from_url(skill.raw_url, slug=skill.slug)
                msg = f"✓ {skill.slug} — {skill.description}"
                ok = True
        except Exception as exc:
            msg = f"✗ {skill.slug} — {exc}"
            ok = False
        results.append((skill.slug, ok, msg))
        if progress_cb is not None:
            progress_cb(skill.slug, ok, msg)
    return results


def uninstall_skill(name: str) -> bool:
    """Remove a user skill directory.

    Returns ``True`` if the skill was found and removed.
    """
    path = get_user_skills_dir() / name
    if not path.exists():
        return False
    shutil.rmtree(path)
    logger.info("Uninstalled skill %r", name)
    return True


def list_installed_skills() -> list[dict]:
    """Return a list of installed user skills as dicts with ``name`` and ``path``."""
    skills_dir = get_user_skills_dir()
    result = []
    for child in sorted(skills_dir.iterdir()):
        if child.is_dir():
            skill_file = child / "SKILL.md"
            if skill_file.exists():
                result.append({"name": child.name, "path": str(skill_file)})
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slug_from_url(url: str) -> str:
    """Derive a skill slug from a URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p and p.upper() != "SKILL.MD"]
    if parts:
        return parts[-1]
    return parsed.netloc.replace(".", "-") or "skill"

