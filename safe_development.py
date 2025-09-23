#!/usr/bin/env python3
"""
Safe Development Workflow
Enforces testing and backup before any code changes
"""
import os
import sys
import subprocess
import argparse
from backup_system import BackupSystem

class SafeDevelopment:
    def __init__(self):
        self.backup_system = BackupSystem()
    
    def run_tests(self) -> bool:
        """Run all tests and return success status"""
        print("🔍 Running M1 functionality tests...")
        result = subprocess.run([sys.executable, "test_m1_functionality.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    
    def create_safe_backup(self, description: str = "") -> str:
        """Create backup only if tests pass"""
        if not self.run_tests():
            print("❌ Cannot create backup - tests failed")
            return None
        
        return self.backup_system.create_backup(description)
    
    def validate_changes(self) -> bool:
        """Validate that changes don't break functionality"""
        print("🔍 Validating changes...")
        return self.run_tests()
    
    def safe_edit(self, file_path: str, description: str = ""):
        """Safely edit a file with backup and validation"""
        print(f"🔧 Safe editing: {file_path}")
        
        # Create backup
        backup_name = self.create_safe_backup(f"before_edit_{description}")
        if not backup_name:
            print("❌ Cannot proceed - tests failed")
            return False
        
        print(f"✅ Backup created: {backup_name}")
        print(f"📝 You can now safely edit: {file_path}")
        print("⚠️  After editing, run: python safe_development.py validate")
        return True
    
    def validate_and_commit(self):
        """Validate changes and commit if successful"""
        if self.validate_changes():
            print("✅ Changes validated successfully")
            print("🎉 Safe to commit changes")
            return True
        else:
            print("❌ Changes failed validation")
            print("🔄 Run: python safe_development.py rollback")
            return False
    
    def rollback(self):
        """Rollback to last backup"""
        backups = self.backup_system.list_backups()
        if not backups:
            print("❌ No backups available")
            return False
        
        latest_backup = backups[0]
        print(f"🔄 Rolling back to: {latest_backup}")
        return self.backup_system.restore_backup(latest_backup)

def main():
    parser = argparse.ArgumentParser(description="Safe Development Workflow")
    parser.add_argument("command", choices=["test", "backup", "edit", "validate", "rollback"])
    parser.add_argument("--file", help="File to edit (for edit command)")
    parser.add_argument("--description", help="Description for backup/edit")
    
    args = parser.parse_args()
    dev = SafeDevelopment()
    
    if args.command == "test":
        success = dev.run_tests()
        sys.exit(0 if success else 1)
    
    elif args.command == "backup":
        description = args.description or ""
        backup_name = dev.create_safe_backup(description)
        if backup_name:
            print(f"✅ Backup created: {backup_name}")
        else:
            sys.exit(1)
    
    elif args.command == "edit":
        if not args.file:
            print("❌ Please specify --file for edit command")
            sys.exit(1)
        success = dev.safe_edit(args.file, args.description or "")
        sys.exit(0 if success else 1)
    
    elif args.command == "validate":
        success = dev.validate_and_commit()
        sys.exit(0 if success else 1)
    
    elif args.command == "rollback":
        success = dev.rollback()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
