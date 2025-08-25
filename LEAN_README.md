# VeriPay - Lean Model

A unified Telegram bot-based payment verification system for restaurants in Ethiopia. Single bot with role-based access for waiters and admins.

## 🎯 Overview

VeriPay ensures that mobile payments (CBE, Dashen, Telebirr) are real by:
- Automatically capturing transaction details from screenshots
- Verifying them with OCR and QR code scanning
- Preparing daily reconciled reports for admins
- Providing a simple, lean, scalable system

## 🏗️ Architecture

### Single Bot Design
- **One bot** handles both waiters and admins
- **Role-based access** using Telegram user IDs
- **Button interfaces** for easy navigation
- **Inline keyboards** for quick actions

### User Roles

#### 👨‍💼 Waiter
- **One-time registration:** Name, phone, Telegram username, assigned table(s)
- **Capture Payment Proof:** Take live photo of customer's payment screenshot
- **Automatic extraction:** STN, amount, date/time, payment method
- **QR verification:** Cross-verify STN, amount, and timestamp
- **Minimal effort:** Just tap and capture

#### 👨‍💼 Admin/Manager
- **Dashboard:** View system overview and statistics
- **Daily summary:** Number of transactions, total amounts per waiter, breakdown by payment method
- **Upload PDF:** Bank statement for daily reconciliation
- **Audit:** Compare captured photos & extracted data vs bank PDF totals
- **Export reports:** CSV/PDF of daily transactions
- **Manage users:** Register waiters, reassign tables

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Install Python 3.8+
python3 --version

# Install Tesseract OCR
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# macOS:
brew install tesseract

# Windows:
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### 2. Setup
```bash
# Clone the repository
git clone <repository-url>
cd veripay

# Install dependencies
pip install -r lean_requirements.txt

# Run setup
python lean_setup.py

# Update bot token in config.yaml
# Get token from @BotFather on Telegram
```

### 3. Run the Bot
```bash
python lean_veripay_bot.py
```

## 📱 Usage

### For Waiters

1. **Start the bot:** `/start`
2. **Capture payment:** `/capture` or use "📸 Capture Payment" button
3. **Take photo:** Live photo of customer's payment screenshot
4. **Review:** Check extracted transaction details
5. **Confirm:** Transaction is automatically saved and verified

### For Admins

1. **Start the bot:** `/start`
2. **Dashboard:** `/dashboard` - View system overview
3. **Daily summary:** `/summary` - View today's transactions
4. **Upload statement:** `/reconcile` - Upload bank PDF for reconciliation
5. **Manage waiters:** `/waiters` - Add/edit waiters and tables

## 🗄️ Database Schema

### Core Tables
- **users:** Unified table for waiters and admins
- **restaurants:** Restaurant information
- **tables:** Restaurant tables
- **table_assignments:** Links users to tables
- **transactions:** Payment verification records
- **bank_statements:** Uploaded bank statements
- **reconciliation_reports:** Generated audit reports

### Key Features
- **Simplified schema:** Only essential tables and fields
- **SQLite support:** Easy local development
- **PostgreSQL ready:** Production database support
- **Automatic timestamps:** Created/updated tracking

## 🔧 Configuration

### config.yaml
```yaml
telegram:
  waiter_bot_token: "YOUR_BOT_TOKEN"
  admin_bot_token: "YOUR_BOT_TOKEN"
  admin_user_ids: ["123456789"]

database:
  url: "sqlite:///lean_veripay.db"  # or PostgreSQL URL

ai:
  ocr_engine: "tesseract"
  confidence_threshold: 0.7

storage:
  upload_path: "./uploads"
  max_file_size_mb: 10
```

## 🎭 Demo Data

The setup script creates demo data for testing:

### Demo Users
- **Admin:** `123456789` - Full admin access
- **Waiters:** `111111111`, `222222222`, `333333333` - Payment capture access

### Demo Restaurant
- **Name:** Demo Restaurant
- **Tables:** 10 tables (T01-T10)
- **Transactions:** 5 sample transactions

## 🔍 Core Features

### OCR Processing
- **Real-time extraction:** STN, amount, date, sender/receiver
- **Multiple banks:** CBE, Telebirr, Dashen detection
- **Confidence scoring:** Quality assessment of extraction
- **Error handling:** Graceful fallback for poor images

### QR Code Verification
- **Instant validation:** Cross-verify STN, amount, timestamp
- **Tamper protection:** Detect manipulated screenshots
- **Real-time feedback:** Immediate verification results

### Admin Dashboard
- **Real-time stats:** Live transaction monitoring
- **Daily summaries:** Per-waiter and per-method breakdowns
- **Export capabilities:** CSV/PDF report generation
- **User management:** Waiter registration and table assignment

### Reconciliation
- **PDF upload:** Bank statement processing
- **Automatic matching:** Compare captured vs bank data
- **Discrepancy flagging:** Highlight mismatches
- **Audit reports:** Compliance-ready documentation

## 🛡️ Security Features

### Tamper Protection
- **Live photos only:** No pre-saved screenshots
- **QR verification:** Real-time payment validation
- **Timestamp checking:** Prevent replay attacks
- **Hash verification:** Duplicate detection

### Access Control
- **Role-based permissions:** Waiter vs admin access
- **Telegram ID validation:** Secure user identification
- **Session management:** Automatic timeout handling
- **Audit logging:** Complete activity tracking

## 📊 Reporting

### Daily Reports
- **Transaction summary:** Total count and amounts
- **Per-waiter breakdown:** Individual performance metrics
- **Payment method analysis:** CBE, Telebirr, Dashen distribution
- **Verification status:** Success/failure rates

### Audit Reports
- **Reconciliation results:** Bank statement matching
- **Discrepancy analysis:** Mismatched transactions
- **Fraud indicators:** Suspicious activity detection
- **Compliance documentation:** Audit-ready reports

## 🔄 Workflow

### Payment Verification Flow
1. Customer makes mobile payment
2. Waiter captures photo via bot
3. Bot extracts STN, amount, date/time, payment method
4. Bot scans QR code if present for verification
5. Data is stored and linked to waiter & table
6. Admin views daily summary
7. Admin uploads bank PDF for reconciliation
8. Bot flags mismatches and produces reports

### Admin Management Flow
1. Register waiters with Telegram IDs
2. Assign tables to waiters
3. Monitor daily transaction activity
4. Upload bank statements for reconciliation
5. Generate audit reports
6. Export data for accounting

## 🚀 Deployment

### Local Development
```bash
# Install dependencies
pip install -r lean_requirements.txt

# Setup database
python lean_setup.py

# Run bot
python lean_veripay_bot.py
```

### Production Deployment
```bash
# Use PostgreSQL for production
# Update config.yaml with production database URL

# Set up webhook (optional)
# Update webhook_url in config.yaml

# Use process manager (PM2, systemd, etc.)
pm2 start lean_veripay_bot.py --name veripay
```

## 🧪 Testing

### Demo Mode
The system includes demo data for testing:
- Sample transactions
- Demo users (admin and waiters)
- Test restaurant with tables

### Manual Testing
1. Use demo Telegram IDs to test different roles
2. Upload sample payment screenshots
3. Test admin dashboard and reporting
4. Verify reconciliation functionality

## 📈 Future Enhancements

### Optional Features
- **AI fraud detection:** Photoshop/fake screenshot detection
- **Video capture:** High-value payment verification
- **Analytics dashboard:** Weekly/monthly trends
- **Multi-branch support:** Multiple restaurant locations
- **Push notifications:** Real-time alerts for mismatches

### Scalability
- **Horizontal scaling:** Multiple bot instances
- **Load balancing:** Distribute user load
- **Caching:** Redis for performance optimization
- **Microservices:** Separate OCR and verification services

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation

## 🎉 Acknowledgments

- Telegram Bot API for the platform
- Tesseract OCR for text extraction
- SQLAlchemy for database management
- Ethiopian payment systems (CBE, Telebirr, Dashen) for integration

---

**VeriPay - Making payment verification simple, secure, and scalable for Ethiopian restaurants.** 