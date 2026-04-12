"""Skill exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from openharness.skills.registry import SkillRegistry
    from openharness.skills.types import SkillDefinition

__all__ = [
    "SkillDefinition",
    "SkillRegistry",
    "get_user_skills_dir",
    "load_skill_registry",
    # installer
    "install_skill_from_url",
    "install_skill_from_github",
    "install_popular_skills",
    "uninstall_skill",
    "list_installed_skills",
    "POPULAR_SKILLS",
    # github search
    "search_skills_on_github",
    "search_skill_repos_on_github",
    "fetch_skill_preview",
    "SkillSearchResult",
]


def __getattr__(name: str):
    if name in {"get_user_skills_dir", "load_skill_registry"}:
        from openharness.skills.loader import get_user_skills_dir, load_skill_registry

        return {
            "get_user_skills_dir": get_user_skills_dir,
            "load_skill_registry": load_skill_registry,
        }[name]
    if name == "SkillRegistry":
        from openharness.skills.registry import SkillRegistry

        return SkillRegistry
    if name == "SkillDefinition":
        from openharness.skills.types import SkillDefinition

        return SkillDefinition
    # installer
    if name in {
        "install_skill_from_url",
        "install_skill_from_github",
        "install_popular_skills",
        "uninstall_skill",
        "list_installed_skills",
        "POPULAR_SKILLS",
    }:
        import importlib

        mod = importlib.import_module("openharness.skills.installer")
        return getattr(mod, name)
    # github search
    if name in {
        "search_skills_on_github",
        "search_skill_repos_on_github",
        "fetch_skill_preview",
        "SkillSearchResult",
    }:
        import importlib

        mod = importlib.import_module("openharness.skills.github_search")
        return getattr(mod, name)
    raise AttributeError(name)
