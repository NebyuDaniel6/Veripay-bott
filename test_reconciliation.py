#!/usr/bin/env python3
"""
Test script for Bank Statement Reconciliation feature
"""

import asyncio
from veripay_bot_enhanced import VeriPayBot

async def test_reconciliation():
    """Test the reconciliation feature"""
    bot = VeriPayBot()
    
    # Test PDF processing patterns
    test_text = """
    CBE Statement
    Date: 2025-01-15
    Transaction Ref: TXN123456
    Amount: 1000.00
    Payer: John Doe
    Receiver: Jane Smith
    """
    
    # Test bank identification
    bank_name = bot.identify_bank(test_text)
    print(f"Identified bank: {bank_name}")
    
    # Test transaction extraction
    transactions = await bot.extract_statement_transactions(test_text, bank_name)
    print(f"Extracted transactions: {transactions}")
    
    # Test weekly period determination
    weekly_period = bot.determine_weekly_period(transactions)
    print(f"Weekly period: {weekly_period}")

if __name__ == "__main__":
    asyncio.run(test_reconciliation()) 