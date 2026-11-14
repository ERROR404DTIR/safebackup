#!/usr/bin/env python3
"""SafeBackup — standard-library folder snapshots with SHA-256 verification."""
import argparse, hashlib, json, os, sys, zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

MANIFEST = "__safebackup_manifest__.json"

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def make_backup(source, destination):
    source = source.resolve()
    if not source.is_dir():
        raise SystemExit(f"Not a directory: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = destination / f"{source.name}-{stamp}.zip"
    records = []
    files = sorted(p for p in source.rglob("*") if p.is_file())
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for file in files:
            rel = file.relative_to(source).as_posix()
            z.write(file, rel)
            records.append({"path": rel, "size": file.stat().st_size, "sha256": digest(file)})
        z.writestr(MANIFEST, json.dumps({
            "format": 1, "source_name": source.name,
            "created": datetime.now().astimezone().isoformat(),
            "files": records
        }, indent=2))
    print(f"Backup created: {archive}")
    print(f"Files: {len(records)} | Size: {archive.stat().st_size:,} bytes")

def read_manifest(z):
    try:
        data = json.loads(z.read(MANIFEST).decode("utf-8"))
        if data.get("format") != 1 or not isinstance(data.get("files"), list):
            raise ValueError("Unsupported manifest")
        return data
    except KeyError:
        raise SystemExit("This ZIP has no SafeBackup manifest.")

def verify(archive):
    with zipfile.ZipFile(archive) as z:
        data = read_manifest(z)
        bad = []
        for item in data["files"]:
            name = item["path"]
            try:
                actual = hashlib.sha256(z.read(name)).hexdigest()
                if actual != item["sha256"]:
                    bad.append(name)
            except KeyError:
                bad.append(name + " (missing)")
    if bad:
        print("Verification FAILED:")
        for name in bad: print("  -", name)
        return 1
    print(f"OK: {len(data['files'])} files verified.")
    return 0

def safe_name(name):
    p = PurePosixPath(name)
    return not p.is_absolute() and all(part not in ("..", "") for part in p.parts)

def restore(archive, target):
    if verify(archive) != 0:
        raise SystemExit("Restore cancelled: backup verification failed.")
    target = target.resolve()
    with zipfile.ZipFile(archive) as z:
        data = read_manifest(z)
        members = {x.filename for x in z.infolist()}
        for item in data["files"]:
            name = item["path"]
            if not safe_name(name) or name not in members:
                raise SystemExit(f"Unsafe or missing archive path: {name}")
        target.mkdir(parents=True, exist_ok=True)
        for item in data["files"]:
            out = target.joinpath(*PurePosixPath(item["path"]).parts)
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item["path"]) as src, out.open("wb") as dst:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    dst.write(chunk)
    print(f"Restored {len(data['files'])} files into: {target}")
    print("Existing files with matching names were overwritten.")

def main():
    ap = argparse.ArgumentParser(description="Create and verify safe ZIP snapshots.")
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backup", help="Create a timestamped backup")
    b.add_argument("source", type=Path); b.add_argument("destination", type=Path)
    v = sub.add_parser("verify", help="Verify every file against SHA-256")
    v.add_argument("archive", type=Path)
    r = sub.add_parser("restore", help="Restore files from a backup")
    r.add_argument("archive", type=Path); r.add_argument("destination", type=Path)
    args = ap.parse_args()
    if args.command == "backup": make_backup(args.source, args.destination)
    elif args.command == "verify": return verify(args.archive)
    else: restore(args.archive, args.destination)
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr); raise SystemExit(2)
