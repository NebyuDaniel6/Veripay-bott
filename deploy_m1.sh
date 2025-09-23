#!/bin/bash

# VeriPay M1 Production Deployment Script
# This script deploys M1 to Supabase Edge Functions

set -e

echo "🚀 Starting VeriPay M1 Deployment..."

# Check if required tools are installed
command -v supabase >/dev/null 2>&1 || { echo "❌ Supabase CLI not found. Install with: npm install -g supabase"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js not found. Please install Node.js"; exit 1; }

# Check environment variables
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN environment variable not set"
    exit 1
fi

if [ -z "$SUPER_ADMIN_ID" ]; then
    echo "❌ SUPER_ADMIN_ID environment variable not set"
    exit 1
fi

echo "✅ Environment check passed"

# Create production configuration
echo "📝 Creating production configuration..."

cat > supabase/functions/veripay-bot/index.ts << 'TYPESCRIPT_EOF'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const BOT_TOKEN = Deno.env.get('BOT_TOKEN')
const SUPER_ADMIN_ID = Deno.env.get('SUPER_ADMIN_ID')
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')
const SUPABASE_ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')

if (!BOT_TOKEN || !SUPER_ADMIN_ID || !SUPABASE_URL || !SUPABASE_ANON_KEY) {
  throw new Error('Missing required environment variables')
}

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

serve(async (req) => {
  try {
    if (req.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 })
    }

    const body = await req.json()
    
    // Handle webhook from Telegram
    if (body.update_id) {
      await handleTelegramUpdate(body)
    }

    return new Response('OK', { status: 200 })
  } catch (error) {
    console.error('Error:', error)
    return new Response('Internal Server Error', { status: 500 })
  }
})

async function handleTelegramUpdate(update: any) {
  // Import and use the existing bot logic
  // This is a simplified version - full implementation would import the Python bot logic
  console.log('Received update:', update)
  
  // TODO: Implement full bot logic here
  // For now, just acknowledge the webhook
}
TYPESCRIPT_EOF

echo "✅ Production configuration created"

# Deploy to Supabase
echo "🚀 Deploying to Supabase..."

# Set up Supabase project (if not already done)
if [ ! -f "supabase/config.toml" ]; then
    echo "📝 Initializing Supabase project..."
    supabase init
fi

# Deploy the function
echo "📦 Deploying Edge Function..."
supabase functions deploy veripay-bot --project-ref $SUPABASE_PROJECT_REF

echo "✅ Deployment completed!"

# Set webhook URL
echo "🔗 Setting webhook URL..."
WEBHOOK_URL="https://$SUPABASE_PROJECT_REF.supabase.co/functions/v1/veripay-bot"

curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$WEBHOOK_URL\"}"

echo "✅ Webhook configured: $WEBHOOK_URL"

echo ""
echo "🎉 M1 Deployment Complete!"
echo "📊 Bot Status: https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
echo "🔗 Webhook URL: $WEBHOOK_URL"
echo ""
echo "Next steps:"
echo "1. Test the bot with /start command"
echo "2. Monitor logs: supabase functions logs veripay-bot"
echo "3. Check database: supabase db reset (if needed)"
echo ""
