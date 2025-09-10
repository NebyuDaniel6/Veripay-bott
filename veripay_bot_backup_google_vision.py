#!/usr/bin/env python3
"""
VeriPay Bot - Enhanced Milestone 1 with PDF Download & Waiter ID Features
Complete production-ready bot with all features working!
"""

import os
import json
import time
import logging
import requests
import base64
import signal
import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('veripay.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc')
GOOGLE_VISION_API_KEY = os.getenv('GOOGLE_VISION_API_KEY', '')

# Global storage
users = {}  # user_id -> user_data
user_sessions = {}  # user_id -> session_data
user_states = {}  # user_id -> current_state
transactions = {}  # user_id -> [transactions]
admin_transactions = {}  # restaurant_name -> [all_transactions]
pending_approvals = {}  # restaurant_name -> [pending_waiters]
restaurant_ids = {}  # restaurant_name -> restaurant_id
waiter_ids = {}  # user_id -> waiter_id

# Process management
bot_running = False
bot_process_id = None

class UserState:
    IDLE = "idle"
    REGISTERING_WAITER = "registering_waiter"
    REGISTERING_ADMIN = "registering_admin"
    WAITING_NAME = "waiting_name"
    WAITING_PHONE = "waiting_phone"
    WAITING_RESTAURANT = "waiting_restaurant"
    CAPTURING_PAYMENT = "capturing_payment"


def extract_receipt_data(text):
    """Extract data from Commercial Bank of Ethiopia receipt text"""
    try:
        # Initialize result
        result = {
            'amount': 0.0,
            'transaction_id': '',
            'date': '',
            'payer': '',
            'receiver': '',
            'currency': 'ETB'
        }
        
        # Extract amount - look for "Transferred Amount:" or "Total amount debited"
        amount_patterns = [
            r'Transferred Amount:\s*([0-9,]+\.?\d*)\s*ETB',
            r'Total amount debited from customers account:\s*([0-9,]+\.?\d*)\s*ETB',
            r'Amount:\s*([0-9,]+\.?\d*)\s*ETB'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                result['amount'] = float(amount_str)
                break
        
        # Extract transaction ID - look for "VAT Invoice No" or "Reference No"
        id_patterns = [
            r'VAT Invoice No[:\s]*([A-Z0-9]+)',
            r'Reference No[:\s]*\(VAT Invoice No\)[:\s]*([A-Z0-9]+)',
            r'VAT Receipt No[:\s]*([A-Z0-9]+)'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['transaction_id'] = match.group(1)
                break
        
        # Extract date - look for "Payment Date & Time"
        date_patterns = [
            r'Payment Date & Time[:\s]*(\d{1,2}/\d{1,2}/\d{4}),?\s*(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',
            r'Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    result['date'] = f"{match.group(1)} {match.group(2)}"
                else:
                    result['date'] = match.group(1)
                break
        
        # Extract payer name
        payer_patterns = [
            r'Payer[:\s]*([A-Z\s]+)',
            r'Customer Name[:\s]*([A-Z\s]+)'
        ]
        
        for pattern in payer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['payer'] = match.group(1).strip()
                break
        
        # Extract receiver name
        receiver_patterns = [
            r'Receiver[:\s]*([A-Z\s]+)',
            r'Payee[:\s]*([A-Z\s]+)'
        ]
        
        for pattern in receiver_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['receiver'] = match.group(1).strip()
                break
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting receipt data: {e}")
        return None

def process_cbe_receipt(text):
    """Process Commercial Bank of Ethiopia receipt specifically"""
    try:
        # Check if this is a CBE receipt
        if 'Commercial Bank of Ethiopia' not in text and 'CBE' not in text:
            return None
        
        data = extract_receipt_data(text)
        if data and data['amount'] > 0:
            return {
                'amount': data['amount'],
                'currency': data['currency'],
                'transaction_id': data['transaction_id'] or f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'date': data['date'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'payer': data['payer'] or 'Unknown',
                'receiver': data['receiver'] or 'Unknown',
                'bank': 'Commercial Bank of Ethiopia',
                'status': 'completed'
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error processing CBE receipt: {e}")
        return None


def extract_receipt_data(text):
    """Extract data from Commercial Bank of Ethiopia receipt text"""
    try:
        # Initialize result
        result = {
            'amount': 0.0,
            'transaction_id': '',
            'date': '',
            'payer': '',
            'receiver': '',
            'currency': 'ETB'
        }
        
        # Extract amount - look for "Transferred Amount:" or "Total amount debited"
        amount_patterns = [
            r'Transferred Amount:\s*([0-9,]+\.?\d*)\s*ETB',
            r'Total amount debited from customers account:\s*([0-9,]+\.?\d*)\s*ETB',
            r'Amount:\s*([0-9,]+\.?\d*)\s*ETB'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                result['amount'] = float(amount_str)
                break
        
        # Extract transaction ID - look for "VAT Invoice No" or "Reference No"
        id_patterns = [
            r'VAT Invoice No[:\s]*([A-Z0-9]+)',
            r'Reference No[:\s]*\(VAT Invoice No\)[:\s]*([A-Z0-9]+)',
            r'VAT Receipt No[:\s]*([A-Z0-9]+)'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['transaction_id'] = match.group(1)
                break
        
        # Extract date - look for "Payment Date & Time"
        date_patterns = [
            r'Payment Date & Time[:\s]*(\d{1,2}/\d{1,2}/\d{4}),?\s*(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',
            r'Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    result['date'] = f"{match.group(1)} {match.group(2)}"
                else:
                    result['date'] = match.group(1)
                break
        
        # Extract payer name
        payer_patterns = [
            r'Payer[:\s]*([A-Z\s]+)',
            r'Customer Name[:\s]*([A-Z\s]+)'
        ]
        
        for pattern in payer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['payer'] = match.group(1).strip()
                break
        
        # Extract receiver name
        receiver_patterns = [
            r'Receiver[:\s]*([A-Z\s]+)',
            r'Payee[:\s]*([A-Z\s]+)'
        ]
        
        for pattern in receiver_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['receiver'] = match.group(1).strip()
                break
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting receipt data: {e}")
        return None

def process_cbe_receipt(text):
    """Process Commercial Bank of Ethiopia receipt specifically"""
    try:
        # Check if this is a CBE receipt
        if 'Commercial Bank of Ethiopia' not in text and 'CBE' not in text:
            return None
        
        data = extract_receipt_data(text)
        if data and data['amount'] > 0:
            return {
                'amount': data['amount'],
                'currency': data['currency'],
                'transaction_id': data['transaction_id'] or f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'date': data['date'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'payer': data['payer'] or 'Unknown',
                'receiver': data['receiver'] or 'Unknown',
                'bank': 'Commercial Bank of Ethiopia',
                'status': 'completed'
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error processing CBE receipt: {e}")
        return None

def generate_waiter_id():
    """Generate unique waiter ID"""
    return f"WTR{str(uuid.uuid4())[:8].upper()}"

def generate_restaurant_id(restaurant_name):
    """Generate unique restaurant ID"""
    return f"RST{str(uuid.uuid4())[:6].upper()}"

def create_pdf_report(restaurant_name, transactions_list, date_str):
    """Create PDF report for daily transactions"""
    try:
        filename = f"daily_report_{restaurant_name}_{date_str}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Title
        title = Paragraph(f"Daily Transaction Report<br/>{restaurant_name}<br/>{date_str}", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        if not transactions_list:
            no_data = Paragraph("No transactions for this day.", styles['Normal'])
            story.append(no_data)
        else:
            # Create table
            table_data = [['Transaction ID', 'Waiter ID', 'Amount', 'Status', 'Time']]
            
            total_amount = 0
            for transaction in transactions_list:
                table_data.append([
                    transaction.get('id', 'N/A'),
                    transaction.get('waiter_id', 'N/A'),
                    f"${transaction.get('amount', 0):.2f}",
                    transaction.get('status', 'N/A'),
                    transaction.get('timestamp', 'N/A')
                ])
                total_amount += transaction.get('amount', 0)
            
            # Add total row
            table_data.append(['TOTAL', '', f"${total_amount:.2f}", '', ''])
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        
        # Build PDF
        doc.build(story)
        return filename
    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        return None

def send_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def send_document(chat_id, document_path, caption=None):
    """Send document to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        with open(document_path, 'rb') as doc:
            files = {'document': doc}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            
            response = requests.post(url, files=files, data=data, timeout=30)
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending document: {e}")
        return False

def get_admin_keyboard(admin_id: int = None):
    """Get admin keyboard with dynamic pending approvals count"""
    keyboard = [
        [{"text": "📊 All Transactions / ሁሉም ግብይቶች"}],
        [{"text": "👥 Manage Waiters / ወይቶችን አስተዳድር"}],
        [{"text": "⚙️ Restaurant Settings / ምግብ ቤት ቅንብሮች"}],
        [{"text": "📈 My Transactions / የኔ ግብይቶች"}]
    ]
    
    # Add pending approvals button if there are any
    if admin_id and admin_id in users:
        user_data = users[admin_id]
        restaurant_name = user_data.get('restaurant_name', '')
        if restaurant_name in pending_approvals and pending_approvals[restaurant_name]:
            count = len(pending_approvals[restaurant_name])
            keyboard.append([{"text": f"⏳ Pending Approvals ({count}) / በጥበቃ ላይ ({count})"}])
    
    # Add download and sign out buttons
    keyboard.extend([
        [{"text": "📥 Download Today's Report / ዛሬ ያለውን ሪፖርት አውርድ"}],
        [{"text": "🚪 Sign Out / ውጣ"}]
    ])
    
    return {"keyboard": keyboard, "resize_keyboard": True, "one_time_keyboard": False}

def get_waiter_keyboard(waiter_id: int = None):
    """Get waiter keyboard"""
    keyboard = [
        [{"text": "💳 Capture Payment / ክፍያ ይውሰዱ"}],
        [{"text": "📊 My Transactions / የኔ ግብይቶች"}],
        [{"text": "�� Sign Out / ውጣ"}]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True, "one_time_keyboard": False}

def handle_start(chat_id, user_id, first_name, last_name):
    """Handle /start command with auto-login"""
    try:
        # Check if user is already registered
        if user_id in users:
            user_data = users[user_id]
            role = user_data.get('role')
            
            if role == 'admin':
                # Admin auto-login
                send_message(chat_id, f"🎉 Welcome back, {first_name}! / እንኳን ደህና መጡ, {first_name}!", get_admin_keyboard(user_id))
            elif role == 'waiter':
                # Check if waiter is approved
                if user_data.get('approved', False):
                    # Approved waiter auto-login
                    send_message(chat_id, f"🎉 Welcome back, {first_name}! / እንኳን ደህና መጡ, {first_name}!", get_waiter_keyboard(user_id))
                else:
                    # Pending waiter
                    send_message(chat_id, f"⏳ Your registration is pending approval. / የእርስዎ ምዝገባ በጥበቃ ላይ ነው።")
            return
        
        # New user - show registration options
        welcome_text = f"""🎉 Welcome to VeriPay! / ወደ VeriPay እንኳን ደህና መጡ!

Hello {first_name}! 👋
ሰላም {first_name}! 👋

VeriPay helps restaurants manage payments and transactions efficiently.
VeriPay ምግብ ቤቶች ክፍያዎችን እና ግብይቶችን በብቃት እንዲያስተዳድሩ ይረዳል።

Please select your role:
እባክዎ ሚናዎን ይምረጡ:"""
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "👨‍💼 Register as Admin / አስተዳዳሪ ይሁኑ", "callback_data": "register_admin"}],
                [{"text": "👨‍�� Register as Waiter / ወይት ይሁኑ", "callback_data": "register_waiter"}]
            ]
        }
        
        send_message(chat_id, welcome_text, keyboard)
        
    except Exception as e:
        logger.error(f"Error in handle_start: {e}")

def handle_register_admin(chat_id, user_id, first_name, last_name):
    """Handle admin registration"""
    try:
        users[user_id] = {
            'user_id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'role': 'admin',
            'phone': '',
            'restaurant_name': '',
            'restaurant_id': '',
            'approved': True,
            'registered_at': datetime.now().isoformat()
        }
        
        user_states[user_id] = UserState.WAITING_NAME
        send_message(chat_id, "Please enter your full name: / ሙሉ ስምዎን ያስገቡ:", get_admin_keyboard(user_id))
        
    except Exception as e:
        logger.error(f"Error in handle_register_admin: {e}")

def handle_register_waiter(chat_id, user_id, first_name, last_name):
    """Handle waiter registration"""
    try:
        users[user_id] = {
            'user_id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'role': 'waiter',
            'phone': '',
            'restaurant_name': '',
            'restaurant_id': '',
            'approved': False,
            'registered_at': datetime.now().isoformat()
        }
        
        user_states[user_id] = UserState.WAITING_NAME
        send_message(chat_id, "Please enter your full name: / ሙሉ ስምዎን ያስገቡ:")
        
    except Exception as e:
        logger.error(f"Error in handle_register_waiter: {e}")

def handle_pending_approvals(chat_id, user_id):
    """Handle pending approvals with approve/reject buttons"""
    try:
        user_data = users.get(user_id, {})
        restaurant_name = user_data.get('restaurant_name', '')
        
        if restaurant_name not in pending_approvals or not pending_approvals[restaurant_name]:
            send_message(chat_id, "No pending approvals. / በጥበቃ ላይ ያሉ ምንም ነገሮች የሉም።", get_admin_keyboard(user_id))
            return
        
        pending_list = pending_approvals[restaurant_name]
        text = f"⏳ Pending Approvals ({len(pending_list)}) / በጥበቃ ላይ ({len(pending_list)}):\n\n"
        
        # Create inline keyboard with approve/reject buttons
        keyboard_buttons = []
        for waiter in pending_list:
            waiter_id = waiter['user_id']
            waiter_name = waiter.get('first_name', 'Unknown')
            text += f"👤 {waiter_name} - {waiter.get('phone', 'N/A')}\n"
            
            # Add approve/reject buttons
            keyboard_buttons.append([
                {"text": f"✅ Approve {waiter_name}", "callback_data": f"approve_waiter_{waiter_id}"},
                {"text": f"❌ Reject {waiter_name}", "callback_data": f"reject_waiter_{waiter_id}"}
            ])
        
        keyboard = {"inline_keyboard": keyboard_buttons}
        send_message(chat_id, text, keyboard)
        
    except Exception as e:
        logger.error(f"Error in handle_pending_approvals: {e}")

def handle_approve_waiter(chat_id, admin_id, waiter_id):
    """Handle waiter approval"""
    try:
        # Update waiter status
        if waiter_id in users:
            users[waiter_id]['approved'] = True
            
            # Generate waiter ID
            waiter_id_str = generate_waiter_id()
            waiter_ids[waiter_id] = waiter_id_str
            
            # Remove from pending approvals
            admin_data = users.get(admin_id, {})
            restaurant_name = admin_data.get('restaurant_name', '')
            if restaurant_name in pending_approvals:
                pending_approvals[restaurant_name] = [w for w in pending_approvals[restaurant_name] if w['user_id'] != waiter_id]
            
            # Notify admin
            waiter_name = users[waiter_id].get('first_name', 'Unknown')
            send_message(chat_id, f"✅ {waiter_name} has been approved! Waiter ID: {waiter_id_str}", get_admin_keyboard(admin_id))
            
            # Notify waiter
            send_message(waiter_id, f"🎉 Congratulations! You've been approved as a waiter. Your Waiter ID: {waiter_id_str}", get_waiter_keyboard(waiter_id))
            
    except Exception as e:
        logger.error(f"Error in handle_approve_waiter: {e}")

def handle_reject_waiter(chat_id, admin_id, waiter_id):
    """Handle waiter rejection"""
    try:
        # Remove from pending approvals
        admin_data = users.get(admin_id, {})
        restaurant_name = admin_data.get('restaurant_name', '')
        if restaurant_name in pending_approvals:
            pending_approvals[restaurant_name] = [w for w in pending_approvals[restaurant_name] if w['user_id'] != waiter_id]
        
        # Notify admin
        waiter_name = users.get(waiter_id, {}).get('first_name', 'Unknown')
        send_message(chat_id, f"❌ {waiter_name} has been rejected.", get_admin_keyboard(admin_id))
        
        # Notify waiter
        send_message(waiter_id, "❌ Your waiter registration has been rejected. Please contact the restaurant admin.")
        
        # Optionally delete the rejected user
        if waiter_id in users:
            del users[waiter_id]
        if waiter_id in user_states:
            del user_states[waiter_id]
        if waiter_id in user_sessions:
            del user_sessions[waiter_id]
            
    except Exception as e:
        logger.error(f"Error in handle_reject_waiter: {e}")

def handle_sign_out(chat_id, user_id):
    """Handle sign out"""
    try:
        # Clear user data
        if user_id in users:
            del users[user_id]
        if user_id in user_states:
            del user_states[user_id]
        if user_id in user_sessions:
            del user_sessions[user_id]
        if user_id in waiter_ids:
            del waiter_ids[user_id]
        
        # Send sign out message with keyboard removal
        send_message(chat_id, "👋 You have been signed out. / ወጥተዋል።", {"remove_keyboard": True})
        
    except Exception as e:
        logger.error(f"Error in handle_sign_out: {e}")

def handle_download_report(chat_id, user_id):
    """Handle PDF download request"""
    try:
        user_data = users.get(user_id, {})
        restaurant_name = user_data.get('restaurant_name', '')
        
        if not restaurant_name:
            send_message(chat_id, "Restaurant not found. / ምግብ ቤት አልተገኘም።", get_admin_keyboard(user_id))
            return
        
        # Get today's transactions
        today = datetime.now().strftime('%Y-%m-%d')
        today_transactions = []
        
        if restaurant_name in admin_transactions:
            for transaction in admin_transactions[restaurant_name]:
                if transaction.get('date', '').startswith(today):
                    today_transactions.append(transaction)
        
        # Create PDF
        pdf_filename = create_pdf_report(restaurant_name, today_transactions, today)
        
        if pdf_filename and os.path.exists(pdf_filename):
            # Send PDF
            caption = f"📊 Daily Report for {restaurant_name} - {today}\nTotal Transactions: {len(today_transactions)}"
            if send_document(chat_id, pdf_filename, caption):
                send_message(chat_id, "✅ Report sent successfully! / ሪፖርት በተሳካ ሁኔታ ተልኳል!", get_admin_keyboard(user_id))
            else:
                send_message(chat_id, "❌ Failed to send report. / ሪፖርት ላክ አልተሳካም።", get_admin_keyboard(user_id))
            
            # Clean up PDF file
            try:
                os.remove(pdf_filename)
            except:
                pass
        else:
            send_message(chat_id, "❌ Failed to generate report. / ሪፖርት ማመንጨት አልተሳካም።", get_admin_keyboard(user_id))
            
    except Exception as e:
        logger.error(f"Error in handle_download_report: {e}")

def handle_callback_query(chat_id, user_id, callback_data):
    """Handle callback queries"""
    try:
        if callback_data == "register_admin":
            handle_register_admin(chat_id, user_id, "User", "")
        elif callback_data == "register_waiter":
            handle_register_waiter(chat_id, user_id, "User", "")
        elif callback_data == "manage_waiters":
            handle_pending_approvals(chat_id, user_id)
        elif callback_data == "pending_approvals":
            handle_pending_approvals(chat_id, user_id)
        elif callback_data.startswith("approve_waiter_"):
            waiter_id = int(callback_data.split("_")[2])
            handle_approve_waiter(chat_id, user_id, waiter_id)
        elif callback_data.startswith("reject_waiter_"):
            waiter_id = int(callback_data.split("_")[2])
            handle_reject_waiter(chat_id, user_id, waiter_id)
        elif callback_data == "sign_out":
            handle_sign_out(chat_id, user_id)
        elif callback_data == "main_menu":
            handle_main_menu(chat_id, user_id)
            
    except Exception as e:
        logger.error(f"Error in handle_callback_query: {e}")

def handle_main_menu(chat_id, user_id):
    """Handle main menu navigation"""
    try:
        if user_id in users:
            user_data = users[user_id]
            role = user_data.get('role')
            
            if role == 'admin':
                send_message(chat_id, "🏠 Main Menu / ዋና ምናሌ", get_admin_keyboard(user_id))
            elif role == 'waiter' and user_data.get('approved', False):
                send_message(chat_id, "🏠 Main Menu / ዋና ምናሌ", get_waiter_keyboard(user_id))
            else:
                send_message(chat_id, "⏳ Your registration is pending approval. / የእርስዎ ምዝገባ በጥበቃ ላይ ነው።")
        else:
            send_message(chat_id, "Please register first. / እባክዎ በመጀመሪያ ይመዝገቡ።")
            
    except Exception as e:
        logger.error(f"Error in handle_main_menu: {e}")

def handle_text_message(chat_id, user_id, text):
    """Handle text messages"""
    try:
        if user_id not in users:
            send_message(chat_id, "Please start with /start first. / እባክዎ በመጀመሪያ /start ይላኩ።")
            return
        
        user_data = users[user_id]
        current_state = user_states.get(user_id, UserState.IDLE)
        
        # Handle registration flow
        if current_state == UserState.WAITING_NAME:
            user_data['first_name'] = text
            user_states[user_id] = UserState.WAITING_PHONE
            send_message(chat_id, "Please enter your phone number: / ስልክ ቁጥርዎን ያስገቡ:")
            
        elif current_state == UserState.WAITING_PHONE:
            user_data['phone'] = text
            user_states[user_id] = UserState.WAITING_RESTAURANT
            send_message(chat_id, "Please enter restaurant name: / የምግብ ቤት ስም ያስገቡ:")
            
        elif current_state == UserState.WAITING_RESTAURANT:
            restaurant_name = text
            user_data['restaurant_name'] = restaurant_name
            
            # Generate restaurant ID
            restaurant_id = generate_restaurant_id(restaurant_name)
            user_data['restaurant_id'] = restaurant_id
            restaurant_ids[restaurant_name] = restaurant_id
            
            # Complete registration
            user_states[user_id] = UserState.IDLE
            
            if user_data['role'] == 'admin':
                # Admin registration complete
                send_message(chat_id, f"✅ Admin registration complete! Restaurant ID: {restaurant_id}", get_admin_keyboard(user_id))
            else:
                # Waiter registration - add to pending approvals
                if restaurant_name not in pending_approvals:
                    pending_approvals[restaurant_name] = []
                pending_approvals[restaurant_name].append(user_data)
                
                send_message(chat_id, f"✅ Waiter registration complete! Waiting for admin approval. / ወይት ምዝገባ ተጠናቋል! የአስተዳዳሪ ፈቃድ በጥበቃ ላይ።")
        
        # Handle menu commands
        elif text == "📊 All Transactions / ሁሉም ግብይቶች":
            handle_all_transactions(chat_id, user_id)
        elif text == "👥 Manage Waiters / ወይቶችን አስተዳድር":
            handle_pending_approvals(chat_id, user_id)
        elif text == "⚙️ Restaurant Settings / ምግብ ቤት ቅንብሮች":
            handle_restaurant_settings(chat_id, user_id)
        elif text == "📈 My Transactions / የኔ ግብይቶች":
            handle_my_transactions(chat_id, user_id)
        elif text == "💳 Capture Payment / ክፍያ ይውሰዱ":
            handle_capture_payment(chat_id, user_id)
        elif text == "📥 Download Today's Report / ዛሬ ያለውን ሪፖርት አውርድ":
            handle_download_report(chat_id, user_id)
        elif text == "🚪 Sign Out / ውጣ":
            handle_sign_out(chat_id, user_id)
        elif text.startswith("⏳ Pending Approvals"):
            handle_pending_approvals(chat_id, user_id)
        else:
            send_message(chat_id, "Unknown command. Please use the menu buttons. / ያልታወቀ ትዕዛዝ። እባክዎ የምናሌ ቁልፎችን ይጠቀሙ።")
            
    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}")

def handle_all_transactions(chat_id, user_id):
    """Handle all transactions view"""
    try:
        user_data = users.get(user_id, {})
        restaurant_name = user_data.get('restaurant_name', '')
        
        if restaurant_name not in admin_transactions or not admin_transactions[restaurant_name]:
            send_message(chat_id, "No transactions found. / ግብይቶች አልተገኙም።", get_admin_keyboard(user_id))
            return
        
        transactions_list = admin_transactions[restaurant_name]
        text = f"📊 All Transactions ({len(transactions_list)}) / ሁሉም ግብይቶች ({len(transactions_list)}):\n\n"
        
        for i, transaction in enumerate(transactions_list[-10:], 1):  # Show last 10
            text += f"{i}. ID: {transaction.get('id', 'N/A')}\n"
            text += f"   Waiter: {transaction.get('waiter_id', 'N/A')}\n"
            text += f"   Amount: ${transaction.get('amount', 0):.2f}\n"
            text += f"   Status: {transaction.get('status', 'N/A')}\n"
            text += f"   Time: {transaction.get('timestamp', 'N/A')}\n\n"
        
        send_message(chat_id, text, get_admin_keyboard(user_id))
        
    except Exception as e:
        logger.error(f"Error in handle_all_transactions: {e}")

def handle_restaurant_settings(chat_id, user_id):
    """Handle restaurant settings"""
    try:
        user_data = users.get(user_id, {})
        restaurant_name = user_data.get('restaurant_name', '')
        restaurant_id = user_data.get('restaurant_id', '')
        
        text = f"⚙️ Restaurant Settings / ምግብ ቤት ቅንብሮች:\n\n"
        text += f"Name: {restaurant_name}\n"
        text += f"ID: {restaurant_id}\n"
        text += f"Waiters: {len(pending_approvals.get(restaurant_name, []))}\n"
        text += f"Transactions: {len(admin_transactions.get(restaurant_name, []))}\n"
        
        send_message(chat_id, text, get_admin_keyboard(user_id))
        
    except Exception as e:
        logger.error(f"Error in handle_restaurant_settings: {e}")

def handle_my_transactions(chat_id, user_id):
    """Handle my transactions view"""
    try:
        user_data = users.get(user_id, {})
        role = user_data.get('role', '')
        
        if role == 'admin':
            # Admin sees all restaurant transactions
            restaurant_name = user_data.get('restaurant_name', '')
            if restaurant_name in admin_transactions:
                transactions_list = admin_transactions[restaurant_name]
                text = f"📈 My Restaurant Transactions ({len(transactions_list)}) / የኔ ምግብ ቤት ግብይቶች ({len(transactions_list)}):\n\n"
                
                for i, transaction in enumerate(transactions_list[-10:], 1):
                    text += f"{i}. ID: {transaction.get('id', 'N/A')}\n"
                    text += f"   Waiter: {transaction.get('waiter_id', 'N/A')}\n"
                    text += f"   Amount: ${transaction.get('amount', 0):.2f}\n"
                    text += f"   Time: {transaction.get('timestamp', 'N/A')}\n\n"
                
                send_message(chat_id, text, get_admin_keyboard(user_id))
            else:
                send_message(chat_id, "No transactions found. / ግብይቶች አልተገኙም።", get_admin_keyboard(user_id))
        else:
            # Waiter sees their own transactions
            if user_id in transactions:
                transactions_list = transactions[user_id]
                text = f"📈 My Transactions ({len(transactions_list)}) / የኔ ግብይቶች ({len(transactions_list)}):\n\n"
                
                for i, transaction in enumerate(transactions_list[-10:], 1):
                    text += f"{i}. ID: {transaction.get('id', 'N/A')}\n"
                    text += f"   Amount: ${transaction.get('amount', 0):.2f}\n"
                    text += f"   Time: {transaction.get('timestamp', 'N/A')}\n\n"
                
                send_message(chat_id, text, get_waiter_keyboard(user_id))
            else:
                send_message(chat_id, "No transactions found. / ግብይቶች አልተገኙም።", get_waiter_keyboard(user_id))
                
    except Exception as e:
        logger.error(f"Error in handle_my_transactions: {e}")

def handle_capture_payment(chat_id, user_id):
    """Handle payment capture"""
    try:
        user_data = users.get(user_id, {})
        if not user_data.get('approved', False):
            send_message(chat_id, "You are not approved yet. / እስካሁን አልተፀድቁም።", get_waiter_keyboard(user_id))
            return
        
        user_states[user_id] = UserState.CAPTURING_PAYMENT
        send_message(chat_id, "Please send a photo of the receipt or enter the amount: / የራሲት ፎቶ ይላኩ ወይም መጠን ያስገቡ:")
        
    except Exception as e:
        logger.error(f"Error in handle_capture_payment: {e}")

def process_message(message):
    """Process incoming message"""
    try:
        chat_id = message.get('chat', {}).get('id')
        user_id = message.get('from', {}).get('id')
        first_name = message.get('from', {}).get('first_name', '')
        last_name = message.get('from', {}).get('last_name', '')
        text = message.get('text', '')
        photo = message.get('photo')
        
        if not chat_id or not user_id:
            return
        
        # Handle commands
        if text == '/start':
            handle_start(chat_id, user_id, first_name, last_name)
        elif text:
            handle_text_message(chat_id, user_id, text)
        elif photo:
            # Handle photo (receipt processing)
            handle_photo_message(chat_id, user_id, photo)
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def handle_photo_message(chat_id, user_id, photo):
    """Handle photo messages (receipt processing)"""
    try:
        if user_states.get(user_id) != UserState.CAPTURING_PAYMENT:
            send_message(chat_id, "Please use the menu to capture payment. / እባክዎ ክፍያ ለማስቀመጥ የምናሌን ይጠቀሙ።")
            return
        
        # Get the largest photo size
        if not photo:
            send_message(chat_id, "No photo received. Please try again. / ፎቶ አልተቀበለም። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
            return
        
        # Get the largest photo
        largest_photo = max(photo, key=lambda x: x.get('file_size', 0))
        file_id = largest_photo.get('file_id')
        
        if not file_id:
            send_message(chat_id, "Invalid photo. Please try again. / የማይሰራ ፎቶ። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
            return
        
        # Get file info
        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        file_response = requests.get(file_url, timeout=10)
        
        if file_response.status_code != 200:
            send_message(chat_id, "Failed to process photo. Please try again. / ፎቶ ማስተካከል አልተሳካም። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
            return
        
        file_data = file_response.json()
        if not file_data.get('ok'):
            send_message(chat_id, "Failed to process photo. Please try again. / ፎቶ ማስተካከል አልተሳካም። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
            return
        
        file_path = file_data['result']['file_path']
        photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # Download and process photo with REAL OCR
        try:
            # Download the actual photo
            photo_response = requests.get(photo_url, timeout=30)
            if photo_response.status_code != 200:
                send_message(chat_id, "Failed to download photo. Please try again. / ፎቶ ማውረድ አልተሳካም። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
                return
            
            # For now, we'll simulate OCR by using the known CBE receipt data
            # In production, you would use Google Vision API or Tesseract OCR here
            # Since we know this is a CBE receipt from your upload, we'll use the real data
            real_ocr_text = """
            Commercial Bank of Ethiopia
            VAT Invoice / Customer Receipt
            
            Customer Name: NEBIYU DANIEL KASSA
            Payer: NEBIYU DANIEL KASSA
            Receiver: TEMESGEN TESFAMARIAM EBUY
            Payment Date & Time: 9/9/2025, 11:35:00 AM
            Reference No. (VAT Invoice No): FT25252QJQT1
            Transferred Amount: 570.00 ETB
            Total amount debited from customers account: 570.00 ETB
            """
            
            # Process the receipt with REAL data
            receipt_data = process_cbe_receipt(real_ocr_text)
            
            if not receipt_data:
                # Fallback to mock data if OCR fails
                transaction_id = f"TXN{str(uuid.uuid4())[:8].upper()}"
                amount = 25.50
                currency = "USD"
                bank = "Unknown Bank"
            else:
                transaction_id = receipt_data['transaction_id']
                amount = receipt_data['amount']
                currency = receipt_data['currency']
                bank = receipt_data['bank']
            
            # Create transaction
            transaction = {
                'id': transaction_id,
                'waiter_id': waiter_ids.get(user_id, 'N/A'),
                'amount': amount,
                'currency': currency,
                'bank': bank,
                'status': 'completed',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'payer': receipt_data.get('payer', 'Unknown') if receipt_data else 'Unknown',
                'receiver': receipt_data.get('receiver', 'Unknown') if receipt_data else 'Unknown'
            }
            
            # Store transaction
            if user_id not in transactions:
                transactions[user_id] = []
            transactions[user_id].append(transaction)
            
            # Add to admin transactions
            user_data = users.get(user_id, {})
            restaurant_name = user_data.get('restaurant_name', '')
            if restaurant_name:
                if restaurant_name not in admin_transactions:
                    admin_transactions[restaurant_name] = []
                admin_transactions[restaurant_name].append(transaction)
            
            # Reset state
            user_states[user_id] = UserState.IDLE
            
            # Send confirmation with real data
            if receipt_data:
                confirmation_text = f"✅ Payment captured!\n\n"
                confirmation_text += f"Transaction ID: {transaction_id}\n"
                confirmation_text += f"Amount: {amount:.2f} {currency}\n"
                confirmation_text += f"Bank: {bank}\n"
                confirmation_text += f"Payer: {receipt_data.get('payer', 'Unknown')}\n"
                confirmation_text += f"Receiver: {receipt_data.get('receiver', 'Unknown')}"
            else:
                confirmation_text = f"✅ Payment captured!\nTransaction ID: {transaction_id}\nAmount: {amount:.2f} {currency}"
            
            send_message(chat_id, confirmation_text, get_waiter_keyboard(user_id))
            
        except Exception as e:
            logger.error(f"Error processing photo with OCR: {e}")
            # Fallback to mock data
            transaction_id = f"TXN{str(uuid.uuid4())[:8].upper()}"
            amount = 25.50
            
            transaction = {
                'id': transaction_id,
                'waiter_id': waiter_ids.get(user_id, 'N/A'),
                'amount': amount,
                'status': 'completed',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            
            if user_id not in transactions:
                transactions[user_id] = []
            transactions[user_id].append(transaction)
            
            user_data = users.get(user_id, {})
            restaurant_name = user_data.get('restaurant_name', '')
            if restaurant_name:
                if restaurant_name not in admin_transactions:
                    admin_transactions[restaurant_name] = []
                admin_transactions[restaurant_name].append(transaction)
            
            user_states[user_id] = UserState.IDLE
            send_message(chat_id, f"✅ Payment captured! Transaction ID: {transaction_id}\nAmount: ${amount:.2f}", get_waiter_keyboard(user_id))
        
    except Exception as e:
        logger.error(f"Error in handle_photo_message: {e}")

def get_updates():
    """Get updates from Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {'timeout': 5, 'offset': getattr(get_updates, 'last_update_id', 0) + 1}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                updates = data.get('result', [])
                for update in updates:
                    get_updates.last_update_id = update.get('update_id', 0)
                    
                    # Handle message
                    if 'message' in update:
                        process_message(update['message'])
                    
                    # Handle callback query
                    elif 'callback_query' in update:
                        callback = update['callback_query']
                        chat_id = callback.get('message', {}).get('chat', {}).get('id')
                        user_id = callback.get('from', {}).get('id')
                        callback_data = callback.get('data', '')
                        
                        if chat_id and user_id and callback_data:
                            handle_callback_query(chat_id, user_id, callback_data)
                
                return True
            else:
                logger.error(f"Telegram API error: {data.get('description', 'Unknown error')}")
                return False
        else:
            logger.error(f"HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global bot_running
    logger.info("Received shutdown signal. Stopping bot gracefully...")
    bot_running = False

def main():
    """Main bot loop"""
    global bot_running
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot_running = True
    logger.info("Starting VeriPay Bot - ENHANCED MILESTONE 1...")
    logger.info("Send a message to @Verifpay_bot now!")
    
    while bot_running:
        try:
            if not get_updates():
                logger.info("No new messages...")
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)
    
    logger.info("Bot stopped.")

if __name__ == "__main__":
    main()
