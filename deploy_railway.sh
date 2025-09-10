#!/bin/bash

echo "🚀 Deploying VeriPay Bot to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Login to Railway
echo "🔐 Logging into Railway..."
railway login

# Initialize Railway project
echo "📦 Initializing Railway project..."
railway init

# Deploy
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment complete!"
echo "🔗 Your bot is now live on Railway!"
