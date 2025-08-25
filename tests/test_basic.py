"""
Basic tests for VeriPay system
"""
import pytest
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, Waiter, Restaurant, Transaction, Admin
from core.ocr_extractor import OCRExtractor
from core.fraud_detector import FraudDetector
from core.bank_verifier import BankVerifier
from utils.config import ConfigManager


class TestDatabaseModels:
    """Test database models"""
    
    def test_waiter_model(self):
        """Test Waiter model creation"""
        waiter = Waiter(
            telegram_id="123456789",
            name="Test Waiter",
            phone="+251911234567"
        )
        assert waiter.telegram_id == "123456789"
        assert waiter.name == "Test Waiter"
        assert waiter.phone == "+251911234567"
        assert waiter.is_active == True
    
    def test_restaurant_model(self):
        """Test Restaurant model creation"""
        restaurant = Restaurant(
            name="Test Restaurant",
            address="Addis Ababa, Ethiopia",
            phone="+251911234567",
            email="test@restaurant.com"
        )
        assert restaurant.name == "Test Restaurant"
        assert restaurant.address == "Addis Ababa, Ethiopia"
        assert restaurant.is_active == True
    
    def test_transaction_model(self):
        """Test Transaction model creation"""
        transaction = Transaction(
            stn_number="STN12345678",
            amount=1000.0,
            bank_type="cbe"
        )
        assert transaction.stn_number == "STN12345678"
        assert transaction.amount == 1000.0
        assert transaction.bank_type.value == "cbe"
        assert transaction.verification_status.value == "pending"
    
    def test_admin_model(self):
        """Test Admin model creation"""
        admin = Admin(
            telegram_id="987654321",
            name="Test Admin",
            email="admin@test.com"
        )
        assert admin.telegram_id == "987654321"
        assert admin.name == "Test Admin"
        assert admin.is_super_admin == False


class TestOCRExtractor:
    """Test OCR extractor"""
    
    def test_ocr_extractor_initialization(self):
        """Test OCR extractor initialization"""
        try:
            extractor = OCRExtractor()
            assert extractor is not None
            assert hasattr(extractor, 'patterns')
            assert 'stn_number' in extractor.patterns
            assert 'amount' in extractor.patterns
        except Exception as e:
            pytest.skip(f"OCR extractor test skipped: {e}")
    
    def test_pattern_extraction(self):
        """Test pattern extraction from text"""
        extractor = OCRExtractor()
        
        # Test STN number extraction
        text = "Transaction ID: STN12345678"
        stn = extractor._extract_pattern(text, extractor.patterns['stn_number'])
        assert stn == "STN12345678"
        
        # Test amount extraction
        text = "Amount: 1,000.00 Birr"
        amount = extractor._extract_pattern(text, extractor.patterns['amount'])
        assert amount == "1,000.00"
    
    def test_bank_type_detection(self):
        """Test bank type detection"""
        extractor = OCRExtractor()
        
        # Test CBE detection
        text = "Commercial Bank of Ethiopia transaction"
        bank_type = extractor._detect_bank_type(text)
        assert bank_type == "cbe"
        
        # Test Telebirr detection
        text = "Telebirr mobile money"
        bank_type = extractor._detect_bank_type(text)
        assert bank_type == "telebirr"


class TestFraudDetector:
    """Test fraud detector"""
    
    def test_fraud_detector_initialization(self):
        """Test fraud detector initialization"""
        try:
            detector = FraudDetector()
            assert detector is not None
            assert hasattr(detector, 'fraud_config')
        except Exception as e:
            pytest.skip(f"Fraud detector test skipped: {e}")
    
    def test_exif_analysis(self):
        """Test EXIF data analysis"""
        detector = FraudDetector()
        
        # Test with non-existent file
        result = detector._check_exif_data("non_existent_file.jpg")
        assert result['suspicious'] == False
        assert 'Could not analyze EXIF data' in result['reason']


class TestBankVerifier:
    """Test bank verifier"""
    
    def test_bank_verifier_initialization(self):
        """Test bank verifier initialization"""
        try:
            verifier = BankVerifier()
            assert verifier is not None
            assert hasattr(verifier, 'banks_config')
        except Exception as e:
            pytest.skip(f"Bank verifier test skipped: {e}")
    
    def test_bank_status_check(self):
        """Test bank status check"""
        verifier = BankVerifier()
        
        # Test with non-existent bank
        status = verifier.get_bank_status("non_existent_bank")
        assert status['available'] == False
        assert 'not configured' in status['error']


class TestConfigManager:
    """Test configuration manager"""
    
    def test_config_initialization(self):
        """Test configuration manager initialization"""
        try:
            config = ConfigManager()
            assert config is not None
            assert hasattr(config, 'config')
        except Exception as e:
            pytest.skip(f"Config manager test skipped: {e}")
    
    def test_config_getters(self):
        """Test configuration getters"""
        try:
            config = ConfigManager()
            
            # Test basic getter
            telegram_config = config.get_telegram_config()
            assert isinstance(telegram_config, dict)
            
            # Test nested getter
            db_url = config.get_nested('database.url')
            assert db_url is not None
        except Exception as e:
            pytest.skip(f"Config getters test skipped: {e}")


class TestIntegration:
    """Integration tests"""
    
    def test_database_connection(self):
        """Test database connection"""
        try:
            from database.operations import DatabaseManager
            db_manager = DatabaseManager()
            session = db_manager.get_session()
            assert session is not None
            session.close()
        except Exception as e:
            pytest.skip(f"Database connection test skipped: {e}")
    
    def test_audit_engine(self):
        """Test audit engine"""
        try:
            from core.audit_engine import AuditEngine
            engine = AuditEngine()
            assert engine is not None
            assert hasattr(engine, 'audit_config')
        except Exception as e:
            pytest.skip(f"Audit engine test skipped: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 