# 🚀 VeriPay Bot Deployment Instructions

## 📋 **Environment Variables for Render**

Copy and paste these into your Render dashboard → Environment tab:

```
BOT_TOKEN=8210288638:AAEbnIFytqruDzQX2IN1qdV8hAJllMhZC-Y
SUPER_ADMIN_ID=369249230
DATABASE_URL=postgresql://postgres:0938438262Neba#@db.rekvcdujfgdxwsjipzce.supabase.co:5432/postgres
GOOGLE_APPLICATION_CREDENTIALS=/opt/render/project/src/veripay-credentials.json
USE_WEBHOOK=1
PUBLIC_URL=https://your-app-name.onrender.com
PORT=10000
WEBHOOK_PATH=/webhook
LEGACY_UI=1
PERSISTENCE_V1=1
```

## �� **Files to Upload to Render**

1. **Upload these files to Render Environment → File Uploads:**
   - `veripay-credentials.json` (Google Cloud credentials)

2. **Deploy these files via GitHub or manual upload:**
   - `bot_v2/app.py` (with webhook support)
   - `bot_v2/storage.py`
   - `bot_v2/ui_legacy.py`
   - `bot_v2/state.py`
   - `bot_v2/ocr.py`
   - `requirements.txt`
   - `render.yaml`

## �� **Render Configuration**

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python bot_v2/app.py`
- **Python Version:** 3.11
- **Plan:** Free

## 🌐 **After Deployment**

1. **Get your Render app URL** (e.g., `https://veripay-bot.onrender.com`)

2. **Set the webhook:**
```bash
curl -X POST "https://api.telegram.org/bot8210288638:AAEbnIFytqruDzQX2IN1qdV8hAJllMhZC-Y/setWebhook" \
  -d "url=https://YOUR_APP_NAME.onrender.com/webhook"
```

3. **Test your bot** by sending `/start` to your Telegram bot

## ✅ **Success Indicators**

- ✅ Bot responds to `/start`
- ✅ All roles get correct dashboards
- ✅ Database operations work
- ✅ OCR functionality works
- ✅ Webhook receives updates

## 💰 **Cost: $0/month** (Free tiers)
