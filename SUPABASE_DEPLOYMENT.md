# VeriPay Bot - Supabase Deployment Guide

This guide will help you deploy the VeriPay bot to a free cloud platform with Supabase as the database.

## 🎯 Overview

We'll deploy to **Railway** (free tier) with **Supabase** (free PostgreSQL database) for a complete cloud solution.

## 📋 Prerequisites

1. **GitHub Account** - For code repository
2. **Railway Account** - For hosting (free tier)
3. **Supabase Account** - For database (free tier)
4. **Telegram Bot Token** - From @BotFather

## 🗄️ Step 1: Set Up Supabase Database

### 1.1 Create Supabase Account
1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign up with GitHub
4. Create a new organization

### 1.2 Create New Project
1. Click "New Project"
2. Choose your organization
3. Enter project details:
   - **Name:** `veripay-bot`
   - **Database Password:** Generate a strong password
   - **Region:** Choose closest to your users
4. Click "Create new project"

### 1.3 Get Database Connection String
1. Go to **Settings** → **Database**
2. Copy the **Connection string** (URI format)
3. It looks like: `postgresql://postgres:[password]@[host]:5432/postgres`

### 1.4 Create Database Tables
1. Go to **SQL Editor**
2. Run the following SQL to create tables:

```sql
-- Create tables for VeriPay
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'waiter',
    restaurant_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address TEXT,
    owner_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tables (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id),
    table_number VARCHAR(20) NOT NULL,
    capacity INTEGER DEFAULT 4,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS table_assignments (
    id SERIAL PRIMARY KEY,
    table_id INTEGER REFERENCES tables(id),
    waiter_id VARCHAR(50),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    waiter_id VARCHAR(50),
    restaurant_id INTEGER REFERENCES restaurants(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ETB',
    transaction_id VARCHAR(100),
    bank_name VARCHAR(50),
    verification_status VARCHAR(20) DEFAULT 'pending',
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bank_statements (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id),
    statement_date DATE,
    total_amount DECIMAL(10,2),
    transaction_count INTEGER,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reconciliation_reports (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id),
    report_date DATE,
    total_transactions INTEGER,
    verified_transactions INTEGER,
    pending_transactions INTEGER,
    total_amount DECIMAL(10,2),
    report_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(10),
    message TEXT,
    user_id VARCHAR(50),
    action VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_transactions_waiter_id ON transactions(waiter_id);
CREATE INDEX idx_transactions_restaurant_id ON transactions(restaurant_id);
CREATE INDEX idx_transactions_status ON transactions(verification_status);
```

## 🚀 Step 2: Deploy to Railway

### 2.1 Prepare Your Code
1. Make sure your code is in a GitHub repository
2. Ensure these files are in your repo:
   - `veripay_supabase_bot.py`
   - `requirements_supabase.txt`
   - `railway_supabase.json`
   - `Procfile_supabase`
   - `runtime_supabase.txt`
   - `database/lean_models.py`
   - `database/lean_operations.py`

### 2.2 Connect Railway to GitHub
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your VeriPay repository

### 2.3 Configure Environment Variables
In Railway dashboard, go to **Variables** and add:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=your_supabase_connection_string
ADMIN_USER_ID=your_telegram_user_id
DEBUG=false
TEST_MODE=false
```

### 2.4 Deploy
1. Railway will automatically detect the Python project
2. It will install dependencies from `requirements_supabase.txt`
3. Start the bot using the command in `Procfile_supabase`

## 🔧 Step 3: Alternative Platforms

### Render (Alternative to Railway)
1. Go to [render.com](https://render.com)
2. Create account and connect GitHub
3. Create new **Web Service**
4. Use these settings:
   - **Build Command:** `pip install -r requirements_supabase.txt`
   - **Start Command:** `python3 veripay_supabase_bot.py`
   - **Environment Variables:** Same as Railway

### Fly.io (Alternative)
1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Create app: `fly launch`
4. Deploy: `fly deploy`

## 🧪 Step 4: Testing

### 4.1 Test Bot Commands
1. Find your bot on Telegram: `@your_bot_username`
2. Send `/start`
3. Test registration flow
4. Test payment upload
5. Test admin features

### 4.2 Check Logs
- **Railway:** Go to project → Deployments → View logs
- **Render:** Go to service → Logs
- **Fly.io:** `fly logs`

### 4.3 Monitor Database
- Go to Supabase dashboard
- Check **Table Editor** for data
- Monitor **Logs** for errors

## 🔍 Step 5: Troubleshooting

### Common Issues

#### Bot Not Responding
1. Check if bot is running (logs)
2. Verify `TELEGRAM_BOT_TOKEN` is correct
3. Ensure bot hasn't been blocked

#### Database Connection Errors
1. Verify `DATABASE_URL` format
2. Check Supabase project is active
3. Ensure tables were created

#### OCR Not Working
1. Tesseract is installed in cloud environment
2. Check image format (JPG/PNG)
3. Verify image quality

#### Deployment Fails
1. Check `requirements_supabase.txt` for conflicts
2. Verify Python version in `runtime_supabase.txt`
3. Check build logs for errors

### Debug Mode
Set `DEBUG=true` in environment variables for detailed logs.

## 📊 Step 6: Monitoring

### Health Checks
- Bot responds to `/start`
- Database queries work
- OCR processing functions

### Performance Metrics
- Response time < 2 seconds
- Database queries < 500ms
- OCR processing < 10 seconds

### Cost Monitoring
- **Supabase:** Free tier includes 500MB database
- **Railway:** Free tier includes 500 hours/month
- Monitor usage in respective dashboards

## 🔄 Step 7: Updates

### Code Updates
1. Push changes to GitHub
2. Railway/Render will auto-deploy
3. Monitor logs for any issues

### Database Migrations
1. Update SQL schema in Supabase
2. Test with development data
3. Apply to production carefully

## 📞 Support

### Getting Help
- **Documentation:** Check this guide
- **Logs:** Check platform logs
- **Community:** GitHub Issues
- **Email:** support@veripay.et

### Emergency Contacts
- **Railway Support:** [railway.app/support](https://railway.app/support)
- **Supabase Support:** [supabase.com/support](https://supabase.com/support)

## 🎉 Success!

Your VeriPay bot is now deployed with:
- ✅ Free cloud hosting
- ✅ Free PostgreSQL database
- ✅ Auto-scaling
- ✅ SSL certificates
- ✅ Global CDN
- ✅ 99.9% uptime

The bot is ready for production use! 