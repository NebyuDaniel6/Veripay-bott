# VeriPay Bot Deployment Guide

## 🚀 Quick Deployment

### Option 1: Using Deployment Script (Recommended)

```bash
# Start the bot
./deploy_veripay.sh start

# Check status
./deploy_veripay.sh status

# View logs
./deploy_veripay.sh logs

# Stop the bot
./deploy_veripay.sh stop

# Restart the bot
./deploy_veripay.sh restart
```

### Option 2: Manual Deployment

```bash
# Start the bot manually
nohup python3 lean_veripay_bot.py > logs/bot.log 2>&1 &

# Check if running
ps aux | grep lean_veripay_bot

# View logs
tail -f logs/bot.log
```

## 🔧 Systemd Service (macOS)

### Install Service
```bash
# Copy service file to systemd directory
sudo cp veripay-bot.service /Library/LaunchDaemons/

# Load and start the service
sudo launchctl load /Library/LaunchDaemons/veripay-bot.service
sudo launchctl start veripay-bot.service
```

### Service Commands
```bash
# Start service
sudo launchctl start veripay-bot.service

# Stop service
sudo launchctl stop veripay-bot.service

# Check status
sudo launchctl list | grep veripay-bot

# Unload service
sudo launchctl unload /Library/LaunchDaemons/veripay-bot.service
```

## 📊 Monitoring

### Check Bot Status
```bash
# Using deployment script
./deploy_veripay.sh status

# Manual check
ps aux | grep lean_veripay_bot
```

### View Logs
```bash
# Live logs
./deploy_veripay.sh logs

# Recent logs
tail -n 50 logs/bot.log

# Search for errors
grep -i error logs/bot.log
```

### Bot Health Check
```bash
# Check if bot responds
curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
```

## 🔍 Troubleshooting

### Common Issues

1. **Bot not starting**
   ```bash
   # Check dependencies
   pip3 install -r requirements.txt
   
   # Check Python version
   python3 --version
   
   # Check bot token
   cat config.yaml | grep bot_token
   ```

2. **Permission errors**
   ```bash
   # Fix permissions
   chmod +x deploy_veripay.sh
   chmod 755 logs/
   chmod 755 uploads/
   chmod 755 reports/
   ```

3. **Database errors**
   ```bash
   # Recreate database
   rm -f lean_veripay.db
   python3 lean_setup.py
   ```

4. **OCR not working**
   ```bash
   # Install Tesseract
   brew install tesseract
   
   # Test OCR
   tesseract --version
   ```

### Log Analysis
```bash
# View recent errors
grep -i error logs/bot.log | tail -10

# View callback errors
grep -i callback logs/bot.log | tail -10

# View registration activity
grep -i registration logs/bot.log | tail -10
```

## 🌐 Production Deployment

### Environment Setup
```bash
# Set environment variables
export VERIPAY_ENV=production
export VERIPAY_LOG_LEVEL=INFO

# Create production config
cp config.yaml config.prod.yaml
# Edit config.prod.yaml with production settings
```

### Security Checklist
- [ ] Bot token is secure
- [ ] Database is properly configured
- [ ] Log files are rotated
- [ ] File permissions are correct
- [ ] Firewall rules are set
- [ ] SSL certificates are valid

### Backup Strategy
```bash
# Backup database
cp lean_veripay.db backups/lean_veripay_$(date +%Y%m%d_%H%M%S).db

# Backup logs
tar -czf backups/logs_$(date +%Y%m%d_%H%M%S).tar.gz logs/

# Backup config
cp config.yaml backups/config_$(date +%Y%m%d_%H%M%S).yaml
```

## 📱 Testing the Deployment

### Test Commands
```bash
# Test bot response
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/sendMessage" \
  -d "chat_id=<YOUR_CHAT_ID>&text=Test message"

# Test webhook (if using)
curl -X POST "https://your-domain.com/webhook" \
  -H "Content-Type: application/json" \
  -d '{"update_id":123,"message":{"text":"/start"}}'
```

### User Testing Checklist
- [ ] Bot responds to /start
- [ ] Registration works
- [ ] Role-based access works
- [ ] Payment capture works
- [ ] Admin features work
- [ ] Logout works
- [ ] Error handling works

## 🔄 Updates and Maintenance

### Update Bot
```bash
# Stop bot
./deploy_veripay.sh stop

# Backup current version
cp lean_veripay_bot.py lean_veripay_bot.py.backup

# Update code
git pull origin main

# Restart bot
./deploy_veripay.sh start
```

### Monitor Performance
```bash
# Check memory usage
ps aux | grep lean_veripay_bot | awk '{print $6}'

# Check CPU usage
top -pid $(pgrep -f lean_veripay_bot)

# Check disk usage
du -sh logs/ uploads/ reports/
```

## 📞 Support

For deployment issues:
1. Check logs: `./deploy_veripay.sh logs`
2. Check status: `./deploy_veripay.sh status`
3. Review this guide
4. Check Telegram Bot API status
5. Contact development team

---

**VeriPay Bot v1.0** - Ready for Production! 🚀 