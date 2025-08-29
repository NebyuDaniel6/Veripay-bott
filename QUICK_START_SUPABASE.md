# VeriPay Bot - Quick Start Guide (Supabase)

Get your VeriPay bot running in minutes with this quick start guide!

## 🚀 Quick Start (5 minutes)

### 1. Set Environment Variables
```bash
export TELEGRAM_BOT_TOKEN="8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc"
export DATABASE_URL="your_supabase_connection_string"
export ADMIN_USER_ID="your_telegram_user_id"
```

### 2. Run Setup
```bash
./deploy_supabase.sh setup
```

### 3. Test Locally
```bash
./deploy_supabase.sh test
```

### 4. Deploy to Cloud
```bash
./deploy_supabase.sh deploy
```

## 📋 What You Get

✅ **Free PostgreSQL Database** (Supabase)  
✅ **Free Cloud Hosting** (Railway)  
✅ **Telegram Bot Integration**  
✅ **OCR Payment Processing**  
✅ **Role-based Access Control**  
✅ **Admin Dashboard**  
✅ **Real-time Reports**  

## 🗄️ Database Setup

### Option 1: Use Supabase (Recommended)
1. Go to [supabase.com](https://supabase.com)
2. Create free account
3. Create new project
4. Copy connection string
5. Run SQL from `SUPABASE_DEPLOYMENT.md`

### Option 2: Use Local SQLite (Development)
```bash
export DATABASE_URL="sqlite:///lean_veripay.db"
```

## ☁️ Deployment Options

### Railway (Recommended)
- Free tier: 500 hours/month
- Auto-deploy from GitHub
- SSL certificates included
- Global CDN

### Render (Alternative)
- Free tier: 750 hours/month
- Easy GitHub integration
- Automatic deployments

### Fly.io (Alternative)
- Free tier: 3 shared-cpu VMs
- Global edge deployment
- Docker-based

## 🧪 Testing

### Local Testing
```bash
# Test bot functionality
./deploy_supabase.sh test

# Manual testing
python3 veripay_supabase_bot.py
```

### Cloud Testing
1. Deploy to Railway/Render
2. Find your bot: `@your_bot_username`
3. Send `/start`
4. Test registration flow
5. Test payment upload

## 🔧 Configuration

### Environment Variables
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_URL=your_database_url
ADMIN_USER_ID=your_telegram_id
DEBUG=false
TEST_MODE=false
```

### Bot Features
- **Registration System**: Auto-approval for demo
- **OCR Processing**: Tesseract integration
- **Role Management**: Guest, Waiter, Admin
- **Payment Verification**: Mock bank APIs
- **Reporting**: Transaction analytics

## 📊 Demo Data

The setup includes demo data:
- 1 Restaurant: "Demo Restaurant"
- 2 Users: Demo Admin, Demo Waiter
- 5 Tables: T1-T5
- 3 Transactions: 2 verified, 1 pending
- Sample reports and logs

## 🆘 Troubleshooting

### Common Issues

**Bot not responding:**
```bash
# Check if bot is running
./deploy_supabase.sh status

# Check logs
tail -f /tmp/veripay.log
```

**Database connection error:**
```bash
# Test database connection
python3 setup_supabase.py
```

**Deployment fails:**
```bash
# Check requirements
pip3 install -r requirements_supabase.txt

# Check Python version
python3 --version
```

### Debug Mode
```bash
export DEBUG=true
python3 veripay_supabase_bot.py
```

## 📞 Support

- **Documentation**: `SUPABASE_DEPLOYMENT.md`
- **Issues**: GitHub repository
- **Email**: support@veripay.et

## 🎉 Success!

Your VeriPay bot is now ready with:
- ✅ Cloud hosting
- ✅ Database storage
- ✅ Telegram integration
- ✅ Payment processing
- ✅ Admin dashboard

Start using it today! 🚀 