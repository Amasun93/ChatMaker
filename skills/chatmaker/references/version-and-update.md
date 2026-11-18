# Check or update ChatMaker

Use the directory of the `SKILL.md` actually loaded for this conversation. Run `scripts/chatmaker_version.py` from that Skill directory with an available Python 3.11 or newer. Reuse the project's Python if the runtime is already prepared. The script uses Python's standard library and can check the Skill before any board tools are installed.

## Check in the background during project work

On first use in a conversation, run `python -I <loaded-skill-directory>/scripts/chatmaker_version.py startup-check` with a Python you already know works. It returns a cached result or starts a detached read-only check. Continue the project without waiting. If it reports `startup_check_pending`, read the result with `startup-status` at the next natural pause or reply, using the same paths. A pending or unavailable result needs no status message and no polling loop. If the user explicitly asks for an offline self-check, use `self-check` directly.

When `update_available` is true, briefly show the available version or commit, link the changelog, and ask whether to update now. Ask once per target in a conversation. Continue the project if the user skips or declines the update. Run `update` only when the user explicitly requests it or agrees to the proposed update.

When an existing Python is unavailable, use the host's repository tools in parallel if the host can identify the loaded revision and check the official source. Skip the automatic check if the host cannot do so without interrupting the project. A version check never needs a Python installation, board tools, or a serial scan.

## Respond to an explicit version request

| User request | Action |
| --- | --- |
| “版本自检”, “检查更新”, “我用的是最新版吗” | `check-update` |
| “只看本地版本”, “离线自检” | `self-check` |
| “更新 ChatMaker”, or agreement to the update you just described | `update` |

Use `--runtime-root` for the actual project runtime when it is separate from the source checkout. Use `--checkout` when the known official source checkout is separate from the loaded Skill. Supply only paths obtained from the active Skill or the local tool the project already uses. Without a known runtime, report the Skill result and say the local tool has yet to be checked. A version request needs no serial scan, board setup, or new runtime.

```text
python <loaded-skill-directory>/scripts/chatmaker_version.py check-update
python <loaded-skill-directory>/scripts/chatmaker_version.py update --checkout <source-checkout> --runtime-root <project-runtime>
```

`check-update` tries the official GitHub main branch first and falls back to the official Gitee mirror. Report the source, the target version and commit, the Skill's file match, the actual local tool's commit, and the changelog link. Same version numbers can correspond to different commits. For a copied Skill, `verified_against_commit` identifies the commit whose instructions and scripts match. Treat an unknown local commit or unavailable source as unverified. If only Gitee was reachable, describe the target as the Gitee mirror's version. If the user only asked to check, report any available update and let them decide whether to apply it.

`update` can advance a clean official Git `main` checkout and refresh the editable runtime that points to it if package inputs change. It preserves project files and existing board tool directories. If local changes, local commits, or a detached checkout prevent that update, explain the specific result and keep the user's working copy available. The user can use their host's update entry or choose a separate official checkout. A failed runtime refresh can be retried by running `update` again.

For a Skill copy managed by the AI app, use that app's native Skill update operation for the current ChatMaker installation if it is exposed. Use the official repository or the mirror named by the check. If the app requires a click or a new chat, give that single action and verify the loaded files afterward. A source checkout update may leave the instructions already loaded in this conversation in memory. When the loaded Skill changed, reload it if supported or open a fresh conversation. Confirm the version there before continuing a requested demo.

If Python or local commands are unavailable, the official repositories and their changelogs can still be read through the available web or repository tools. Report the remote version and whatever the app can prove about the loaded Skill. The app's Skill update entry is the route for its installed copy in that case.
