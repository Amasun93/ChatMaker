from __future__ import annotations

import re
from pathlib import Path

import yaml


FRONTMATTER = re.compile(r"\A---\s*\n(?P<yaml>.*?)\n---(?:\s*\n|\Z)", re.DOTALL)


def validate_skill_directory(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_path = skill_dir / "SKILL.md"
    agent_path = skill_dir / "agents" / "openai.yaml"

    if not skill_path.is_file():
        return [f"{skill_dir}: missing SKILL.md"]
    text = skill_path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        return [f"{skill_path}: missing YAML frontmatter"]
    try:
        metadata = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError as exc:
        return [f"{skill_path}: invalid YAML frontmatter: {exc}"]
    if not isinstance(metadata, dict):
        return [f"{skill_path}: frontmatter must be a mapping"]
    if set(metadata) != {"name", "description"}:
        errors.append(f"{skill_path}: frontmatter keys must be exactly name and description")
    name = metadata.get("name")
    if name != skill_dir.name:
        errors.append(f"{skill_path}: name must match directory '{skill_dir.name}'")
    if not isinstance(metadata.get("description"), str) or not metadata["description"].strip():
        errors.append(f"{skill_path}: description must be non-empty text")

    if not agent_path.is_file():
        errors.append(f"{agent_path}: missing UI metadata")
        return errors
    try:
        agent = yaml.safe_load(agent_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"{agent_path}: invalid YAML: {exc}")
        return errors
    interface = agent.get("interface") if isinstance(agent, dict) else None
    if not isinstance(interface, dict):
        errors.append(f"{agent_path}: missing interface mapping")
        return errors
    for field in ("display_name", "short_description", "default_prompt"):
        if not isinstance(interface.get(field), str) or not interface[field].strip():
            errors.append(f"{agent_path}: interface.{field} must be non-empty text")
    if isinstance(name, str) and isinstance(interface.get("default_prompt"), str):
        invocation = f"${name}"
        if invocation not in interface["default_prompt"]:
            errors.append(f"{agent_path}: default_prompt must mention {invocation}")
    return errors

