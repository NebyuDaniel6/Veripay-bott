#!/usr/bin/env python3
"""
Test script to verify callback handling
"""
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_callback_patterns():
    """Test callback data patterns"""
    test_callbacks = [
        "waiter_capture",
        "waiter_transactions", 
        "waiter_help",
        "admin_dashboard",
        "admin_summary",
        "register_role_waiter",
        "register_role_restaurant",
        "approve_registration_123456",
        "reject_registration_123456",
        "start_registration",
        "guest_help"
    ]
    
    print("Testing callback patterns:")
    for callback in test_callbacks:
        if callback.startswith("waiter_"):
            print(f"✅ {callback} -> Waiter callback")
        elif callback.startswith("admin_"):
            print(f"✅ {callback} -> Admin callback")
        elif callback.startswith("register_role_"):
            print(f"✅ {callback} -> Registration role callback")
        elif callback.startswith("approve_registration_"):
            print(f"✅ {callback} -> Approve registration callback")
        elif callback.startswith("reject_registration_"):
            print(f"✅ {callback} -> Reject registration callback")
        elif callback == "start_registration":
            print(f"✅ {callback} -> Start registration callback")
        elif callback == "guest_help":
            print(f"✅ {callback} -> Guest help callback")
        else:
            print(f"❌ {callback} -> Unknown callback")

if __name__ == "__main__":
    test_callback_patterns() 