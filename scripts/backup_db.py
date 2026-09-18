#!/usr/bin/env python3
"""Daily database backup script for PyroGuard."""
import os
import sys
import gzip
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config.config import settings

def backup_database():
    """Create a compressed backup of the SQLite database."""
    # Parse database URL
    db_url = settings.DATABASE_URL
    if not db_url.startswith("sqlite:///"):
        print(f"Only SQLite databases supported. Current: {db_url}")
        return False

    db_path = Path(db_url.replace("sqlite:///", ""))
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return False

    # Backup directory
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Timestamped backup filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"incidents_{timestamp}.sqlite.gz"
    backup_path = backup_dir / backup_name

    try:
        # Compress and copy
        with open(db_path, "rb") as f_in:
            with gzip.open(backup_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        print(f"Backup created: {backup_path} ({size_mb:.2f} MB)")

        # Cleanup old backups (keep last 30)
        backups = sorted(backup_dir.glob("incidents_*.sqlite.gz"), key=lambda p: p.stat().st_mtime)
        for old_backup in backups[:-30]:
            old_backup.unlink()
            print(f"Removed old backup: {old_backup}")

        return True

    except Exception as e:
        print(f"Backup failed: {e}")
        return False


def restore_database(backup_file: str):
    """Restore database from a backup file."""
    backup_path = Path(backup_file)
    if not backup_path.exists():
        print(f"Backup file not found: {backup_path}")
        return False

    db_url = settings.DATABASE_URL
    if not db_url.startswith("sqlite:///"):
        print(f"Only SQLite databases supported. Current: {db_url}")
        return False

    db_path = Path(db_url.replace("sqlite:///", ""))

    try:
        # Decompress and restore
        with gzip.open(backup_path, "rb") as f_in:
            with open(db_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        print(f"Database restored from: {backup_path}")
        return True

    except Exception as e:
        print(f"Restore failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PyroGuard database backup/restore")
    parser.add_argument("action", choices=["backup", "restore"], help="Action to perform")
    parser.add_argument("file", nargs="?", help="Backup file to restore (for restore action)")
    
    args = parser.parse_args()
    
    if args.action == "backup":
        success = backup_database()
        sys.exit(0 if success else 1)
    elif args.action == "restore":
        if not args.file:
            print("Error: restore action requires a backup file path")
            sys.exit(1)
        success = restore_database(args.file)
        sys.exit(0 if success else 1)