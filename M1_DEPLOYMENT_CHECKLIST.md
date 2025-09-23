# ✅ M1 Deployment Checklist

## Pre-Deployment Setup

### 1. Environment Preparation
- [ ] Create production Supabase project
- [ ] Set up Google Cloud Vision API credentials
- [ ] Create production Telegram bot with @BotFather
- [ ] Configure environment variables
- [ ] Set up monitoring and logging

### 2. Database Migration
- [ ] Export SQLite data (if any)
- [ ] Run PostgreSQL migrations in Supabase
- [ ] Set up Row Level Security (RLS)
- [ ] Test database connections
- [ ] Verify all tables and relationships

### 3. Code Preparation
- [ ] Review and test all M1 features
- [ ] Fix any remaining bugs
- [ ] Optimize performance
- [ ] Add error handling
- [ ] Update documentation

## Deployment Steps

### 1. Supabase Setup
```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Initialize project (if not done)
supabase init

# Link to your project
supabase link --project-ref YOUR_PROJECT_REF
```

### 2. Environment Variables
```bash
# Set in Supabase Dashboard > Settings > Edge Functions
BOT_TOKEN=your_production_bot_token
SUPER_ADMIN_ID=369249230
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
GOOGLE_APPLICATION_CREDENTIALS=your_gcp_credentials
```

### 3. Deploy Edge Function
```bash
# Deploy the bot function
supabase functions deploy veripay-bot

# Set webhook URL
curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_PROJECT_REF.supabase.co/functions/v1/veripay-bot"}'
```

## Post-Deployment Testing

### 1. Basic Functionality
- [ ] Bot responds to /start
- [ ] User registration works
- [ ] Role-based routing works
- [ ] Language selection works
- [ ] OCR payment capture works
- [ ] Transaction storage works
- [ ] Approval workflows work

### 2. User Flows
- [ ] New user registration
- [ ] Super Admin approval flow
- [ ] Restaurant Admin approval flow
- [ ] Waiter payment capture
- [ ] Transaction viewing
- [ ] Multi-language support

### 3. Error Handling
- [ ] Invalid input handling
- [ ] Network error recovery
- [ ] Database error handling
- [ ] OCR failure handling
- [ ] Webhook timeout handling

## Monitoring Setup

### 1. Logging
- [ ] Application logs
- [ ] Error tracking
- [ ] Performance metrics
- [ ] User activity logs

### 2. Alerts
- [ ] Bot downtime alerts
- [ ] High error rate alerts
- [ ] Database connection alerts
- [ ] OCR API limit alerts

### 3. Analytics
- [ ] User registration metrics
- [ ] Transaction volume
- [ ] OCR success rate
- [ ] Response times

## Go-Live Checklist

### 1. Final Verification
- [ ] All tests passing
- [ ] Performance acceptable
- [ ] Security review complete
- [ ] Documentation updated
- [ ] Support channels ready

### 2. Launch Preparation
- [ ] Bot description updated
- [ ] Commands configured
- [ ] Support team notified
- [ ] Monitoring active
- [ ] Rollback plan ready

### 3. Post-Launch
- [ ] Monitor for 24 hours
- [ ] Collect user feedback
- [ ] Fix critical issues
- [ ] Plan M2 development

## Emergency Procedures

### 1. Bot Issues
```bash
# Disable webhook (fallback to polling)
curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/deleteWebhook"

# Check bot status
curl "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

### 2. Database Issues
```bash
# Check database status
supabase db status

# Restore from backup
supabase db reset
```

### 3. Function Issues
```bash
# Check function logs
supabase functions logs veripay-bot

# Redeploy function
supabase functions deploy veripay-bot
```

---

## 🎯 M1 Ready for Production!

**All core features are implemented and tested.**
**Deployment can proceed when ready.**
