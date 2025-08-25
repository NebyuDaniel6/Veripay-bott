# 🚀 VeriPay Bot - Render Deployment Guide

## 🆓 **Free Deployment on Render**

Render offers a generous free tier perfect for Telegram bots!

---

## 📋 **Prerequisites**

1. **GitHub Account** - To host your code
2. **Render Account** - For deployment (free)
3. **Telegram Bot Token** - From @BotFather

---

## 🚀 **Quick Deployment Steps**

### **Step 1: Push to GitHub**
```bash
# Your code is already on GitHub at:
# https://github.com/NebyuDaniel6/Veripay-bott
```

### **Step 2: Deploy to Render**
1. **Go to [Render.com](https://render.com)**
2. **Sign up/Login** with GitHub
3. **Click "New +"**
4. **Select "Web Service"**
5. **Connect your GitHub repository**
6. **Choose:** `NebyuDaniel6/Veripay-bott`

### **Step 3: Configure Service**
- **Name:** `veripay-bot`
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python3 lean_veripay_bot_cloud.py`
- **Plan:** `Free`

### **Step 4: Set Environment Variables**
In Render dashboard, add:
```bash
BOT_TOKEN=8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc
ADMIN_USER_ID=123456789
DATABASE_URL=sqlite:///lean_veripay.db
LOG_LEVEL=INFO
OCR_ENGINE=tesseract
OCR_CONFIDENCE=0.7
```

### **Step 5: Deploy**
- **Click "Create Web Service"**
- **Render will automatically deploy**
- **Your bot will be live** at the provided URL

---

## 💰 **Render Free Tier Benefits**

### **What You Get:**
- ✅ **750 hours/month** (enough for 24/7 bot)
- ✅ **512MB RAM**
- ✅ **1GB storage**
- ✅ **Custom domains**
- ✅ **SSL certificates**
- ✅ **Automatic deployments**
- ✅ **No credit card required**

### **Limitations:**
- ⏰ **Sleeps after 15 minutes** of inactivity
- 🔄 **Takes 30 seconds** to wake up
- 📊 **Limited bandwidth** (but enough for bots)

---

## 🔧 **Configuration**

### **Environment Variables**
| Variable | Description | Value |
|----------|-------------|-------|
| `BOT_TOKEN` | Telegram bot token | Your bot token |
| `ADMIN_USER_ID` | Admin user ID | 123456789 |
| `DATABASE_URL` | Database connection | sqlite:///lean_veripay.db |
| `LOG_LEVEL` | Logging level | INFO |
| `OCR_ENGINE` | OCR engine | tesseract |
| `OCR_CONFIDENCE` | OCR confidence | 0.7 |

### **Auto-Deploy Settings**
- ✅ **Auto-deploy** on push to main branch
- ✅ **Branch:** `main`
- ✅ **Root Directory:** `/` (root)

---

## 📊 **Monitoring**

### **Render Dashboard**
- **Logs:** Real-time application logs
- **Metrics:** CPU, memory usage
- **Deployments:** Deployment history
- **Environment:** Environment variables

### **Health Checks**
- **URL:** Your bot's URL
- **Status:** 200 OK when running
- **Uptime:** 99.9% (when not sleeping)

---

## 🔍 **Troubleshooting**

### **Common Issues**
1. **Build Fails**
   - Check `requirements.txt`
   - Verify Python version
   - Check build logs

2. **Bot Not Responding**
   - Check `BOT_TOKEN`
   - Verify environment variables
   - Check application logs

3. **Sleep Issues**
   - Bot sleeps after 15 minutes inactive
   - Takes 30 seconds to wake up
   - Normal for free tier

### **Logs**
```bash
# View logs in Render dashboard
# Or use Render CLI
render logs --service veripay-bot
```

---

## 🚀 **Advanced Features**

### **Custom Domain**
1. Go to Render dashboard
2. Click on your service
3. Go to "Settings" → "Custom Domains"
4. Add your domain

### **Database (Optional)**
1. Add PostgreSQL service in Render
2. Update `DATABASE_URL` environment variable
3. Update database configuration

---

## 📱 **Testing Your Deployment**

### **Bot Testing**
1. **Open Telegram**
2. **Search for your bot** (@Verifpay_bot)
3. **Send `/start`**
4. **Test all features**

### **Health Check**
```bash
# Your bot URL will be something like:
# https://veripay-bot.onrender.com
curl https://veripay-bot.onrender.com
```

---

## 🎉 **Success!**

Your VeriPay bot will be:
- ✅ **Deployed on Render** (free)
- ✅ **Running 24/7** (with sleep/wake)
- ✅ **Auto-scaling**
- ✅ **SSL secured**
- ✅ **Monitoring enabled**

**Bot URL:** https://t.me/Verifpay_bot
**Render URL:** https://veripay-bot.onrender.com

---

**🚀 Ready for Free Deployment on Render!** 