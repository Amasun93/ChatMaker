from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:  # Allow direct execution from a checked-out release folder.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _has_hardware_intent(request: dict[str, Any]) -> bool:
    hardware = request.get("hardware")
    return isinstance(hardware, dict) and any(hardware.values())


def _has_web_intent(request: dict[str, Any]) -> bool:
    web = request.get("web")
    return isinstance(web, dict) and any(web.values())


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_contract_transport(contract: Any) -> bool:
    return isinstance(contract, dict) and _is_nonempty_string(contract.get("transport"))


def _has_contract_interaction(contract: Any) -> bool:
    if not isinstance(contract, dict):
        return False
    interactions = contract.get("interactions")
    if not isinstance(interactions, list):
        return False
    for interaction in interactions:
        if not isinstance(interaction, dict):
            continue
        has_request_response = _is_nonempty_string(
            interaction.get("request")
        ) and _is_nonempty_string(interaction.get("response"))
        has_message = _is_nonempty_string(interaction.get("message"))
        if has_request_response or has_message:
            return True
    return False


def chatweb_llmwiki_requests_for_intent(
    request: dict[str, Any],
    *,
    board_id: str,
) -> list[dict[str, str]]:
    if not _has_web_intent(request) or not _has_hardware_intent(request):
        return []
    return [
        {
            "action": "section",
            "board_id": board_id,
            "consumer": "chatweb",
            "section_id": "web-and-protocol",
        }
    ]


def route_project_intent(request: dict[str, Any]) -> dict[str, Any]:
    has_hardware = _has_hardware_intent(request)
    has_web = _has_web_intent(request)

    if has_hardware and has_web:
        contract = request.get("communication_contract")
        requirements: list[str] = []
        if not _has_contract_transport(contract):
            requirements.append("transport")
        if not _has_contract_interaction(contract):
            requirements.append("request_response_or_message_interaction")
        success = not requirements
        result = {
            "success": success,
            "route": "combined",
            "status": "ready" if success else "blocked",
            "stage": "routed" if success else "planning",
            "specialists": ["chatduino", "chatweb"],
            "contract_requirements": requirements,
            "evidence_boundaries": {
                "page_rendering_is_web_only": True,
                "hardware_effect_requires_separate_verification": True,
            },
        }
        if not success:
            result["missing"] = requirements
        return result

    if has_hardware:
        return {
            "success": True,
            "route": "hardware",
            "status": "ready",
            "stage": "routed",
            "specialists": ["chatduino"],
            "contract_requirements": [],
        }

    if has_web:
        return {
            "success": True,
            "route": "web",
            "status": "ready",
            "stage": "routed",
            "specialists": ["chatweb"],
            "contract_requirements": [],
        }

    return {
        "success": False,
        "route": "clarify",
        "status": "blocked",
        "stage": "clarify",
        "specialists": [],
        "contract_requirements": [],
        "missing": ["hardware_or_web_outcome"],
    }


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    return route_project_intent(request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route structured ChatMaker project intent.")
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request_json)
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        result = execute_request(request)
    except Exception as exc:
        result = {
            "success": False,
            "route": "clarify",
            "status": "blocked",
            "stage": "clarify",
            "error": "route_request_failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
