# VeriPay Telegram Bot

A comprehensive Telegram-based payment and reconciliation bot designed for restaurants in Ethiopia. The bot streamlines waiter transactions, automates reconciliation with bank statements, and provides admins with oversight for approvals and system updates.

## 🚀 Features

### Current Implementation (Milestone 1)

#### **User Roles & Authentication**
- **Super Admin**: Approves restaurant registrations, manages system-wide settings
- **Restaurant Admin**: Manages restaurant data, approves waiters, handles reconciliation
- **Waiter**: Records transactions via photo capture, views personal transaction history

#### **Waiter Functionality**
- ✅ **Registration**: Waiters register with name, phone, and restaurant selection
- ✅ **Photo Capture**: Upload receipt photos for automatic transaction extraction
- ✅ **OCR Processing**: Extracts payment data using Google Vision API
- ✅ **Transaction History**: View personal transaction records
- ✅ **Multi-language Support**: English + Amharic interface

#### **Restaurant Admin Functionality**
- ✅ **Restaurant Registration**: Register new restaurants with approval workflow
- ✅ **Waiter Management**: Approve/reject waiter registrations
- ✅ **Transaction Oversight**: View all restaurant transactions
- ✅ **Dashboard**: Comprehensive admin panel with inline keyboard navigation

#### **Super Admin Functionality**
- ✅ **Restaurant Approval**: Approve/reject restaurant registrations
- ✅ **System Management**: Global oversight and system health monitoring
- ✅ **Audit Logging**: Complete action tracking with timestamps

### **Transaction Processing**
- ✅ **Automatic OCR**: Extracts amount, transaction ID, payer, receiver, bank info
- ✅ **Bank Support**: Dashen Bank, CBE, Telebirr, and generic bank support
- ✅ **Fallback Data**: Testing mode with sample data when OCR fails
- ✅ **Real-time Processing**: Immediate transaction recording and confirmation

## 🛠️ Technical Stack

- **Platform**: Python 3.12 + python-telegram-bot
- **OCR**: Google Vision API for receipt text extraction
- **Database**: In-memory storage (PostgreSQL integration planned)
- **Authentication**: Telegram User ID-based
- **Deployment**: Local development with polling

## 📋 Setup Instructions

### Prerequisites
```bash
pip install python-telegram-bot google-cloud-vision aiohttp
```

### Environment Variables
```bash
export BOT_TOKEN="your_telegram_bot_token"
export GOOGLE_APPLICATION_CREDENTIALS="path_to_google_credentials.json"
export SUPER_ADMIN_USER_ID="your_telegram_user_id"
```

### Running the Bot
```bash
python3 veripay_bot.py
```

## 🎯 Usage Guide

### For Waiters
1. **Start**: Send `/start` to the bot
2. **Register**: Click "🍳 Waiter Registration"
3. **Provide Details**: Enter name, phone, select restaurant
4. **Capture Payments**: Use "📸 Capture Payment" to upload receipt photos
5. **View History**: Check "📊 My Transactions" for transaction records

### For Restaurant Admins
1. **Register Restaurant**: Complete restaurant registration form
2. **Wait for Approval**: Super Admin will approve your restaurant
3. **Manage Waiters**: Approve/reject waiter registrations
4. **Monitor Transactions**: View all restaurant transaction data

### For Super Admins
1. **Admin Access**: Use `/admin` command
2. **Approve Restaurants**: Review and approve restaurant registrations
3. **System Oversight**: Monitor all system activities

## 🔧 Current Status

### ✅ Completed Features
- [x] User role-based authentication system
- [x] Waiter registration and approval workflow
- [x] Restaurant registration and approval workflow
- [x] Photo-based transaction capture with OCR
- [x] Multi-bank receipt processing (Dashen, CBE, Telebirr)
- [x] Inline keyboard navigation for all user types
- [x] Automatic menu display after registration/approval
- [x] Comprehensive audit logging
- [x] Error handling and fallback mechanisms

### 🚧 In Progress
- [ ] Database integration (PostgreSQL)
- [ ] Bank statement reconciliation
- [ ] CSV export functionality
- [ ] Advanced reporting features

### 📋 Planned Features
- [ ] Multi-language UI (Amharic + English)
- [ ] Advanced analytics and insights
- [ ] Payment provider integrations
- [ ] Offline mode with sync capabilities

## 🏗️ Architecture

### Core Components
- **VeriPayBot**: Main bot class handling all interactions
- **User Management**: Role-based access control system
- **OCR Engine**: Google Vision API integration for receipt processing
- **Transaction System**: Real-time transaction recording and storage
- **Approval Workflows**: Multi-level approval system for users and restaurants

### Data Flow
1. **Waiter Registration**: User → Bot → Restaurant Admin Approval
2. **Transaction Capture**: Photo → OCR → Data Extraction → Storage
3. **Restaurant Registration**: Admin → Bot → Super Admin Approval
4. **Approval Notifications**: Bot → Relevant Admin → Action Required

## 🔒 Security Features

- **Role-based Access**: Strict separation between waiter, admin, and super admin
- **Telegram Authentication**: Uses Telegram User ID for secure access
- **Audit Logging**: Complete action tracking for compliance
- **Input Validation**: Comprehensive error handling and validation
- **No Password System**: Secure Telegram-based authentication only

## 📊 Testing

### Manual Testing Checklist
- [x] Waiter registration flow
- [x] Restaurant registration and approval
- [x] Photo upload and OCR processing
- [x] Menu navigation and user experience
- [x] Error handling and edge cases
- [x] Multi-user concurrent access

### Test Scenarios
1. **New Waiter**: Register → Get Approved → Capture Payment → View History
2. **New Restaurant**: Register → Get Approved → Approve Waiters → Monitor Transactions
3. **Super Admin**: Approve Restaurants → Monitor System → Manage Users

## 🚀 Deployment

### Development
- Uses polling for updates
- Single bot instance enforcement
- Local logging and error handling

### Production (Planned)
- Webhook-based updates
- Process manager (systemd/supervisor)
- Database integration
- Cloud deployment (AWS/DigitalOcean)

## 📝 API Reference

### Bot Commands
- `/start` - Initialize bot and show role selection
- `/admin` - Super admin access (restricted)

### Callback Data
- `register_waiter` - Start waiter registration
- `register_restaurant` - Start restaurant registration
- `capture_payment` - Begin payment capture flow
- `restaurant_pending_waiters` - View pending waiter approvals

## 🤝 Contributing

This project follows the VeriPay PRD as the single source of truth. All changes must:
- Follow the established role-based access patterns
- Include comprehensive error handling
- Maintain audit logging
- Pass all existing tests

## 📄 License

Private project - All rights reserved.

---

**Status**: ✅ Fully Functional for Milestone 1
**Last Updated**: September 12, 2025
**Version**: 1.0.0
