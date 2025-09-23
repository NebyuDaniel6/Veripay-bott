#!/bin/bash

echo "🚀 VeriPay Bot Quick Deploy Script"
echo "=================================="

# Check if we have the credentials file
if [ ! -f "veripay-credentials.json" ]; then
    echo "❌ Error: veripay-credentials.json not found!"
    echo "Please make sure the Google Cloud credentials file is in the current directory."
    exit 1
fi

echo "✅ Found veripay-credentials.json"

# Create deployment package
echo "📦 Creating deployment package..."
mkdir -p deploy-package
cp -r bot_v2 deploy-package/
cp requirements.txt render.yaml .env.production deploy-package/
cp veripay-credentials.json deploy-package/

cd deploy-package
tar -czf ../veripay-deploy-complete.tar.gz .
cd ..

echo "✅ Created veripay-deploy-complete.tar.gz"

echo ""
echo "🎯 Next Steps:"
echo "1. Go to your Render dashboard"
echo "2. Upload veripay-deploy-complete.tar.gz"
echo "3. Set environment variables (see DEPLOYMENT_INSTRUCTIONS.md)"
echo "4. Deploy!"
echo ""
echo "📋 Your database URL:"
echo "postgresql://postgres:0938438262Neba#@db.rekvcdujfgdxwsjipzce.supabase.co:5432/postgres"
echo ""
echo "🔗 Your Supabase project: https://supabase.com/dashboard/project/rekvcdujfgdxwsjipzce"
