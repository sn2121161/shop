"""Exercise deployment ordering and failure handling without touching Docker."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


DEPLOY = Path(__file__).resolve().parents[1]
SHA = "a" * 40
IMAGE_ID = "sha256:" + "b" * 64


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shop-deploy-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.release = self.root / "release"
        self.release.mkdir()
        for name in ("deploy.sh", "compose.yml"):
            shutil.copyfile(DEPLOY / name, self.release / name)
        (self.release / "images.tar.gz").write_bytes(b"mock image archive")
        for service in ("api", "frontend"):
            (self.release / f"{service}-image.id").write_text(IMAGE_ID + "\n")
        names = ("images.tar.gz", "api-image.id", "frontend-image.id", "compose.yml", "deploy.sh")
        (self.release / "SHA256SUMS").write_text("".join(
            f"{hashlib.sha256((self.release / name).read_bytes()).hexdigest()}  {name}\n"
            for name in names
        ))
        env_file = self.root / "production.env"
        env_file.touch()
        (self.root / "deploy.env").write_text(
            f"SHOP_COMPOSE_PROJECT=shop\nSHOP_ENV_FILE={env_file}\n"
            "SHOP_DB_VOLUME=existing-db\nSHOP_UPLOAD_VOLUME=existing-uploads\n"
        )
        self.log = self.root / "commands.jsonl"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Docker operations are logged, with selectable failures at real seams.
        stub = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
mode = os.environ["DEPLOY_TEST_MODE"]
with open(os.environ["DEPLOY_TEST_LOG"], "a") as log:
    log.write(json.dumps([name, args]) + "\\n")
if name == "curl": sys.exit(mode == "health-fail")
if name != "docker": sys.exit(0)
if "pull" in args or "push" in args:
    raise SystemExit("Unexpected registry access")
if args[:2] == ["image", "load"]:
    sys.exit(mode == "load-fail")
if args[:2] == ["image", "inspect"]:
    fmt = args[3]
    if ".Id" in fmt: print("sha256:" + ("c" if mode == "wrong-image" else "b") * 64)
    elif ".Architecture" in fmt: print("arm64" if mode == "wrong-architecture" else "amd64")
    else: print(("c" if mode == "wrong-revision" else "a") * 40)
elif args[0] == "inspect":
    fmt = args[2]
    if "/var/lib/postgresql/data" in fmt: print("wrong" if mode == "wrong-volume" else "existing-db")
    elif "/app/uploads" in fmt: print("existing-uploads")
    else: print("old-image:previous")
elif args[0] == "compose":
    if "ps" in args: print("id-" + args[-1])
    elif "exec" in args:
        if mode == "backup-fail": sys.exit(1)
        print("-- SQL backup")
    elif "alembic" in args and mode == "migration-fail": sys.exit(1)
    elif "python" in args and mode == "mail-fail": sys.exit(1)
'''
        for name in ("docker", "flock", "curl", "sleep"):
            path = self.bin / name
            path.write_text(stub)
            path.chmod(0o755)
        # Use real checksum verification on both macOS and Linux.
        if not shutil.which("sha256sum"):
            path = self.bin / "sha256sum"
            path.write_text('#!/bin/sh\nexec shasum -a 256 "$@"\n')
            path.chmod(0o755)

    def run_deploy(self, mode="success"):
        env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                   DEPLOY_TEST_MODE=mode, DEPLOY_TEST_LOG=str(self.log))
        result = subprocess.run(
            ["bash", str(self.release / "deploy.sh"), str(self.root), "shop-release", SHA],
            env=env, capture_output=True, text=True, timeout=30,
        )
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        return result, calls

    def assert_not_released(self, result, calls):
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(name == "docker" and "up" in args for name, args in calls))
        self.assertFalse((self.root / "deployed-sha").exists())

    def test_success_uses_uploaded_images_and_records_release(self):
        result, calls = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        docker = [args for name, args in calls if name == "docker"]
        load = next(i for i, args in enumerate(docker) if args[:2] == ["image", "load"])
        migration = next(i for i, args in enumerate(docker) if "alembic" in args)
        switch = next(i for i, args in enumerate(docker) if "up" in args)
        self.assertLess(load, migration)
        self.assertLess(migration, switch)
        for args in docker:
            if args[0] == "compose" and ("run" in args or "up" in args):
                self.assertEqual(args[args.index("--pull") + 1], "never")
        self.assertEqual((self.root / "deployed-sha").read_text().strip(), SHA)
        self.assertEqual((self.root / "current").resolve(), self.release)
        self.assertFalse((self.release / "images.tar.gz").exists())
        self.assertEqual(len(list((self.root / "backups").glob("*.sql.gz"))), 1)

    def test_corrupt_archive_stops_before_import(self):
        (self.release / "images.tar.gz").write_bytes(b"corrupted during transfer")
        result, calls = self.run_deploy()
        self.assert_not_released(result, calls)
        self.assertFalse(any(args[:2] == ["image", "load"] for _, args in calls))

    def test_missing_archive_stops_before_import(self):
        (self.release / "images.tar.gz").unlink()
        result, calls = self.run_deploy()
        self.assert_not_released(result, calls)
        self.assertFalse(any(args[:2] == ["image", "load"] for _, args in calls))

    def test_image_import_failure_stops_before_migration(self):
        self.check_failure_before_migration("load-fail")

    def test_wrong_image_stops_before_migration(self):
        self.check_failure_before_migration("wrong-image")

    def test_wrong_architecture_stops_before_migration(self):
        self.check_failure_before_migration("wrong-architecture")

    def test_wrong_revision_stops_before_migration(self):
        self.check_failure_before_migration("wrong-revision")

    def test_wrong_volume_stops_before_import(self):
        result, calls = self.run_deploy("wrong-volume")
        self.assert_not_released(result, calls)
        self.assertFalse(any(args[:2] == ["image", "load"] for _, args in calls))

    def test_missing_mail_config_stops_before_migration(self):
        self.check_failure_before_migration("mail-fail")

    def test_backup_failure_stops_before_migration(self):
        self.check_failure_before_migration("backup-fail")

    def check_failure_before_migration(self, mode):
        result, calls = self.run_deploy(mode)
        self.assert_not_released(result, calls)
        self.assertFalse(any("alembic" in args for _, args in calls))

    def test_migration_failure_keeps_old_containers(self):
        result, calls = self.run_deploy("migration-fail")
        self.assert_not_released(result, calls)

    def test_health_failure_is_not_reported_as_success(self):
        result, calls = self.run_deploy("health-fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(name == "docker" and "up" in args for name, args in calls))
        self.assertFalse((self.root / "deployed-sha").exists())
        self.assertTrue((self.release / "images.tar.gz").exists())


if __name__ == "__main__":
    unittest.main()
