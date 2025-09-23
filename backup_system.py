#!/usr/bin/env python3
"""
Backup and Rollback System for VeriPay
Creates backups before changes and allows rollback if issues occur
"""
import os
import shutil
import datetime
import subprocess
import sys
from pathlib import Path

class BackupSystem:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, description: str = "") -> str:
        """Create a backup of critical files"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        if description:
            backup_name += f"_{description.replace(' ', '_')}"
        
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        # Backup critical files
        critical_files = [
            "bot_v2/app.py",
            "bot_v2/storage.py", 
            "bot_v2/ui_legacy.py",
            "bot_v2/state.py",
            "bot_v2/ocr.py",
            "veripay_dev.db"
        ]
        
        for file_path in critical_files:
            src = self.project_root / file_path
            if src.exists():
                dst = backup_path / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        
        print(f"✅ Backup created: {backup_name}")
        return backup_name
    
    def list_backups(self) -> list:
        """List all available backups"""
        backups = []
        for item in self.backup_dir.iterdir():
            if item.is_dir() and item.name.startswith("backup_"):
                backups.append(item.name)
        return sorted(backups, reverse=True)
    
    def restore_backup(self, backup_name: str) -> bool:
        """Restore from a backup"""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            print(f"❌ Backup {backup_name} not found")
            return False
        
        # Restore critical files
        critical_files = [
            "bot_v2/app.py",
            "bot_v2/storage.py",
            "bot_v2/ui_legacy.py", 
            "bot_v2/state.py",
            "bot_v2/ocr.py",
            "veripay_dev.db"
        ]
        
        for file_path in critical_files:
            src = backup_path / file_path
            if src.exists():
                dst = self.project_root / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        
        print(f"✅ Restored from backup: {backup_name}")
        return True
    
    def test_before_backup(self) -> bool:
        """Run tests before creating backup"""
        print("🔍 Running tests before backup...")
        result = subprocess.run([sys.executable, "test_m1_functionality.py"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Tests passed - backup is safe")
            return True
        else:
            print("❌ Tests failed - backup may be unsafe")
            print(result.stdout)
            return False

def main():
    backup_system = BackupSystem()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python backup_system.py create [description]  - Create backup")
        print("  python backup_system.py list                  - List backups")
        print("  python backup_system.py restore <name>        - Restore backup")
        return
    
    command = sys.argv[1]
    
    if command == "create":
        description = sys.argv[2] if len(sys.argv) > 2 else ""
        if backup_system.test_before_backup():
            backup_system.create_backup(description)
        else:
            print("⚠️  Skipping backup due to test failures")
    
    elif command == "list":
        backups = backup_system.list_backups()
        print("Available backups:")
        for backup in backups:
            print(f"  - {backup}")
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("❌ Please specify backup name to restore")
            return
        backup_name = sys.argv[2]
        backup_system.restore_backup(backup_name)
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()
