#!/bin/bash

echo "🚀 Deploying VeriPay Bot to Supabase..."

# Set environment variables
export SUPABASE_URL="https://qdlnikkuycvloagmmczn.supabase.co"
export SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFkbG5pa2t1eWN2bG9hZ21tY3puIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc1MjI1MDgsImV4cCI6MjA3MzA5ODUwOH0.vFpyhsOck9jExrRJU35ULa7U0FMUUluOR6hUfM0Np4Y"

echo "✅ Environment variables set"
echo "📁 Function directory: supabase/functions/veripay-bot/"
echo "📄 Function file: index.ts"

echo ""
echo "🔧 Manual deployment steps:"
echo "1. Go to: https://supabase.com/dashboard/project/qdlnikkuycvloagmmczn/functions"
echo "2. Click 'Create a new function'"
echo "3. Name: veripay-bot"
echo "4. Copy the contents of supabase/functions/veripay-bot/index.ts"
echo "5. Set environment variables:"
echo "   - BOT_TOKEN: 8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc"
echo "   - GOOGLE_VISION_API_KEY: AIzaSyC4ESpSW_c1ijlLGwTUQ5wdBhflQOPps6M"
echo "6. Deploy the function"
echo "7. Set webhook URL: https://qdlnikkuycvloagmmczn.supabase.co/functions/v1/veripay-bot"

echo ""
echo "📋 Function ready for deployment!"
