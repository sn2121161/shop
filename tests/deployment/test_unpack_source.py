import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("unpack_source", Path(__file__).resolve().parents[2] / "deploy" / "unpack-source.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceArchiveTests(unittest.TestCase):
    def test_normal_source_and_example_env_are_extracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as source:
                for name in ("backend/.env.example", "frontend/package.json"):
                    member = tarfile.TarInfo(name)
                    member.size = 2
                    source.addfile(member, io.BytesIO(b"{}"))
            destination = Path(tmp) / "source"
            module.unpack(archive, destination)
            self.assertEqual((destination / "frontend/package.json").read_bytes(), b"{}")

    def test_secrets_traversal_and_links_are_rejected_before_extracting(self):
        for name in ("../outside", "/absolute", "backend/.env", ".env.production", ".git/config", "frontend/node_modules/code", "link"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "source.tar.gz"
                with tarfile.open(archive, "w:gz") as source:
                    member = tarfile.TarInfo(name)
                    if name == "link":
                        member.type = tarfile.SYMTYPE
                        member.linkname = "../outside"
                    source.addfile(member)
                destination = Path(tmp) / "source"
                with self.assertRaises(ValueError):
                    module.unpack(archive, destination)
                self.assertEqual(list(destination.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
