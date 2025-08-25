# VeriPay - Telegram Payment Verification System

A comprehensive Telegram-based payment verification system designed for restaurants, cafés, and service providers in Ethiopia to eliminate fake payment screenshots and provide real-time verification.

## 🎯 Overview

VeriPay solves the challenge of fake payment screenshots by:
- **AI-powered screenshot analysis** to detect manipulations
- **Bank API integration** for real-time verification
- **Automated audit reconciliation** with bank statements
- **Streamlined Telegram workflow** for waiters and admins

## 🏗️ Architecture

```
veripay/
├── bots/                 # Telegram bot implementations
│   ├── waiter_bot.py    # Frontend for waiters
│   └── admin_bot.py     # Admin interface
├── core/                # Core verification logic
│   ├── ocr_extractor.py # OCR and data extraction
│   ├── fraud_detector.py # AI-based tampering detection
│   ├── bank_verifier.py # Bank API integration
│   └── audit_engine.py  # Statement reconciliation
├── database/            # Database models and operations
│   ├── models.py        # SQLAlchemy models
│   └── operations.py    # Database operations
├── utils/               # Utility functions
│   ├── image_utils.py   # Image processing utilities
│   └── config.py        # Configuration management
├── tests/               # Test suite
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Docker setup
└── config.yaml         # Configuration file
```

## 🚀 Features

### For Waiters
- Upload payment screenshots via Telegram
- Automatic data extraction (STN, Amount, Date, Accounts)
- Real-time verification results
- Simple, intuitive interface

### For Admins
- Real-time verification alerts
- Search and filter transactions
- Bulk statement reconciliation
- Automated audit reports
- Override capabilities

### Verification Engine
- **AI-powered tampering detection** using computer vision
- **OCR extraction** of transaction details
- **Bank API integration** for CBE, Telebirr, Dashen
- **Statement reconciliation** every 3 days
- **Audit-ready reports** in PDF/Excel format

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- PostgreSQL
- Telegram Bot Tokens
- Bank API credentials (optional)

### Installation

1. **Clone and setup environment:**
```bash
git clone <repository>
cd veripay
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your bot tokens and database settings
```

3. **Setup database:**
```bash
python -c "from database.models import Base, engine; Base.metadata.create_all(engine)"
```

4. **Run the bots:**
```bash
# Terminal 1 - Waiter Bot
python bots/waiter_bot.py

# Terminal 2 - Admin Bot
python bots/admin_bot.py
```

### Docker Setup

```bash
docker-compose up -d
```

## 📊 Supported Payment Systems

- **CBE Birr** - Commercial Bank of Ethiopia
- **Telebirr** - Ethio Telecom mobile money
- **Dashen Bank** - Mobile banking
- **Other Ethiopian banks** - Extensible framework

## 🔒 Security Features

- AI-powered screenshot manipulation detection
- Bank API verification
- Audit trail for all transactions
- Encrypted data storage
- Role-based access control

## 📈 Success Metrics

- ✅ 90%+ fraud detection accuracy
- ✅ <10 sec average verification response time
- ✅ 100% audit reconciliation accuracy
- ✅ Adoption by 10+ restaurants in pilot phase

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Contact: support@veripay.et

---

**VeriPay** - Making payments trustworthy, one verification at a time. 💳✅ 