"""Extract a release archive without following links or overwriting env files."""
import sys
import tarfile
from pathlib import Path, PurePosixPath


def unpack(archive: Path, destination: Path) -> None:
    destination.mkdir(mode=0o700)
    with tarfile.open(archive, "r:gz") as source:
        for member in source.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Archive contains an unsafe path")
            if any(part == ".git" or part == "node_modules" or
                   (part.startswith(".env") and part != ".env.example")
                   for part in path.parts):
                raise ValueError("Archive contains local configuration or dependencies")
            if not (member.isfile() or member.isdir()):
                raise ValueError("Archive links and special files are not supported")
        # All entries were checked before extraction into a new, empty directory.
        source.extractall(destination)


if __name__ == "__main__":
    unpack(Path(sys.argv[1]), Path(sys.argv[2]))
