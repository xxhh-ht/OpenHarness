"""GitHub skill discovery – search for SKILL.md files across public repositories."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_GITHUB_API_BASE = "https://api.github.com"
_SEARCH_CODE_URL = f"{_GITHUB_API_BASE}/search/code"
_SEARCH_REPOS_URL = f"{_GITHUB_API_BASE}/search/repositories"

# GitHub code-search query that looks for SKILL.md files
_SKILL_FILENAME = "SKILL.md"


@dataclass
class SkillSearchResult:
    """A skill discovered on GitHub."""

    name: str
    """Skill slug / directory name (derived from path)."""
    repo: str
    """Full repo name, e.g. ``owner/repo``."""
    path: str
    """Path inside the repo to the SKILL.md file."""
    raw_url: str
    """GitHub raw content URL for direct download."""
    html_url: str
    """GitHub web URL."""
    description: str = ""
    """Repository description or skill description extracted from content."""
    stars: int = 0
    """Repository star count."""
    topics: list[str] = field(default_factory=list)
    """Repository topics."""

    @property
    def install_slug(self) -> str:
        """Return a safe local directory name for this skill."""
        parts = [p for p in self.path.split("/") if p and p.upper() != "SKILL.MD"]
        if parts:
            return parts[-1]
        # Fall back to repo name without owner
        return self.repo.split("/")[-1]


def search_skills_on_github(
    query: str,
    *,
    token: str | None = None,
    max_results: int = 20,
) -> list[SkillSearchResult]:
    """Search GitHub for SKILL.md files matching *query*.

    Uses the GitHub code-search API:
    ``filename:SKILL.md <query>``

    Parameters
    ----------
    query:
        Free-text search query (e.g. ``"code review python"``).
    token:
        Optional GitHub personal access token for higher rate limits.
    max_results:
        Maximum number of results to return (capped at 30 by GitHub's API
        without authentication).

    Returns
    -------
    list[SkillSearchResult]
        Sorted by repository star count (descending).
    """
    full_query = f"filename:{_SKILL_FILENAME} {query}"
    params = urllib.parse.urlencode({"q": full_query, "per_page": min(max_results, 30)})
    url = f"{_SEARCH_CODE_URL}?{params}"

    data = _github_get(url, token=token)
    items: list[Any] = data.get("items", [])

    results: list[SkillSearchResult] = []
    seen_repos: dict[str, dict] = {}

    for item in items:
        repo_data = item.get("repository", {})
        repo_full = repo_data.get("full_name", "")
        path = item.get("path", _SKILL_FILENAME)
        html_url = item.get("html_url", "")

        # Build raw URL
        raw_url = _to_raw_url(repo_full, path)

        # Fetch extra repo metadata (stars, description) – cached per repo
        if repo_full not in seen_repos:
            seen_repos[repo_full] = _fetch_repo_meta(repo_full, token=token)
        meta = seen_repos[repo_full]

        results.append(
            SkillSearchResult(
                name=_derive_name(path, repo_full),
                repo=repo_full,
                path=path,
                raw_url=raw_url,
                html_url=html_url,
                description=meta.get("description") or repo_data.get("description") or "",
                stars=meta.get("stargazers_count", 0),
                topics=meta.get("topics", []),
            )
        )

    results.sort(key=lambda r: r.stars, reverse=True)
    return results[:max_results]


def search_skill_repos_on_github(
    query: str,
    *,
    token: str | None = None,
    max_results: int = 10,
) -> list[SkillSearchResult]:
    """Search GitHub *repositories* that contain skills matching *query*.

    Uses the repository search API with topic and keyword filters.
    Useful for discovering skill packs / collections.
    """
    full_query = f"{query} topic:openharness-skills"
    params = urllib.parse.urlencode({
        "q": full_query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(max_results, 30),
    })
    url = f"{_SEARCH_REPOS_URL}?{params}"

    try:
        data = _github_get(url, token=token)
    except Exception:
        # Fallback: search without topic constraint
        params = urllib.parse.urlencode({
            "q": f"{query} skills SKILL.md in:readme",
            "sort": "stars",
            "order": "desc",
            "per_page": min(max_results, 30),
        })
        data = _github_get(f"{_SEARCH_REPOS_URL}?{params}", token=token)

    results: list[SkillSearchResult] = []
    for item in (data.get("items") or []):
        full_name = item.get("full_name", "")
        if not full_name:
            continue
        results.append(
            SkillSearchResult(
                name=full_name.split("/")[-1],
                repo=full_name,
                path=_SKILL_FILENAME,
                raw_url=_to_raw_url(full_name, _SKILL_FILENAME),
                html_url=item.get("html_url", ""),
                description=item.get("description") or "",
                stars=item.get("stargazers_count", 0),
                topics=item.get("topics") or [],
            )
        )

    return results[:max_results]


def fetch_skill_preview(raw_url: str, *, token: str | None = None, max_chars: int = 500) -> str:
    """Fetch the first *max_chars* of a remote SKILL.md for preview."""
    try:
        req = urllib.request.Request(raw_url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "text/plain")
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            content = resp.read(max_chars).decode("utf-8", errors="replace")
        return content
    except Exception as exc:
        logger.debug("Failed to fetch skill preview from %s: %s", raw_url, exc)
        return ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _github_get(url: str, *, token: str | None = None) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "OpenHarness-SkillSearch/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API error {exc.code} for {url}: {body[:200]}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Network error fetching {url}: {exc}") from exc


def _fetch_repo_meta(full_name: str, *, token: str | None = None) -> dict:
    url = f"{_GITHUB_API_BASE}/repos/{full_name}"
    try:
        return _github_get(url, token=token)
    except Exception:
        return {}


def _to_raw_url(full_name: str, path: str, ref: str = "main") -> str:
    return f"https://raw.githubusercontent.com/{full_name}/{ref}/{path}"


def _derive_name(path: str, repo_full: str) -> str:
    parts = [p for p in path.split("/") if p and p.upper() != "SKILL.MD"]
    if parts:
        return parts[-1]
    return repo_full.split("/")[-1]
