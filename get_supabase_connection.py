#!/usr/bin/env python3
"""
Helper script to get Supabase database connection string
"""

print("🔗 Supabase Database Connection Setup")
print("=" * 50)

print("\n📋 To get your database connection string:")
print("1. Go to your Supabase dashboard: https://supabase.com/dashboard")
print("2. Select your project: mnxschqpuppxlcmstvke")
print("3. Go to Settings → Database")
print("4. Copy the 'Connection string' (URI format)")

print("\n🔧 The connection string should look like:")
print("postgresql://postgres:[YOUR-PASSWORD]@db.mnxschqpuppxlcmstvke.supabase.co:5432/postgres")

print("\n⚠️  Important:")
print("- Replace [YOUR-PASSWORD] with your database password")
print("- This is the password you set when creating the project")
print("- NOT the API key you provided")

print("\n📝 Once you have the connection string, run:")
print("export DATABASE_URL='your_connection_string_here'")

print("\n🧪 Then test the connection:")
print("python3 setup_supabase.py")

print("\n🚀 For Railway deployment, you'll need:")
print("- Database connection string")
print("- Your Telegram bot token")
print("- Your Telegram user ID") 