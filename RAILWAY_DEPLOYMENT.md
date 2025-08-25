# 🚀 VeriPay Bot - Railway Deployment Guide

## 📋 **Prerequisites**

1. **GitHub Account** - To host your code
2. **Railway Account** - For deployment (free tier available)
3. **Telegram Bot Token** - From @BotFather

---

## 🚀 **Quick Deployment Steps**

### **Step 1: Prepare Your Code**

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial VeriPay bot deployment"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/veripay-bot.git
   git push -u origin main
   ```

### **Step 2: Deploy to Railway**

1. **Go to [Railway.app](https://railway.app)**
2. **Sign up/Login** with GitHub
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Choose your repository**
6. **Railway will automatically detect Python and deploy**

### **Step 3: Configure Environment Variables**

In Railway dashboard, go to your project and add these environment variables:

```bash
BOT_TOKEN=8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc
ADMIN_USER_ID=123456789
DATABASE_URL=sqlite:///lean_veripay.db
LOG_LEVEL=INFO
OCR_ENGINE=tesseract
OCR_CONFIDENCE=0.7
```

### **Step 4: Deploy**

1. **Railway will automatically deploy** when you push to GitHub
2. **Check the logs** in Railway dashboard
3. **Your bot will be live** at the provided URL

---

## 🔧 **Configuration**

### **Environment Variables**

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token | Required |
| `ADMIN_USER_ID` | Admin user ID | 123456789 |
| `DATABASE_URL` | Database connection | sqlite:///lean_veripay.db |
| `LOG_LEVEL` | Logging level | INFO |
| `OCR_ENGINE` | OCR engine to use | tesseract |
| `OCR_CONFIDENCE` | OCR confidence threshold | 0.7 |

### **Railway Configuration**

The `railway.json` file configures:
- **Builder:** NIXPACKS (automatic Python detection)
- **Start Command:** `python3 lean_veripay_bot_cloud.py`
- **Health Check:** `/health` endpoint
- **Restart Policy:** Automatic restart on failure

---

## 📊 **Monitoring**

### **Railway Dashboard**
- **Logs:** Real-time application logs
- **Metrics:** CPU, memory, network usage
- **Deployments:** Deployment history and status
- **Environment:** Environment variables management

### **Health Checks**
Railway automatically checks:
- Application startup
- Health endpoint response
- Resource usage

---

## 🔍 **Troubleshooting**

### **Common Issues**

1. **Build Fails**
   ```bash
   # Check requirements.txt
   # Ensure all dependencies are listed
   # Check Python version in runtime.txt
   ```

2. **Bot Not Responding**
   ```bash
   # Check BOT_TOKEN environment variable
   # Verify bot token is valid
   # Check Railway logs for errors
   ```

3. **Database Issues**
   ```bash
   # SQLite is included by default
   # For PostgreSQL, add DATABASE_URL
   # Check database permissions
   ```

4. **OCR Not Working**
   ```bash
   # Tesseract is not available on Railway
   # Use cloud OCR services instead
   # Or disable OCR features
   ```

### **Logs**
```bash
# View logs in Railway dashboard
# Or use Railway CLI
railway logs
```

---

## 🚀 **Advanced Configuration**

### **Custom Domain**
1. Go to Railway dashboard
2. Click on your project
3. Go to "Settings" → "Domains"
4. Add your custom domain

### **Database (PostgreSQL)**
1. Add PostgreSQL service in Railway
2. Update `DATABASE_URL` environment variable
3. Update database configuration in code

### **Scaling**
- **Free Tier:** 1 instance
- **Pro Plan:** Multiple instances
- **Auto-scaling:** Based on traffic

---

## 📱 **Testing Your Deployment**

### **Bot Testing**
1. **Open Telegram**
2. **Search for your bot** (@YourBotName)
3. **Send `/start`**
4. **Test all features**

### **Health Check**
```bash
# Your bot URL will be something like:
# https://your-app-name.railway.app
curl https://your-app-name.railway.app/health
```

---

## 💰 **Pricing**

### **Free Tier**
- ✅ **500 hours/month** (enough for 24/7 bot)
- ✅ **512MB RAM**
- ✅ **1GB storage**
- ✅ **Custom domains**
- ✅ **SSL certificates**

### **Pro Plan** ($5/month)
- ✅ **Unlimited hours**
- ✅ **More resources**
- ✅ **Priority support**
- ✅ **Advanced features**

---

## 🔄 **Updates**

### **Automatic Deployments**
- **Push to GitHub** → **Automatic deployment**
- **No downtime** during updates
- **Rollback** to previous version if needed

### **Manual Deployments**
```bash
# Using Railway CLI
railway up
```

---

## 📞 **Support**

### **Railway Support**
- **Documentation:** [docs.railway.app](https://docs.railway.app)
- **Discord:** [Railway Discord](https://discord.gg/railway)
- **Email:** support@railway.app

### **Bot Issues**
- Check Railway logs
- Verify environment variables
- Test bot token
- Review code for errors

---

## 🎉 **Success!**

Your VeriPay bot is now:
- ✅ **Deployed on Railway**
- ✅ **Running 24/7**
- ✅ **Auto-scaling**
- ✅ **SSL secured**
- ✅ **Monitoring enabled**

**Bot URL:** https://t.me/YourBotName
**Railway URL:** https://your-app-name.railway.app

---

**🚀 Ready for Production!** 