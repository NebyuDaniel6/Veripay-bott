"""
Telebirr Parser Tests - DO NOT MODIFY WITHOUT UPDATING TESTS
This file protects the Telebirr parsing logic from regressions.
"""
import os
import sys
import unittest
from pathlib import Path

# Add bot_v2 to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'bot_v2'))

from ocr_parsers.telebirr import parse

class TestTelebirrParser(unittest.TestCase):
    """Test cases for Telebirr transaction parsing"""
    
    def setUp(self):
        """Load test fixtures"""
        self.fixtures_dir = Path(__file__).parent / 'fixtures' / 'telebirr'
    
    def load_fixture(self, filename):
        """Load a test fixture file"""
        with open(self.fixtures_dir / filename, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def test_sample1_real_world_format(self):
        """Test real-world Telebirr screenshot format"""
        text = self.load_fixture('sample1.txt')
        result = parse(text)
        
        self.assertEqual(result['bank'], 'Telebirr')
        self.assertEqual(result['amount'], '7008.00')
        self.assertEqual(result['transaction_id'], 'CHC85KOLMU')
        self.assertEqual(result['sender'], 'Mekonen')
        self.assertEqual(result['time'], '2025/08/12 13:23:22')
    
    def test_sample2_clean_format(self):
        """Test clean, structured format"""
        text = self.load_fixture('sample2.txt')
        result = parse(text)
        
        self.assertEqual(result['bank'], 'Telebirr')
        self.assertEqual(result['amount'], '7008.00')
        self.assertEqual(result['transaction_id'], 'CHC85KOLMU')
        self.assertEqual(result['sender'], 'Mekonen')
        self.assertEqual(result['time'], '2025/08/12 13:23:22')
    
    def test_sample3_positive_amount(self):
        """Test positive amount format"""
        text = self.load_fixture('sample3.txt')
        result = parse(text)
        
        self.assertEqual(result['bank'], 'Telebirr')
        self.assertEqual(result['amount'], '1500.00')
        self.assertEqual(result['transaction_id'], 'CH12345678')
        self.assertEqual(result['sender'], 'John Doe')
        self.assertEqual(result['time'], '2025/08/12 14:30:15')
    
    def test_amount_patterns(self):
        """Test various amount formats"""
        test_cases = [
            ("-7,008.00 (ETB)", "7008.00"),
            ("-7,008.00 ETB", "7008.00"),
            ("7,008.00 (ETB)", "7008.00"),
            ("7,008.00 ETB", "7008.00"),
            ("1,500.00 ETB", "1500.00"),
            ("Amount: 2,000.00 ETB", "2000.00"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = parse(f"Telebirr {input_text}")
                self.assertEqual(result['amount'], expected)
    
    def test_transaction_number_patterns(self):
        """Test various transaction number formats"""
        test_cases = [
            ("Transaction Number: CHC85KOLMU", "CHC85KOLMU"),
            ("Transaction Number: CH12345678", "CH12345678"),
            ("Transaction ID: CHC85KOLMU", "CHC85KOLMU"),
            ("Ref No: CHC85KOLMU", "CHC85KOLMU"),
            ("CHC85KOLMU", "CHC85KOLMU"),  # Bare code
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = parse(f"Telebirr {input_text}")
                self.assertEqual(result['transaction_id'], expected)
    
    def test_recipient_patterns(self):
        """Test various recipient/to patterns"""
        test_cases = [
            ("Transaction To: Mekonen", "Mekonen"),
            ("To: John Doe", "John Doe"),
            ("Recipient: Alice Smith", "Alice Smith"),
            ("Transaction To: Bob Johnson", "Bob Johnson"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = parse(f"Telebirr {input_text}")
                self.assertEqual(result['sender'], expected)
    
    def test_time_patterns(self):
        """Test various time formats"""
        test_cases = [
            ("Transaction Time: 2025/08/12 13:23:22", "2025/08/12 13:23:22"),
            ("2025/08/12 13:23:22", "2025/08/12 13:23:22"),
            ("Time: 2025-08-12 13:23:22", "2025-08-12 13:23:22"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = parse(f"Telebirr {input_text}")
                self.assertEqual(result['time'], expected)
    
    def test_noise_filtering(self):
        """Test that noise words are filtered from recipient field"""
        text = "Telebirr Transaction To: Transaction Number Download Share"
        result = parse(text)
        
        # Should not capture noise words as recipient
        self.assertNotEqual(result['sender'], 'Transaction')
        self.assertNotEqual(result['sender'], 'Number')
        self.assertNotEqual(result['sender'], 'Download')
        self.assertNotEqual(result['sender'], 'Share')
    
    def test_o_zero_ambiguity(self):
        """Test handling of O/0 ambiguity in transaction numbers"""
        test_cases = [
            ("CHC85KOLMU", "CHC85KOLMU"),  # Should keep as-is
            ("CHC850LMU", "CHC850LMU"),    # Should keep as-is
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = parse(f"Telebirr Transaction Number: {input_text}")
                self.assertEqual(result['transaction_id'], expected)
    
    def test_missing_fields(self):
        """Test behavior when fields are missing"""
        text = "Telebirr payment"
        result = parse(text)
        
        self.assertEqual(result['bank'], 'Telebirr')
        self.assertEqual(result['amount'], 'Unknown')
        self.assertEqual(result['transaction_id'], 'Unknown')
        self.assertEqual(result['sender'], 'Unknown')
        self.assertEqual(result['time'], 'Unknown')

if __name__ == '__main__':
    unittest.main()
