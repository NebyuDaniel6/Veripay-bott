# VeriPay Bot Deployment Guide

## 🚀 Production-Ready Deployment

### Features Included
- ✅ Multi-format OCR for all Ethiopian mobile payments
- ✅ Enhanced PDF reports with complete transaction data
- ✅ Login system with Telegram ID authentication
- ✅ Admin panel with waiter management
- ✅ Real-time transaction tracking
- ✅ Comprehensive error handling

### Deployment Options

#### Option 1: Railway (Recommended)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

#### Option 2: Render
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Use the provided `render.yaml` configuration
4. Deploy automatically

#### Option 3: Heroku
```bash
# Install Heroku CLI
# Login and create app
heroku login
heroku create veripay-bot

# Set environment variables
heroku config:set BOT_TOKEN=8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc
heroku config:set GOOGLE_VISION_API_KEY=AIzaSyC4ESpSW_c1ijlLGwTUQ5wdBhflQOPps6M

# Deploy
git push heroku main
```

### Environment Variables
- `BOT_TOKEN`: Your Telegram bot token
- `GOOGLE_VISION_API_KEY`: Google Vision API key for OCR

### Supported Payment Formats
- Commercial Bank of Ethiopia (CBE)
- Telebirr
- Dashen Bank
- Bank of Abyssinia
- Awash Bank
- Nib Bank, Zemen Bank, Hibret Bank
- Wegagen Bank, United Bank, Berhan Bank
- And many more Ethiopian banks and mobile payment providers

### Bot Commands
- `/start` - Start the bot
- `/register` - Register as waiter or admin
- Upload receipt image - Process payment
- Admin panel - Manage waiters and view reports

### Testing
1. Send `/start` to @Verifpay_bot
2. Register as waiter or admin
3. Upload a receipt image
4. Check PDF reports for complete data extraction

### Support
The bot is now production-ready with comprehensive OCR support for all Ethiopian mobile payment formats!
