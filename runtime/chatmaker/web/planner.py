from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any

from .directions import DesignDirection, suggest_directions


@dataclass(frozen=True)
class CreativeBrief:
    kind: str
    idea: str = ""
    audience_scene: str = ""
    desired_feeling: str = ""
    core_message: str = ""
    primary_action: str = ""


@dataclass(frozen=True)
class CreativeBriefPlan:
    status: str
    questions: tuple[str, ...]
    directions: tuple[DesignDirection, ...]
    advanced: bool


def _clean(value: str) -> str:
    return value.strip()


def _missing_questions(brief: CreativeBrief) -> list[str]:
    questions: list[str] = []
    if not _clean(brief.idea):
        questions.append("你希望这个网页具体帮助大家完成什么？")
    if not _clean(brief.audience_scene):
        questions.append("谁会在什么场景里使用这个网页？")
    if not (_clean(brief.desired_feeling) or _clean(brief.core_message)):
        questions.append("你希望它让人感到什么，或最想传达哪句话？")
    if not _clean(brief.primary_action):
        questions.append("使用者最重要的一次操作是什么？")
    return questions


def plan_creative_brief(
    brief: CreativeBrief,
    *,
    advanced: bool = False,
) -> CreativeBriefPlan:
    questions = _missing_questions(brief)
    if questions:
        return CreativeBriefPlan(
            status="clarify",
            questions=tuple(questions[:2]),
            directions=(),
            advanced=advanced,
        )

    desired = brief.desired_feeling or brief.core_message
    return CreativeBriefPlan(
        status="directions",
        questions=(),
        directions=tuple(
            suggest_directions(
                brief.kind,
                desired_feeling=desired,
                advanced=advanced,
            )
        ),
        advanced=advanced,
    )


def _brief_from_json(value: str) -> CreativeBrief:
    payload: dict[str, Any] = json.loads(value)
    return CreativeBrief(**payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clarify a ChatWeb creative brief and return curated directions."
    )
    parser.add_argument("--brief-json", required=True)
    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Explicitly include the expanded direction catalog.",
    )
    args = parser.parse_args()
    result = plan_creative_brief(_brief_from_json(args.brief_json), advanced=args.advanced)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
