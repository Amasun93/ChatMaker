# ChatMaker Knowledge Phase Integration and Release Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the Knowledge rename, universal installer, and Starcore pack; independently review them; publish signed artifacts; refresh global Skills; and fast-forward tested work to GitHub main.

**Architecture:** Merge only test-green subsystem commits into the feature branch, run local and CI gates, then use a two-commit artifact/registry publication because registry URLs must pin the commit already containing each archive. Public smoke tests and repository identity checks happen before main is considered complete.

**Tech Stack:** Git, Python/unittest, Playwright, GitHub Actions, deterministic ZIP, Ed25519 signing, GitHub raw content.

## Global Constraints

- Preserve unrelated user work and re-check remote movement before merge/push.
- No GitHub Release is created in this phase.
- Registry sequence increases from 1 to at least 2.
- Pack URLs pin an exact 40-character commit containing each archive.
- Never print, read into chat, copy, or commit the private signing-key contents.
- Global Skill refresh and GitHub publication are separate acceptance gates.
- No physical-board result may be claimed.

---

### Task 1: Integrate and run local gates

**Files:**
- Modify: `docs/verification/2026-08-16-chatmaker-knowledge-auto-starcore.md`

**Interfaces:**
- Consumes: all subsystem plan deliverables.
- Produces: one feature-branch candidate with no unresolved old identity.

- [ ] **Step 1: Rebase is forbidden when user work is present**; instead fetch and inspect branch ancestry/status before integration.
- [ ] **Step 2: Run naming/path/archive scans**, all Python tests, Playwright, runtime doctor, Skill validation, publication validation, release tests, and `git diff --check`.
- [ ] **Step 3: Build Core twice and every Knowledge pack twice**, recording size, file count, and SHA-256.
- [ ] **Step 4: Record precise evidence** including the Starcore compile-only boundary.
- [ ] **Step 5: Commit** `test: verify Knowledge installer and Starcore integration`.

### Task 2: Review subsystem and whole-change correctness

**Files:**
- No required production edits; reviewers may return findings for the implementing agent.

**Interfaces:**
- Produces: spec-compliance review, code-quality review, privacy review, and final whole-change verdict.

- [ ] **Step 1: Dispatch independent reviewers** for Knowledge/state migration, installer transaction safety, and Starcore publication leakage/evidence.
- [ ] **Step 2: Fix every validated finding** with focused tests; do not accept vague approval as evidence.
- [ ] **Step 3: Dispatch a final whole-diff reviewer** against the confirmed design and four plans.
- [ ] **Step 4: Re-run affected focused tests and the full suite** after fixes.
- [ ] **Step 5: Commit review fixes** with specific messages.

### Task 3: Publish commit-pinned archives and signed registry

**Files:**
- Modify: `distribution/packs/*.cmpack`
- Modify: `distribution/registry/registry.json`
- Modify: `distribution/registry/registry.sig.json`

**Interfaces:**
- Produces: sequence-2-or-higher registry signed by the existing accepted Ed25519 key.

- [ ] **Step 1: Commit and push the final deterministic archives on the feature branch**, then capture the exact remote commit SHA.
- [ ] **Step 2: Verify each raw commit-pinned URL returns the expected archive length and SHA-256**.
- [ ] **Step 3: Generate the new registry** with four new Knowledge pack IDs, compatibility fields, and the captured immutable URLs.
- [ ] **Step 4: Sign through `scripts/sign_registry.py` using the explicit repository-external key path**; only signature metadata may appear in output.
- [ ] **Step 5: Verify signature, sequence, expiration, hashes, and URLs locally**, then commit and push registry metadata.

### Task 4: Run public and cross-platform smoke tests

**Files:**
- Update: final verification document with live evidence

**Interfaces:**
- Produces: public first-read, cached second-read, offline-read, and Windows/macOS CI evidence.

- [ ] **Step 1: In a clean temporary HOME/state root**, install Core through bootstrap and run `chatmaker-install auto` twice.
- [ ] **Step 2: Read one existing board and Starcore from the public registry**, assert first read downloads registry/signature/pack and second read adds no requests.
- [ ] **Step 3: Disable network and confirm exact installed versions remain readable**.
- [ ] **Step 4: Wait for GitHub Actions Windows and macOS installer jobs**, record their run URL/status, and investigate any real failure.
- [ ] **Step 5: Commit only truthful refreshed verification evidence**.

### Task 5: Fast-forward main, refresh global Skills, and verify GitHub

**Files:**
- External user installation: global `chatmaker`, `chatduino`, and `chatweb` Skill directories

**Interfaces:**
- Produces: local main, origin/main, public GitHub main, and global Skills all matching the tested candidate.

- [ ] **Step 1: Fetch origin and confirm** the feature candidate still descends from the expected main and both worktrees are clean.
- [ ] **Step 2: Fast-forward local `main` to the tested feature branch**, then push `main` non-forcefully.
- [ ] **Step 3: Confirm `git ls-remote origin refs/heads/main` equals the local tested commit**.
- [ ] **Step 4: Run the universal installer to refresh global Skills**, then byte-compare all three global Skill directories with repository source.
- [ ] **Step 5: Run final doctor and one public Knowledge read**, mark the long goal complete only if all required gates pass, and report remaining physical-hardware checks separately.

