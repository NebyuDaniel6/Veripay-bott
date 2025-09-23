#!/bin/bash

echo "🚀 Deploying VeriPay Bot to Render..."

# Check if we're in the right directory
if [ ! -f "bot_v2/app.py" ]; then
    echo "❌ Error: bot_v2/app.py not found. Please run this script from the project root."
    exit 1
fi

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Error: Git not initialized. Please run 'git init' first."
    exit 1
fi

# Add all files to git
echo "📁 Adding files to git..."
git add .

# Commit changes
echo "💾 Committing changes..."
git commit -m "Deploy VeriPay Bot to Render - $(date)"

# Push to GitHub
echo "⬆️ Pushing to GitHub..."
git push origin main

echo "✅ Deployment initiated! Check your Render dashboard for progress."
echo "🔗 Your bot will be available at: https://your-app-name.onrender.com"
echo ""
echo "📋 Next steps:"
echo "1. Set environment variables in Render dashboard"
echo "2. Upload veripay-credentials.json file"
echo "3. Set webhook URL in Telegram"
