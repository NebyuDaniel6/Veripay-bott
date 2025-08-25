# VeriPay Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.8+
- PostgreSQL
- Telegram Bot Tokens (from @BotFather)

### 1. Clone and Setup
```bash
cd ~/veripay
python setup.py
```

### 2. Configure Environment
Edit `config.yaml` with your bot tokens:
```yaml
telegram:
  waiter_bot_token: "YOUR_WAITER_BOT_TOKEN"
  admin_bot_token: "YOUR_ADMIN_BOT_TOKEN"
```

### 3. Start the Bots
```bash
# Option 1: Run both bots together
python run_bots.py

# Option 2: Run separately
python bots/waiter_bot.py &
python bots/admin_bot.py &
```

### 4. Test the System
1. Send `/start` to your waiter bot
2. Upload a payment screenshot
3. Check verification results

## 🐳 Docker Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📱 Bot Commands

### Waiter Bot
- `/start` - Initialize bot
- `/upload` - Upload payment screenshot
- `/help` - Show help

### Admin Bot
- `/start` - Initialize admin panel
- `/dashboard` - View system overview
- `/transactions` - View recent transactions
- `/statement` - Upload bank statement
- `/report` - Generate audit report
- `/waiters` - Manage waiters

## 🔧 Configuration

### Environment Variables
```bash
export WAITER_BOT_TOKEN="your_waiter_bot_token"
export ADMIN_BOT_TOKEN="your_admin_bot_token"
export DATABASE_URL="postgresql://user:pass@localhost:5432/veripay"
```

### Bank API Configuration
Edit `config.yaml` to enable bank APIs:
```yaml
banks:
  cbe:
    enabled: true
    api_key: "your_cbe_api_key"
  telebirr:
    enabled: true
    api_key: "your_telebirr_api_key"
```

## 📊 Monitoring

### Logs
- Application logs: `logs/veripay.log`
- Waiter bot logs: `logs/waiter_bot.log`
- Admin bot logs: `logs/admin_bot.log`

### Health Check
```bash
# Check bot status
curl http://localhost:8000/health

# Check database
python -c "from database.operations import DatabaseManager; print('DB OK')"
```

## 🧪 Testing

```bash
# Run tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_basic.py::TestOCRExtractor -v
```

## 📈 Production Deployment

### 1. Environment Setup
```bash
# Set production environment
export ENVIRONMENT=production
export DEBUG=false
```

### 2. Database Setup
```bash
# Create production database
createdb veripay_prod

# Run migrations
python -c "from database.models import Base, engine; Base.metadata.create_all(engine)"
```

### 3. SSL/HTTPS Setup
```bash
# Generate SSL certificates
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Configure nginx
cp nginx/nginx.conf.example nginx/nginx.conf
```

### 4. Start Production Services
```bash
# Start with Docker
docker-compose -f docker-compose.prod.yml up -d

# Or start manually
python run_bots.py
```

## 🔒 Security Checklist

- [ ] Change default database passwords
- [ ] Set strong encryption keys
- [ ] Configure firewall rules
- [ ] Enable SSL/TLS
- [ ] Set up regular backups
- [ ] Monitor access logs
- [ ] Update dependencies regularly

## 🆘 Troubleshooting

### Common Issues

**Bot not responding:**
```bash
# Check bot token
python -c "import requests; print(requests.get('https://api.telegram.org/bot<TOKEN>/getMe').json())"
```

**Database connection error:**
```bash
# Check PostgreSQL
sudo systemctl status postgresql
psql -U veripay_user -d veripay -c "SELECT 1;"
```

**OCR not working:**
```bash
# Check Tesseract
tesseract --version
# Install if missing: sudo apt-get install tesseract-ocr
```

**Docker issues:**
```bash
# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Getting Help

1. Check logs: `tail -f logs/veripay.log`
2. Review documentation: `README.md`
3. Run tests: `python -m pytest tests/`
4. Contact support: support@veripay.et

## 📞 Support

- **Documentation**: README.md
- **Issues**: Create GitHub issue
- **Email**: support@veripay.et
- **Telegram**: @veripay_support

---

**VeriPay** - Making payments trustworthy, one verification at a time! 💳✅ 