#!/usr/bin/env python3
"""
Fix PDF download to show all extracted transaction data
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find and replace the handle_download_today function
old_function = '''def handle_download_today(chat_id, user_id):
    """Handle PDF download of today's transactions"""
    try:
        user_data = users.get(user_id, {})
        if user_data.get('role') != 'admin':
            send_message(chat_id, "Access denied. Admin only. / መዳረሻ ተከልክሏል። አስተዳዳሪ ብቻ።")
            return

        restaurant_name = user_data.get('restaurant_name', 'Unknown Restaurant')
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get today's transactions for this restaurant
        today_transactions = []
        if restaurant_name in admin_transactions:
            for transaction in admin_transactions[restaurant_name]:
                if transaction.get('date') == today:
                    today_transactions.append(transaction)
        
        if not today_transactions:
            send_message(chat_id, f"No transactions found for today ({today}). / ዛሬ ምንም ግብይት አልተገኘም ({today})።")
            return

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Title
        title = f"Daily Transaction Report - {restaurant_name}"
        elements.append(Paragraph(title, getSampleStyleSheet()['Title']))
        elements.append(Spacer(1, 12))
        
        # Date
        date_text = f"Date: {today}"
        elements.append(Paragraph(date_text, getSampleStyleSheet()['Normal']))
        elements.append(Spacer(1, 12))
        
        # Transaction table
        table_data = [['Transaction ID', 'Waiter ID', 'Amount', 'Status', 'Time']]
        total_amount = 0
        
        for transaction in today_transactions:
            table_data.append([
                transaction.get('id', 'N/A'),
                transaction.get('waiter_id', 'N/A'),
                f"{transaction.get('amount', 0):.2f} {transaction.get('currency', 'ETB')}",
                transaction.get('status', 'N/A'),
                transaction.get('timestamp', 'N/A')
            ])
            total_amount += transaction.get('amount', 0)
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        # Total
        total_text = f"Total Amount: {total_amount:.2f} ETB"
        elements.append(Paragraph(total_text, getSampleStyleSheet()['Heading2']))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Send PDF
        send_document(chat_id, buffer.getvalue(), f"daily_report_{today}.pdf")
        
    except Exception as e:
        logger.error(f"Error in handle_download_today: {e}")
        send_message(chat_id, "Error generating PDF. Please try again. / ፒዲኤፍ ማመንጨት ላይ ስህተት። እባክዎ እንደገና ይሞክሩ።")'''

new_function = '''def handle_download_today(chat_id, user_id):
    """Handle PDF download of today's transactions with full extracted data"""
    try:
        user_data = users.get(user_id, {})
        if user_data.get('role') != 'admin':
            send_message(chat_id, "Access denied. Admin only. / መዳረሻ ተከልክሏል። አስተዳዳሪ ብቻ።")
            return

        restaurant_name = user_data.get('restaurant_name', 'Unknown Restaurant')
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get today's transactions for this restaurant
        today_transactions = []
        if restaurant_name in admin_transactions:
            for transaction in admin_transactions[restaurant_name]:
                if transaction.get('date') == today:
                    today_transactions.append(transaction)
        
        if not today_transactions:
            send_message(chat_id, f"No transactions found for today ({today}). / ዛሬ ምንም ግብይት አልተገኘም ({today})።")
            return

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Title
        title = f"Daily Transaction Report - {restaurant_name}"
        elements.append(Paragraph(title, getSampleStyleSheet()['Title']))
        elements.append(Spacer(1, 12))
        
        # Date
        date_text = f"Date: {today}"
        elements.append(Paragraph(date_text, getSampleStyleSheet()['Normal']))
        elements.append(Spacer(1, 12))
        
        # Enhanced transaction table with all extracted data
        table_data = [['Transaction ID', 'Waiter ID', 'Amount', 'Bank', 'Payment Method', 'Date', 'Time', 'Payer', 'Receiver', 'Status']]
        total_amount = 0
        
        for transaction in today_transactions:
            table_data.append([
                transaction.get('id', 'N/A'),
                transaction.get('waiter_id', 'N/A'),
                f"{transaction.get('amount', 0):.2f} {transaction.get('currency', 'ETB')}",
                transaction.get('bank', 'N/A'),
                transaction.get('payment_method', 'N/A'),
                transaction.get('date', 'N/A'),
                transaction.get('time', 'N/A'),
                transaction.get('payer', 'N/A'),
                transaction.get('receiver', 'N/A'),
                transaction.get('status', 'N/A')
            ])
            total_amount += transaction.get('amount', 0)
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        # Summary section
        summary_text = f"Total Transactions: {len(today_transactions)}"
        elements.append(Paragraph(summary_text, getSampleStyleSheet()['Heading2']))
        
        total_text = f"Total Amount: {total_amount:.2f} ETB"
        elements.append(Paragraph(total_text, getSampleStyleSheet()['Heading2']))
        
        # Bank breakdown
        bank_counts = {}
        for transaction in today_transactions:
            bank = transaction.get('bank', 'Unknown')
            bank_counts[bank] = bank_counts.get(bank, 0) + 1
        
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Bank Breakdown:", getSampleStyleSheet()['Heading3']))
        for bank, count in bank_counts.items():
            bank_text = f"{bank}: {count} transactions"
            elements.append(Paragraph(bank_text, getSampleStyleSheet()['Normal']))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Send PDF
        send_document(chat_id, buffer.getvalue(), f"daily_report_{today}.pdf")
        
    except Exception as e:
        logger.error(f"Error in handle_download_today: {e}")
        send_message(chat_id, "Error generating PDF. Please try again. / ፒዲኤፍ ማመንጨት ላይ ስህተት። እባክዎ እንደገና ይሞክሩ።")'''

# Replace the function
content = content.replace(old_function, new_function)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("PDF download enhanced with all extracted transaction data!")
