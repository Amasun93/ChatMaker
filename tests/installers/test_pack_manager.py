from __future__ import annotations

import base64
import hashlib
import io
import json
import multiprocessing
import os
import shutil
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.installers.pack_artifact import build_pack
from chatmaker.installers import pack_manager as pack_manager_module

try:
    from chatmaker.installers.pack_manager import (
        FetchResponse,
        PackManager,
        PackManagerError,
    )
    from chatmaker.pack_cli import execute as execute_cli
except ImportError:
    FetchResponse = None
    PackManager = None
    PackManagerError = None
    execute_cli = None


NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
REGISTRY_URL = (
    "https://raw.githubusercontent.com/Amasun93/ChatMaker/main/"
    "distribution/registry/registry.json"
)
SIGNATURE_URL = REGISTRY_URL.replace("registry.json", "registry.sig.json")
PACK_ID = "chatmaker-board-arduino-nano-classic-wiki"
BOARD_ID = "arduino-nano-classic"


class MemoryTransport:
    def __init__(self) -> None:
        self.responses: dict[str, object] = {}
        self.calls: list[str] = []
        self._lock = threading.Lock()

    def set(self, url: str, data: bytes, *, final_url: str | None = None) -> None:
        self.responses[url] = (data, final_url or url)

    def fetch(self, url: str):
        with self._lock:
            self.calls.append(url)
            response = self.responses[url]
        if isinstance(response, BaseException):
            raise response
        data, final_url = response
        return FetchResponse(data=data, final_url=final_url)


class NoNetworkTransport:
    def fetch(self, url: str):
        raise AssertionError(f"offline operation attempted network access: {url}")


def _crash_after_part_write(
    user_root: str,
    trust_store: dict,
    responses: dict[str, tuple[bytes, str]],
) -> None:
    class _StaticTransport:
        def fetch(self, url: str):
            data, final_url = responses[url]
            return FetchResponse(data=data, final_url=final_url)

    def crash(point: str) -> None:
        if point == "pack.after_part_write":
            os._exit(23)

    PackManager(
        user_root=Path(user_root),
        transport=_StaticTransport(),
        trust_store=trust_store,
        registry_url=REGISTRY_URL,
        signature_url=SIGNATURE_URL,
        core_version="0.1.0",
        now=NOW,
        failure_injector=crash,
    ).ensure(PACK_ID)


class PackFixture:
    def __init__(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.user_root = self.root / "user"
        self.private_key = Ed25519PrivateKey.generate()
        public = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.trust_store = {
            "schema_version": "1.0",
            "registry_url": REGISTRY_URL,
            "signature_url": SIGNATURE_URL,
            "keys": [
                {
                    "key_id": "test-official",
                    "algorithm": "ed25519",
                    "public_key_base64": base64.b64encode(public).decode("ascii"),
                    "fingerprint_sha256": hashlib.sha256(public).hexdigest(),
                    "status": "active",
                    "not_before": "2026-08-01T00:00:00Z",
                    "not_after": None,
                }
            ],
        }
        self.transport = MemoryTransport()
        self.archives: dict[str, bytes] = {}

    def cleanup(self) -> None:
        self.tempdir.cleanup()

    def archive(self, version: str, body: str | None = None) -> bytes:
        if version in self.archives:
            return self.archives[version]
        source = self.root / "sources" / version
        (source / "llmwiki" / "sections").mkdir(parents=True)
        (source / "llmwiki" / "index.yaml").write_text(
            "schema_version: '1.0'\n", encoding="utf-8"
        )
        (source / "llmwiki" / "sections" / "start-here.md").write_text(
            body or f"# Version {version}\n", encoding="utf-8"
        )
        output = self.root / "build" / f"{version}.cmpack"
        build_pack(
            source,
            output,
            pack_id=PACK_ID,
            pack_version=version,
            board_id=BOARD_ID,
            core_minimum="0.1.0",
            core_maximum_exclusive="0.2.0",
        )
        self.archives[version] = output.read_bytes()
        return self.archives[version]

    def publish(
        self,
        version: str,
        *,
        sequence: int,
        expires_at: str = "2026-08-23T00:00:00Z",
        archive_bytes: bytes | None = None,
        served_archive: bytes | None = None,
        pack_final_url: str | None = None,
        corrupt_signature: bool = False,
    ) -> dict:
        expected = archive_bytes if archive_bytes is not None else self.archive(version)
        pack_url = (
            "https://raw.githubusercontent.com/Amasun93/ChatMaker/"
            + f"{sequence:040x}"
            + "/distribution/packs/"
            + f"{PACK_ID}-{version}.cmpack"
        )
        entry = {
            "pack_id": PACK_ID,
            "pack_type": "knowledge",
            "version": version,
            "board_id": BOARD_ID,
            "url": pack_url,
            "length": len(expected),
            "sha256": hashlib.sha256(expected).hexdigest(),
            "compatibility": {
                "core": {"minimum": "0.1.0", "maximum_exclusive": "0.2.0"},
                "pack_manifest_schema": ["1.0"],
                "llmwiki_index_schema": ["1.0"],
            },
        }
        value = {
            "schema_version": "1.0",
            "sequence": sequence,
            "generated_at": "2026-08-16T00:00:00Z",
            "expires_at": expires_at,
            "packs": [entry],
        }
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8") + b"\n"
        signature = self.private_key.sign(raw)
        if corrupt_signature:
            signature = bytes([signature[0] ^ 1]) + signature[1:]
        detached = json.dumps(
            {
                "key_id": "test-official",
                "algorithm": "ed25519",
                "signature": base64.b64encode(signature).decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        self.transport.set(REGISTRY_URL, raw)
        self.transport.set(SIGNATURE_URL, detached)
        self.transport.set(
            pack_url,
            expected if served_archive is None else served_archive,
            final_url=pack_final_url,
        )
        return entry

    def manager(self, **overrides):
        kwargs = {
            "user_root": self.user_root,
            "transport": self.transport,
            "trust_store": self.trust_store,
            "registry_url": REGISTRY_URL,
            "signature_url": SIGNATURE_URL,
            "core_version": "0.1.0",
            "now": NOW,
        }
        kwargs.update(overrides)
        return PackManager(**kwargs)


class PackManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        if PackManager is None or FetchResponse is None or PackManagerError is None:
            self.fail("Task 4 pack manager is missing")
        self.fx = PackFixture()

    def tearDown(self) -> None:
        self.fx.cleanup()

    def assert_manager_error(self, code: str, operation, *args, **kwargs):
        with self.assertRaises(PackManagerError) as caught:
            operation(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_user_layout_separates_override_cache_store_state_locks_and_quarantine(self):
        paths = self.fx.manager().paths
        values = {
            paths.overrides,
            paths.cache,
            paths.store,
            paths.state,
            paths.locks,
            paths.quarantine,
            paths.staging,
        }
        self.assertEqual(len(values), 7)
        for path in values:
            path.relative_to(self.fx.user_root)
        self.assertEqual(paths.registry_state, paths.state / "registry-sequences.json")

    def test_first_ensure_downloads_then_exact_active_ensure_is_zero_write(self):
        entry = self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()

        first = manager.ensure(PACK_ID)
        active_before = manager.paths.active.read_bytes()
        calls_before = list(self.fx.transport.calls)
        cache_mtime = (manager.paths.cache / f"{entry['sha256']}.cmpack").stat().st_mtime_ns
        second = manager.ensure(PACK_ID, version="1.0.0")

        self.assertEqual(first["version"], "1.0.0")
        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(self.fx.transport.calls, calls_before)
        self.assertEqual(manager.paths.active.read_bytes(), active_before)
        self.assertEqual(
            (manager.paths.cache / f"{entry['sha256']}.cmpack").stat().st_mtime_ns,
            cache_mtime,
        )
        self.assertTrue(manager.status(PACK_ID)["packs"][0]["verified"])
        self.assertEqual(manager.inspect_cache()["objects"][0]["sha256"], entry["sha256"])

    def test_offline_exact_cached_archive_installs_without_network(self):
        self.fx.publish("1.0.0", sequence=1)
        online = self.fx.manager()
        online.ensure(PACK_ID)
        shutil.rmtree(online.paths.store / PACK_ID)
        online.paths.active.unlink()

        offline = self.fx.manager(transport=NoNetworkTransport())
        result = offline.ensure(PACK_ID, version="1.0.0", offline=True)

        self.assertEqual(result["source"], "cache")
        self.assertEqual(result["version"], "1.0.0")
        self.assertTrue(offline.status(PACK_ID)["packs"][0]["verified"])

    def test_offline_missing_reports_cached_and_installed_versions(self):
        error = self.assert_manager_error(
            "offline_pack_unavailable",
            self.fx.manager(transport=NoNetworkTransport()).ensure,
            PACK_ID,
            version="9.9.9",
            offline=True,
        )
        self.assertEqual(error.details["cached_versions"], [])
        self.assertEqual(error.details["installed_versions"], [])

    def test_bad_signature_and_registry_replay_leave_active_bytes_unchanged(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        active_before = manager.paths.active.read_bytes()

        self.fx.publish("2.0.0", sequence=2, corrupt_signature=True)
        self.assert_manager_error("registry_signature_invalid", manager.update, PACK_ID)
        self.assertEqual(manager.paths.active.read_bytes(), active_before)

        self.fx.publish("2.0.0", sequence=1)
        self.assert_manager_error("registry_replay_detected", manager.update, PACK_ID)
        self.assertEqual(manager.paths.active.read_bytes(), active_before)

    def test_corrupt_archive_and_redirect_origin_do_not_replace_active(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        active_before = manager.paths.active.read_bytes()

        valid_v2 = self.fx.archive("1.1.0")
        corrupt_v2 = valid_v2[:-1] + bytes([valid_v2[-1] ^ 1])
        self.fx.publish(
            "1.1.0", sequence=2, archive_bytes=valid_v2, served_archive=corrupt_v2
        )
        self.assert_manager_error("pack_hash_mismatch", manager.update, PACK_ID)
        self.assertEqual(manager.paths.active.read_bytes(), active_before)

        redirect_fx = PackFixture()
        try:
            redirect_fx.publish("1.0.0", sequence=1)
            redirect_manager = redirect_fx.manager()
            redirect_manager.ensure(PACK_ID)
            redirect_active = redirect_manager.paths.active.read_bytes()
            redirect_archive = redirect_fx.archive("1.1.0")
            redirect_fx.publish(
                "1.1.0",
                sequence=2,
                archive_bytes=redirect_archive,
                pack_final_url="https://example.invalid/pack.cmpack",
            )
            self.assert_manager_error(
                "pack_redirect_origin_changed", redirect_manager.update, PACK_ID
            )
            self.assertEqual(redirect_manager.paths.active.read_bytes(), redirect_active)
        finally:
            redirect_fx.cleanup()

    def test_concurrent_ensure_serializes_to_one_download(self):
        entry = self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: manager.ensure(PACK_ID), range(2)))

        self.assertEqual(sorted(result["changed"] for result in results), [False, True])
        self.assertEqual(self.fx.transport.calls.count(entry["url"]), 1)
        self.assertTrue(manager.status(PACK_ID)["packs"][0]["verified"])

    def test_concurrent_ensure_and_update_leave_one_verified_newer_active_version(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        entry = self.fx.publish("1.1.0", sequence=2)

        with ThreadPoolExecutor(max_workers=2) as pool:
            ensure_future = pool.submit(manager.ensure, PACK_ID)
            update_future = pool.submit(manager.update, PACK_ID)
            ensure_result = ensure_future.result()
            update_result = update_future.result()

        self.assertIn(ensure_result["version"], {"1.0.0", "1.1.0"})
        self.assertEqual(update_result["version"], "1.1.0")
        self.assertEqual(self.fx.transport.calls.count(entry["url"]), 1)
        status = manager.status(PACK_ID)["packs"][0]
        self.assertEqual(status["version"], "1.1.0")
        self.assertTrue(status["verified"])

    def test_failures_at_every_pack_boundary_preserve_or_compensate_active_state(self):
        points = [
            "pack.after_part_write",
            "pack.after_archive_verify",
            "pack.after_staging_extract",
            "pack.after_staging_validate",
            "pack.after_store_move",
            "pack.before_active_replace",
            "pack.after_active_replace",
        ]
        for point in points:
            with self.subTest(point=point):
                fx = PackFixture()
                try:
                    fx.publish("1.0.0", sequence=1)

                    def fail(name: str) -> None:
                        if name == point:
                            raise RuntimeError(point)

                    manager = fx.manager(failure_injector=fail)
                    self.assert_manager_error(
                        "pack_activation_failed", manager.ensure, PACK_ID
                    )
                    self.assertFalse(manager.paths.active.exists())
                    self.assertEqual(
                        (fx.user_root / "overrides").exists(), False
                    )
                finally:
                    fx.cleanup()

    def test_before_and_after_active_replace_failures_restore_prior_bytes_on_update(self):
        for point in ("pack.before_active_replace", "pack.after_active_replace"):
            with self.subTest(point=point):
                fx = PackFixture()
                try:
                    fx.publish("1.0.0", sequence=1)
                    fx.manager().ensure(PACK_ID)
                    active_before = (fx.user_root / "state" / "active.json").read_bytes()
                    fx.publish("1.1.0", sequence=2)

                    def fail(name: str) -> None:
                        if name == point:
                            raise RuntimeError(point)

                    interrupted = fx.manager(failure_injector=fail)
                    self.assert_manager_error(
                        "pack_activation_failed", interrupted.update, PACK_ID
                    )
                    self.assertEqual(
                        (fx.user_root / "state" / "active.json").read_bytes(),
                        active_before,
                    )
                    self.assertEqual(
                        interrupted.status(PACK_ID)["packs"][0]["version"], "1.0.0"
                    )
                finally:
                    fx.cleanup()

    def test_restart_cleans_inactive_part_and_staging_then_resumes_verified_registry(self):
        self.fx.publish("1.0.0", sequence=1)

        def fail_after_part(name: str) -> None:
            if name == "pack.after_part_write":
                raise RuntimeError(name)

        crashed = self.fx.manager(failure_injector=fail_after_part)
        self.assert_manager_error("pack_activation_failed", crashed.ensure, PACK_ID)
        self.assertTrue(list(crashed.paths.cache.glob("*.part")))
        abandoned = crashed.paths.staging / "abandoned"
        abandoned.mkdir(parents=True)
        (abandoned / "partial").write_text("partial", encoding="utf-8")

        restarted = self.fx.manager()
        result = restarted.ensure(PACK_ID)

        self.assertEqual(result["version"], "1.0.0")
        self.assertFalse(list(restarted.paths.cache.glob("*.part")))
        self.assertFalse(abandoned.exists())

    def test_process_crash_releases_lock_without_deleting_live_lock_identity(self):
        self.fx.publish("1.0.0", sequence=1)
        responses = {
            url: value
            for url, value in self.fx.transport.responses.items()
            if isinstance(value, tuple)
        }
        context = multiprocessing.get_context("spawn")
        process = context.Process(
            target=_crash_after_part_write,
            args=(str(self.fx.user_root), self.fx.trust_store, responses),
        )
        process.start()
        process.join(20)
        if process.is_alive():
            process.terminate()
            process.join(5)
            self.fail("crash-injection child did not terminate")
        self.assertEqual(process.exitcode, 23)
        lock_path = self.fx.user_root / "locks" / "pack-manager.lock"
        self.assertTrue(lock_path.is_file())
        lock_identity = lock_path.stat().st_ino

        result = self.fx.manager().ensure(PACK_ID)

        self.assertEqual(result["version"], "1.0.0")
        self.assertEqual(lock_path.stat().st_ino, lock_identity)
        self.assertFalse(list((self.fx.user_root / "cache").glob("*.part")))

    def test_interrupted_update_resumes_accepted_registry_without_replay_fetch(self):
        self.fx.publish("1.0.0", sequence=1)
        self.fx.manager().ensure(PACK_ID)
        self.fx.publish("1.1.0", sequence=2)

        def fail_after_store(name: str) -> None:
            if name == "pack.after_store_move":
                raise RuntimeError(name)

        interrupted = self.fx.manager(failure_injector=fail_after_store)
        self.assert_manager_error("pack_activation_failed", interrupted.update, PACK_ID)
        calls_before = list(self.fx.transport.calls)

        result = self.fx.manager().update(PACK_ID)

        self.assertEqual(result["version"], "1.1.0")
        self.assertEqual(self.fx.transport.calls, calls_before)
        self.assertEqual(
            self.fx.manager().status(PACK_ID)["packs"][0]["version"], "1.1.0"
        )

    def test_drift_is_quarantined_and_reinstalled_without_touching_override(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        override = manager.paths.overrides / PACK_ID / "llmwiki" / "sections" / "start-here.md"
        override.parent.mkdir(parents=True)
        override.write_text("my local override", encoding="utf-8")
        override_before = override.read_bytes()
        official = (
            manager.paths.store
            / PACK_ID
            / "1.0.0"
            / "llmwiki"
            / "sections"
            / "start-here.md"
        )
        official.write_text("drift", encoding="utf-8")

        result = manager.ensure(PACK_ID, version="1.0.0")

        self.assertTrue(result["changed"])
        self.assertEqual(override.read_bytes(), override_before)
        self.assertTrue(list((manager.paths.quarantine / PACK_ID).iterdir()))
        self.assertTrue(manager.status(PACK_ID)["packs"][0]["verified"])

    def test_self_consistent_manifest_rewrite_is_still_official_drift(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        store = manager.paths.store / PACK_ID / "1.0.0"
        payload = store / "llmwiki" / "sections" / "start-here.md"
        changed = b"# Locally rewritten official content\n"
        payload.write_bytes(changed)
        manifest_path = store / "pack-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        item = next(
            value
            for value in manifest["files"]
            if value["path"] == "llmwiki/sections/start-here.md"
        )
        item["length"] = len(changed)
        item["sha256"] = hashlib.sha256(changed).hexdigest()
        manifest_path.write_bytes(
            (
                json.dumps(
                    manifest,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
        )

        result = manager.ensure(PACK_ID, version="1.0.0")

        self.assertTrue(result["changed"])
        self.assertNotEqual(payload.read_bytes(), changed)
        self.assertTrue(list((manager.paths.quarantine / PACK_ID).iterdir()))

    def test_update_only_moves_newer_and_rollback_rehashes_installed_older_version(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        self.fx.publish("1.1.0", sequence=2)

        updated = manager.update(PACK_ID)
        rolled_back = manager.rollback(PACK_ID)

        self.assertEqual(updated["version"], "1.1.0")
        self.assertEqual(rolled_back["version"], "1.0.0")
        self.assertTrue(manager.status(PACK_ID)["packs"][0]["verified"])

        resumed = manager.update(PACK_ID)
        self.assertEqual(resumed["version"], "1.1.0")

        downgrade_fx = PackFixture()
        try:
            downgrade_fx.publish("1.0.0", sequence=1)
            downgrade_manager = downgrade_fx.manager()
            downgrade_manager.ensure(PACK_ID)
            downgrade_fx.publish("0.9.0", sequence=2)
            self.assert_manager_error(
                "pack_activation_failed", downgrade_manager.update, PACK_ID
            )
            self.assertEqual(
                downgrade_manager.status(PACK_ID)["packs"][0]["version"], "1.0.0"
            )
        finally:
            downgrade_fx.cleanup()

    def test_ensure_cannot_silently_downgrade_an_active_newer_version(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        self.fx.publish("1.1.0", sequence=2)
        manager.update(PACK_ID)
        active_before = manager.paths.active.read_bytes()

        error = self.assert_manager_error(
            "pack_activation_failed",
            manager.ensure,
            PACK_ID,
            version="1.0.0",
        )

        self.assertEqual(error.reason, "ensure_would_downgrade")
        self.assertEqual(manager.paths.active.read_bytes(), active_before)
        self.assertEqual(manager.status(PACK_ID)["packs"][0]["version"], "1.1.0")

    def test_expired_cached_registry_cannot_authorize_new_offline_install(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        shutil.rmtree(manager.paths.store / PACK_ID)
        manager.paths.active.unlink()

        stale = self.fx.manager(
            transport=NoNetworkTransport(),
            now=datetime(2026, 8, 24, tzinfo=timezone.utc),
        )
        self.assert_manager_error(
            "registry_expired",
            stale.ensure,
            PACK_ID,
            version="1.0.0",
            offline=True,
        )

    def test_cli_adapter_returns_structured_json_for_status_and_errors(self):
        manager = self.fx.manager(transport=NoNetworkTransport())
        output = io.StringIO()
        exit_code = execute_cli(["status", PACK_ID], manager=manager, output=output)
        status = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(status["success"])

        output = io.StringIO()
        exit_code = execute_cli(
            ["ensure", PACK_ID, "--version", "1.0.0", "--offline"],
            manager=manager,
            output=output,
        )
        error = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(error["error"]["code"], "offline_pack_unavailable")
        self.assertIn("retryable", error["error"])

        output = io.StringIO()
        exit_code = execute_cli(["ensure"], manager=manager, output=output)
        invalid = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(invalid["error"]["reason"], "invalid_cli_request")

    def test_missing_production_trust_store_is_a_stable_manager_error(self):
        error = self.assert_manager_error(
            "registry_fetch_failed",
            PackManager,
            user_root=self.fx.user_root,
            trust_store_path=self.fx.root / "missing-trust-store.json",
        )
        self.assertEqual(error.reason, "trust_store_unavailable")

    def test_rollback_retains_original_archive_identity_after_cache_is_removed(self):
        first_entry = self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        self.fx.publish("1.1.0", sequence=2)
        manager.update(PACK_ID)
        for path in manager.paths.cache.iterdir():
            path.unlink()

        manager.rollback(PACK_ID, version="1.0.0")

        status = manager.status(PACK_ID)["packs"][0]
        self.assertEqual(status["archive_sha256"], first_entry["sha256"])
        self.assertTrue(status["verified"])

    def test_symlinked_cache_root_is_rejected_without_writing_outside_user_root(self):
        outside = self.fx.root / "outside-cache"
        outside.mkdir()
        self.fx.user_root.mkdir()
        try:
            self.fx.user_root.joinpath("cache").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"directory symlink unavailable: {exc}")
        self.fx.publish("1.0.0", sequence=1)

        error = self.assert_manager_error(
            "pack_activation_failed", self.fx.manager().ensure, PACK_ID
        )

        self.assertEqual(error.reason, "managed_path_unsafe")
        self.assertEqual(list(outside.iterdir()), [])

    def test_hardlinked_lock_file_is_rejected_without_mutating_the_other_name(self):
        outside = self.fx.root / "outside-lock"
        outside.write_bytes(b"")
        lock = self.fx.user_root / "locks" / "pack-manager.lock"
        lock.parent.mkdir(parents=True)
        try:
            os.link(outside, lock)
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")
        self.fx.publish("1.0.0", sequence=1)

        error = self.assert_manager_error(
            "pack_activation_failed", self.fx.manager().ensure, PACK_ID
        )

        self.assertEqual(error.reason, "manager_lock_unsafe")
        self.assertEqual(outside.read_bytes(), b"")

    def test_sequence_accepted_before_receipt_failure_recovers_same_registry(self):
        self.fx.publish("1.0.0", sequence=1)

        def fail_after_sequence(name: str) -> None:
            if name == "registry.after_sequence_replace":
                raise RuntimeError(name)

        interrupted = self.fx.manager(failure_injector=fail_after_sequence)
        error = self.assert_manager_error(
            "registry_fetch_failed", interrupted.ensure, PACK_ID
        )
        self.assertEqual(error.reason, "failure_injected")
        state_before = interrupted.paths.registry_state.read_bytes()

        recovered = self.fx.manager().ensure(PACK_ID)

        self.assertEqual(recovered["version"], "1.0.0")
        self.assertEqual(interrupted.paths.registry_state.read_bytes(), state_before)
        self.assertTrue(interrupted.paths.verified_registry.is_file())

    def test_repeated_replay_cannot_create_its_own_recovery_receipt(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        manager.paths.verified_registry.unlink()
        active_before = manager.paths.active.read_bytes()

        for _ in range(2):
            self.assert_manager_error(
                "registry_replay_detected", manager.update, PACK_ID
            )

        self.assertEqual(manager.paths.active.read_bytes(), active_before)
        self.assertFalse(manager.paths.pending_registry.exists())

    def test_drifted_active_version_remains_a_floor_for_update_and_ensure(self):
        for operation, expected_reason in (
            ("update", "update_would_downgrade"),
            ("ensure", "ensure_would_downgrade"),
        ):
            with self.subTest(operation=operation):
                fx = PackFixture()
                try:
                    fx.publish("1.1.0", sequence=1)
                    manager = fx.manager()
                    manager.ensure(PACK_ID)
                    active_before = manager.paths.active.read_bytes()
                    official = (
                        manager.paths.store
                        / PACK_ID
                        / "1.1.0"
                        / "llmwiki"
                        / "sections"
                        / "start-here.md"
                    )
                    official.write_text("drift", encoding="utf-8")
                    manager.paths.verified_registry.unlink()
                    fx.publish("1.0.0", sequence=2)

                    if operation == "update":
                        error = self.assert_manager_error(
                            "pack_activation_failed", manager.update, PACK_ID
                        )
                    else:
                        error = self.assert_manager_error(
                            "pack_activation_failed", manager.ensure, PACK_ID
                        )

                    self.assertEqual(error.reason, expected_reason)
                    self.assertEqual(manager.paths.active.read_bytes(), active_before)
                    self.assertFalse(
                        (manager.paths.store / PACK_ID / "1.0.0").exists()
                    )
                finally:
                    fx.cleanup()

    def test_fsynced_part_is_reread_before_cache_promotion(self):
        self.fx.publish("1.0.0", sequence=1)

        def corrupt_actual_part(name: str) -> None:
            if name != "pack.after_part_write":
                return
            part = next(self.fx.manager().paths.cache.glob("*.part"))
            data = part.read_bytes()
            part.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))

        manager = self.fx.manager(phase_callback=corrupt_actual_part)
        self.assert_manager_error("pack_hash_mismatch", manager.ensure, PACK_ID)
        self.assertFalse(manager.paths.active.exists())
        self.assertFalse(list(manager.paths.cache.glob("*.cmpack")))

    def test_newer_registry_refreshes_receipt_for_same_cached_archive(self):
        entry = self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        self.fx.publish("1.0.0", sequence=2, archive_bytes=self.fx.archive("1.0.0"))

        unchanged = manager.update(PACK_ID)

        self.assertFalse(unchanged["changed"])
        receipt_path = manager.paths.cache / f"{entry['sha256']}.receipt.json"
        self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8"))["sequence"], 2)
        shutil.rmtree(manager.paths.store / PACK_ID)
        manager.paths.active.unlink()
        offline = self.fx.manager(transport=NoNetworkTransport())
        self.assertEqual(
            offline.ensure(PACK_ID, version="1.0.0", offline=True)["source"],
            "cache",
        )

    def test_status_rejects_metadata_only_archive_identity_tampering(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        metadata = json.loads(manager.paths.installed_metadata.read_text(encoding="utf-8"))
        metadata["packs"][PACK_ID]["1.0.0"]["archive_sha256"] = "f" * 64
        manager.paths.installed_metadata.write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        status = manager.status(PACK_ID)["packs"][0]

        self.assertFalse(status["verified"])
        self.assertEqual(status["error"]["code"], "pack_drift_detected")

    def test_rollback_rejects_metadata_only_archive_identity_tampering(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        manager.ensure(PACK_ID)
        self.fx.publish("1.1.0", sequence=2)
        manager.update(PACK_ID)
        active_before = manager.paths.active.read_bytes()
        metadata = json.loads(manager.paths.installed_metadata.read_text(encoding="utf-8"))
        metadata["packs"][PACK_ID]["1.0.0"]["archive_sha256"] = "f" * 64
        manager.paths.installed_metadata.write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        self.assert_manager_error(
            "pack_drift_detected", manager.rollback, PACK_ID, version="1.0.0"
        )
        self.assertEqual(manager.paths.active.read_bytes(), active_before)

    def test_every_store_file_is_fsynced_before_activation(self):
        self.fx.publish("1.0.0", sequence=1)
        manager = self.fx.manager()
        real_fsync = os.fsync
        seen: set[str] = set()

        def track_store_fsync(descriptor: int) -> None:
            descriptor_stat = os.fstat(descriptor)
            store = manager.paths.store
            if store.is_dir():
                for path in store.rglob("*"):
                    if not path.is_file():
                        continue
                    path_stat = path.stat()
                    if (path_stat.st_dev, path_stat.st_ino) == (
                        descriptor_stat.st_dev,
                        descriptor_stat.st_ino,
                    ):
                        seen.add(path.relative_to(store / PACK_ID / "1.0.0").as_posix())
            real_fsync(descriptor)

        with mock.patch.object(pack_manager_module.os, "fsync", track_store_fsync):
            manager.ensure(PACK_ID)

        self.assertEqual(
            seen,
            {
                "pack-manifest.json",
                "llmwiki/index.yaml",
                "llmwiki/sections/start-here.md",
            },
        )

    def test_unrelated_corrupt_cache_is_quarantined_before_offline_missing(self):
        manager = self.fx.manager(transport=NoNetworkTransport())
        manager.paths.cache.mkdir(parents=True)
        corrupt = manager.paths.cache / f"{'0' * 64}.cmpack"
        corrupt.write_bytes(b"not a zip")

        error = self.assert_manager_error(
            "offline_pack_unavailable",
            manager.ensure,
            PACK_ID,
            version="9.9.9",
            offline=True,
        )

        self.assertEqual(error.details["cached_versions"], [])
        self.assertEqual(error.details["installed_versions"], [])
        self.assertFalse(corrupt.exists())
        self.assertTrue(list((manager.paths.quarantine / "cache").iterdir()))


if __name__ == "__main__":
    unittest.main()
