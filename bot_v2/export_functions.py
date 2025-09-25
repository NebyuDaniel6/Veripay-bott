import csv
import io
from datetime import datetime
import logging

async def export_transactions_csv(update, context, storage):
    """Export transactions to CSV format"""
    user_id = update.effective_user.id
    user_role = storage.get_user_role(user_id)
    
    if user_role not in ["admin", "super_admin"]:
        await update.message.reply_text("❌ Access denied. Only admins can export data.")
        return
    
    try:
        # Get transactions based on user role
        if user_role == "super_admin":
            transactions = storage.get_all_transactions()
        else:
            restaurant_name = storage.get_user_restaurant(user_id)
            transactions = storage.get_restaurant_transactions(restaurant_name)
        
        if not transactions:
            await update.message.reply_text("📊 No transactions found to export.")
            return
        
        # Create CSV content
        csv_buffer = io.StringIO()
        fieldnames = ["ID", "Transaction ID", "Waiter ID", "Amount", "Currency", "Bank", "Payment Method", "Date", "Time", "Payer", "Receiver", "Reference", "Status", "Restaurant", "Created At"]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        for tx in transactions:
            writer.writerow({
                "ID": tx.get("id", ""),
                "Transaction ID": tx.get("transaction_id", ""),
                "Waiter ID": tx.get("waiter_id", ""),
                "Amount": tx.get("amount", ""),
                "Currency": tx.get("currency", "ETB"),
                "Bank": tx.get("bank", ""),
                "Payment Method": tx.get("payment_method", ""),
                "Date": tx.get("date", ""),
                "Time": tx.get("time", ""),
                "Payer": tx.get("payer", ""),
                "Receiver": tx.get("receiver", ""),
                "Reference": tx.get("original_ref", ""),
                "Status": tx.get("status", ""),
                "Restaurant": tx.get("restaurant_name", ""),
                "Created At": tx.get("created_at", "")
            })
        
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()
        
        # Send CSV file
        csv_bytes = io.BytesIO(csv_content.encode("utf-8"))
        csv_bytes.name = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        await update.message.reply_document(
            document=csv_bytes,
            filename=csv_bytes.name,
            caption=f"📊 **Transaction Export**\n\n📈 **Total Transactions:** {len(transactions)}\n📅 **Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n💡 *This CSV file contains all transaction data and can be opened in Excel or Google Sheets.*"
        )
        
    except Exception as e:
        logging.error(f"Export error: {e}")
        await update.message.reply_text(f"❌ Export failed: {str(e)}")

async def export_analytics_report(update, context, storage):
    """Export comprehensive analytics report"""
    user_id = update.effective_user.id
    user_role = storage.get_user_role(user_id)
    
    if user_role not in ["admin", "super_admin"]:
        await update.message.reply_text("❌ Access denied. Only admins can export analytics.")
        return
    
    try:
        # Get data based on user role
        if user_role == "super_admin":
            transactions = storage.get_all_transactions()
            users = storage.get_all_users()
        else:
            restaurant_name = storage.get_user_restaurant(user_id)
            transactions = storage.get_restaurant_transactions(restaurant_name)
            users = storage.get_restaurant_users(restaurant_name)
        
        if not transactions:
            await update.message.reply_text("📊 No data found to generate analytics report.")
            return
        
        # Calculate analytics
        total_amount = sum(float(tx.get("amount", 0)) for tx in transactions)
        total_transactions = len(transactions)
        avg_transaction = total_amount / total_transactions if total_transactions > 0 else 0
        
        # Bank distribution
        bank_counts = {}
        for tx in transactions:
            bank = tx.get("bank", "Unknown")
            bank_counts[bank] = bank_counts.get(bank, 0) + 1
        
        # Waiter performance
        waiter_stats = {}
        for tx in transactions:
            waiter_id = tx.get("waiter_id", "Unknown")
            if waiter_id not in waiter_stats:
                waiter_stats[waiter_id] = {"count": 0, "total": 0}
            waiter_stats[waiter_id]["count"] += 1
            waiter_stats[waiter_id]["total"] += float(tx.get("amount", 0))
        
        # Create analytics CSV
        csv_buffer = io.StringIO()
        fieldnames = ["Metric", "Value", "Details"]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        # Add summary metrics
        writer.writerow({"Metric": "Total Transactions", "Value": total_transactions, "Details": "All time"})
        writer.writerow({"Metric": "Total Amount", "Value": f"{total_amount:.2f} ETB", "Details": "All time"})
        writer.writerow({"Metric": "Average Transaction", "Value": f"{avg_transaction:.2f} ETB", "Details": "Per transaction"})
        writer.writerow({"Metric": "", "Value": "", "Details": ""})
        
        # Add bank distribution
        writer.writerow({"Metric": "Bank Distribution", "Value": "", "Details": ""})
        for bank, count in bank_counts.items():
            percentage = (count / total_transactions) * 100 if total_transactions > 0 else 0
            writer.writerow({"Metric": bank, "Value": count, "Details": f"{percentage:.1f}%"})
        
        writer.writerow({"Metric": "", "Value": "", "Details": ""})
        
        # Add waiter performance
        writer.writerow({"Metric": "Waiter Performance", "Value": "", "Details": ""})
        for waiter_id, stats in waiter_stats.items():
            avg_waiter = stats["total"] / stats["count"] if stats["count"] > 0 else 0
            writer.writerow({"Metric": waiter_id, "Value": stats["count"], "Details": f"{stats['total']:.2f} ETB (avg: {avg_waiter:.2f})"})
        
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()
        
        # Send analytics report
        csv_bytes = io.BytesIO(csv_content.encode("utf-8"))
        csv_bytes.name = f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        await update.message.reply_document(
            document=csv_bytes,
            filename=csv_bytes.name,
            caption=f"📊 **Analytics Report**\n\n📈 **Total Transactions:** {total_transactions}\n💰 **Total Amount:** {total_amount:.2f} ETB\n📊 **Average Transaction:** {avg_transaction:.2f} ETB\n🏦 **Banks Used:** {len(bank_counts)}\n👥 **Active Waiters:** {len(waiter_stats)}\n\n💡 *This report contains comprehensive analytics and can be opened in Excel or Google Sheets.*"
        )
        
    except Exception as e:
        logging.error(f"Analytics export error: {e}")
        await update.message.reply_text(f"❌ Analytics export failed: {str(e)}")
