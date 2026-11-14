# 🛟 SafeBackup

A single-file folder snapshot tool. **No pip, no third-party packages** — only Python's standard library.

## Run

```bash
python safebackup.py backup ./my-project ./backups
python safebackup.py verify ./backups/my-project-20261113-201000.zip
python safebackup.py restore ./backups/my-project-20261113-201000.zip ./restored-project
```

- Creates timestamped ZIP snapshots.
- Stores a SHA-256 manifest and verifies file contents.
- Restores only paths validated against archive traversal.
- Restore may overwrite files with the same names; choose a new destination to keep existing data.

Requires Python 3.9+. No installation or `pip install`.