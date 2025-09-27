"""
PDF Generator for VeriPay Daily Reports
M1 & M2 Enhancement - Feature 3
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime, timedelta
import io

class PDFGenerator:
    def __init__(self, storage):
        self.storage = storage
    
    def generate_daily_report(self, restaurant_id: int, date: datetime = None) -> bytes:
        """Generate daily PDF report for restaurant"""
        if date is None:
            date = datetime.now()
        
        # Get restaurant info
        restaurant = self.storage.get_restaurant_by_id(restaurant_id)
        if not restaurant:
            raise ValueError("Restaurant not found")
        
        # Get transactions for the date
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        transactions = self.storage.get_transactions_by_date_range(
            restaurant_id, start_date, end_date
        )
        
        # Get waiters
        waiters = self.storage.list_waiters_by_restaurant(restaurant_id)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center
        )
        
        story.append(Paragraph(f"Daily Report - {restaurant['name']}", title_style))
        story.append(Paragraph(f"Date: {date.strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary
        total_amount = sum(float(tx.get('amount', 0) or 0) for tx in transactions)
        story.append(Paragraph(f"Total Transactions: {len(transactions)}", styles['Normal']))
        story.append(Paragraph(f"Total Amount: {total_amount:.2f} ETB", styles['Normal']))
        story.append(Paragraph(f"Active Waiters: {len(waiters)}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Transactions table
        if transactions:
            data = [['Time', 'Amount', 'Bank', 'Waiter', 'Receipt']]
            for tx in transactions:
                waiter_name = tx.get('waiter_full_name', tx.get('waiter_name', 'Unknown'))
                data.append([
                    tx.get('created_at', '')[:16],  # Truncate timestamp
                    f"{tx.get('amount', '0')} ETB",
                    tx.get('bank', 'Unknown'),
                    waiter_name,
                    tx.get('transaction_id', 'N/A')
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("No transactions for this date.", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
