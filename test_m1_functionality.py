#!/usr/bin/env python3
"""
M1 Functionality Test Suite
Tests all critical M1 features to ensure they work before any changes
"""
import os
import sys
import sqlite3
import asyncio
from typing import Dict, List, Any

# Add project root to path
sys.path.append('.')

def test_database_connectivity():
    """Test database connection and table structure"""
    print("🔍 Testing database connectivity...")
    try:
        conn = sqlite3.connect('veripay_dev.db')
        cur = conn.cursor()
        
        # Check all required tables exist
        required_tables = ['users', 'restaurants', 'waiters', 'sessions', 'media', 'transactions', 'approvals', 'audit_logs']
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cur.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
            
        print("✅ All database tables exist")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connectivity failed: {e}")
        return False

def test_imports():
    """Test all critical imports work"""
    print("🔍 Testing imports...")
    try:
        from bot_v2.app import start, handle_callback, handle_photo, handle_text_message
        from bot_v2.storage import Storage
        from bot_v2.ocr import VisionOCR
        from bot_v2.ui_legacy import (
            UserRole, UserState, build_super_admin_menu_keyboard,
            build_restaurant_admin_menu_keyboard, build_waiter_menu_keyboard
        )
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_storage_operations():
    """Test storage operations work correctly"""
    print("🔍 Testing storage operations...")
    try:
        from bot_v2.storage import Storage
        storage = Storage("sqlite:///veripay_dev.db")
        
        # Test user operations
        test_user_id = 999999999
        storage.upsert_user(test_user_id, "test_user", None, role='NEW_USER', language='en')
        user = storage.get_user_by_telegram(test_user_id)
        if not user or user['telegram_id'] != test_user_id:
            print("❌ User operations failed")
            return False
            
        # Test restaurant operations
        restaurant_data = storage.create_restaurant_for_owner(test_user_id, "Test Restaurant", "1234567890")
        if not restaurant_data:
            print("❌ Restaurant operations failed")
            return False
            
        # Test waiter operations
        waiter_data = storage.create_waiter_for_user(test_user_id, restaurant_data['id'])
        if not waiter_data:
            print("❌ Waiter operations failed")
            return False
            
        # Cleanup
        storage.conn.execute("DELETE FROM waiters WHERE id = ?", (waiter_data['id'],))
        storage.conn.execute("DELETE FROM restaurants WHERE id = ?", (restaurant_data['id'],))
        storage.conn.execute("DELETE FROM users WHERE telegram_id = ?", (test_user_id,))
        storage.conn.commit()
        
        print("✅ All storage operations successful")
        return True
    except Exception as e:
        print(f"❌ Storage operations failed: {e}")
        return False

def test_ui_functions():
    """Test UI functions work correctly"""
    print("🔍 Testing UI functions...")
    try:
        from bot_v2.ui_legacy import (
            build_super_admin_menu_keyboard, build_restaurant_admin_menu_keyboard,
            build_waiter_menu_keyboard, build_main_menu_keyboard
        )
        
        # Test with dummy data
        user_languages = {123: 'en'}
        
        # Test all menu builders
        super_menu = build_super_admin_menu_keyboard(123, user_languages)
        restaurant_menu = build_restaurant_admin_menu_keyboard(123, user_languages)
        waiter_menu = build_waiter_menu_keyboard(123, user_languages)
        main_menu = build_main_menu_keyboard(123, user_languages)
        
        if not all([super_menu, restaurant_menu, waiter_menu, main_menu]):
            print("❌ UI functions failed")
            return False
            
        print("✅ All UI functions successful")
        return True
    except Exception as e:
        print(f"❌ UI functions failed: {e}")
        return False

def test_environment_variables():
    """Test required environment variables are set"""
    print("🔍 Testing environment variables...")
    required_vars = ['BOT_TOKEN', 'SUPER_ADMIN_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
        
    print("✅ All required environment variables set")
    return True

def run_all_tests():
    """Run all tests and return overall result"""
    print("🚀 Running M1 Functionality Test Suite...")
    print("=" * 50)
    
    tests = [
        test_environment_variables,
        test_database_connectivity,
        test_imports,
        test_storage_operations,
        test_ui_functions
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("✅ M1 functionality is working correctly")
        return True
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("⚠️  M1 functionality has issues - DO NOT PROCEED WITH CHANGES")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
