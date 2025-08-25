"""
Configuration utilities for VeriPay
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class ConfigManager:
    """Configuration manager for VeriPay"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration manager"""
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file {self.config_path} not found, creating default config")
                self._create_default_config()
            
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            # Override with environment variables
            config = self._override_with_env(config)
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            'telegram': {
                'waiter_bot_token': os.getenv('WAITER_BOT_TOKEN', 'YOUR_WAITER_BOT_TOKEN'),
                'admin_bot_token': os.getenv('ADMIN_BOT_TOKEN', 'YOUR_ADMIN_BOT_TOKEN'),
                'webhook_url': os.getenv('WEBHOOK_URL', 'https://your-domain.com/webhook'),
                'admin_user_ids': []
            },
            'database': {
                'url': os.getenv('DATABASE_URL', 'postgresql://username:password@localhost:5432/veripay'),
                'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
                'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')),
                'echo': os.getenv('DB_ECHO', 'false').lower() == 'true'
            },
            'ai': {
                'ocr_engine': os.getenv('OCR_ENGINE', 'tesseract'),
                'tesseract_path': os.getenv('TESSERACT_PATH', '/usr/local/bin/tesseract'),
                'confidence_threshold': float(os.getenv('OCR_CONFIDENCE_THRESHOLD', '0.7')),
                'fraud_detection': {
                    'enabled': os.getenv('FRAUD_DETECTION_ENABLED', 'true').lower() == 'true',
                    'model_path': os.getenv('FRAUD_MODEL_PATH', 'models/fraud_detector.h5'),
                    'confidence_threshold': float(os.getenv('FRAUD_CONFIDENCE_THRESHOLD', '0.8')),
                    'check_exif': os.getenv('CHECK_EXIF', 'true').lower() == 'true',
                    'check_noise': os.getenv('CHECK_NOISE', 'true').lower() == 'true',
                    'check_fonts': os.getenv('CHECK_FONTS', 'true').lower() == 'true'
                }
            },
            'banks': {
                'cbe': {
                    'name': 'Commercial Bank of Ethiopia',
                    'api_url': os.getenv('CBE_API_URL', 'https://api.cbe.com.et'),
                    'api_key': os.getenv('CBE_API_KEY', 'YOUR_CBE_API_KEY'),
                    'verification_url': os.getenv('CBE_VERIFICATION_URL', 'https://cbe.com.et/verify'),
                    'enabled': os.getenv('CBE_ENABLED', 'true').lower() == 'true'
                },
                'telebirr': {
                    'name': 'Telebirr',
                    'api_url': os.getenv('TELEBIRR_API_URL', 'https://api.telebirr.et'),
                    'api_key': os.getenv('TELEBIRR_API_KEY', 'YOUR_TELEBIRR_API_KEY'),
                    'verification_url': os.getenv('TELEBIRR_VERIFICATION_URL', 'https://telebirr.et/verify'),
                    'enabled': os.getenv('TELEBIRR_ENABLED', 'true').lower() == 'true'
                },
                'dashen': {
                    'name': 'Dashen Bank',
                    'api_url': os.getenv('DASHEN_API_URL', 'https://api.dashenbank.com'),
                    'api_key': os.getenv('DASHEN_API_KEY', 'YOUR_DASHEN_API_KEY'),
                    'verification_url': os.getenv('DASHEN_VERIFICATION_URL', 'https://dashenbank.com/verify'),
                    'enabled': os.getenv('DASHEN_ENABLED', 'true').lower() == 'true'
                }
            },
            'audit': {
                'reconciliation_interval_days': int(os.getenv('RECONCILIATION_INTERVAL_DAYS', '3')),
                'report_format': os.getenv('REPORT_FORMAT', 'pdf'),
                'auto_generate_reports': os.getenv('AUTO_GENERATE_REPORTS', 'true').lower() == 'true',
                'report_retention_days': int(os.getenv('REPORT_RETENTION_DAYS', '90'))
            },
            'storage': {
                'upload_path': os.getenv('UPLOAD_PATH', './uploads'),
                'max_file_size_mb': int(os.getenv('MAX_FILE_SIZE_MB', '10')),
                'allowed_extensions': os.getenv('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,pdf').split(','),
                'backup_enabled': os.getenv('BACKUP_ENABLED', 'true').lower() == 'true',
                'backup_path': os.getenv('BACKUP_PATH', './backups')
            },
            'logging': {
                'level': os.getenv('LOG_LEVEL', 'INFO'),
                'file': os.getenv('LOG_FILE', 'logs/veripay.log'),
                'max_size_mb': int(os.getenv('LOG_MAX_SIZE_MB', '100')),
                'backup_count': int(os.getenv('LOG_BACKUP_COUNT', '5')),
                'format': os.getenv('LOG_FORMAT', '{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}')
            },
            'security': {
                'encryption_key': os.getenv('ENCRYPTION_KEY', 'YOUR_ENCRYPTION_KEY'),
                'session_timeout_minutes': int(os.getenv('SESSION_TIMEOUT_MINUTES', '30')),
                'max_login_attempts': int(os.getenv('MAX_LOGIN_ATTEMPTS', '5')),
                'password_min_length': int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
            },
            'performance': {
                'max_concurrent_verifications': int(os.getenv('MAX_CONCURRENT_VERIFICATIONS', '10')),
                'verification_timeout_seconds': int(os.getenv('VERIFICATION_TIMEOUT_SECONDS', '30')),
                'cache_enabled': os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
                'cache_ttl_seconds': int(os.getenv('CACHE_TTL_SECONDS', '3600'))
            },
            'monitoring': {
                'health_check_enabled': os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true',
                'metrics_enabled': os.getenv('METRICS_ENABLED', 'true').lower() == 'true',
                'alert_email': os.getenv('ALERT_EMAIL', 'admin@veripay.et'),
                'alert_telegram_chat_id': os.getenv('ALERT_TELEGRAM_CHAT_ID', 'YOUR_ALERT_CHAT_ID')
            },
            'development': {
                'debug': os.getenv('DEBUG', 'false').lower() == 'true',
                'test_mode': os.getenv('TEST_MODE', 'false').lower() == 'true',
                'mock_bank_apis': os.getenv('MOCK_BANK_APIS', 'false').lower() == 'true',
                'sample_data_enabled': os.getenv('SAMPLE_DATA_ENABLED', 'false').lower() == 'true'
            }
        }
        
        # Create config directory if it doesn't exist
        config_dir = Path(self.config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Write default config
        with open(self.config_path, 'w') as file:
            yaml.dump(default_config, file, default_flow_style=False, indent=2)
        
        logger.info(f"Created default config file: {self.config_path}")
    
    def _override_with_env(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Override configuration with environment variables"""
        # Telegram settings
        if os.getenv('WAITER_BOT_TOKEN'):
            config['telegram']['waiter_bot_token'] = os.getenv('WAITER_BOT_TOKEN')
        if os.getenv('ADMIN_BOT_TOKEN'):
            config['telegram']['admin_bot_token'] = os.getenv('ADMIN_BOT_TOKEN')
        
        # Database settings
        if os.getenv('DATABASE_URL'):
            config['database']['url'] = os.getenv('DATABASE_URL')
        
        # AI settings
        if os.getenv('OCR_ENGINE'):
            config['ai']['ocr_engine'] = os.getenv('OCR_ENGINE')
        if os.getenv('TESSERACT_PATH'):
            config['ai']['tesseract_path'] = os.getenv('TESSERACT_PATH')
        
        # Bank API settings
        if os.getenv('CBE_API_KEY'):
            config['banks']['cbe']['api_key'] = os.getenv('CBE_API_KEY')
        if os.getenv('TELEBIRR_API_KEY'):
            config['banks']['telebirr']['api_key'] = os.getenv('TELEBIRR_API_KEY')
        if os.getenv('DASHEN_API_KEY'):
            config['banks']['dashen']['api_key'] = os.getenv('DASHEN_API_KEY')
        
        return config
    
    def _validate_config(self):
        """Validate configuration settings"""
        required_fields = [
            'telegram.waiter_bot_token',
            'telegram.admin_bot_token',
            'database.url'
        ]
        
        for field in required_fields:
            value = self.get_nested(field)
            if not value or value.startswith('YOUR_'):
                logger.warning(f"Configuration field '{field}' needs to be set")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def get_nested(self, key_path: str, default: Any = None) -> Any:
        """Get nested configuration value using dot notation"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def set_nested(self, key_path: str, value: Any):
        """Set nested configuration value using dot notation"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as file:
                yaml.dump(self.config, file, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        self._validate_config()
        logger.info("Configuration reloaded")
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Get Telegram configuration"""
        return self.config.get('telegram', {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.config.get('database', {})
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration"""
        return self.config.get('ai', {})
    
    def get_banks_config(self) -> Dict[str, Any]:
        """Get banks configuration"""
        return self.config.get('banks', {})
    
    def get_audit_config(self) -> Dict[str, Any]:
        """Get audit configuration"""
        return self.config.get('audit', {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration"""
        return self.config.get('storage', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return self.config.get('security', {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return self.config.get('performance', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self.config.get('monitoring', {})
    
    def get_development_config(self) -> Dict[str, Any]:
        """Get development configuration"""
        return self.config.get('development', {})
    
    def is_development_mode(self) -> bool:
        """Check if development mode is enabled"""
        return self.get_development_config().get('debug', False)
    
    def is_test_mode(self) -> bool:
        """Check if test mode is enabled"""
        return self.get_development_config().get('test_mode', False)
    
    def get_allowed_file_extensions(self) -> list:
        """Get allowed file extensions"""
        return self.get_storage_config().get('allowed_extensions', ['jpg', 'jpeg', 'png', 'pdf'])
    
    def get_max_file_size_mb(self) -> int:
        """Get maximum file size in MB"""
        return self.get_storage_config().get('max_file_size_mb', 10)
    
    def get_upload_path(self) -> str:
        """Get upload path"""
        return self.get_storage_config().get('upload_path', './uploads')
    
    def get_backup_path(self) -> str:
        """Get backup path"""
        return self.get_storage_config().get('backup_path', './backups')


# Global configuration instance
config = ConfigManager()


def get_config() -> ConfigManager:
    """Get global configuration instance"""
    return config


def reload_config():
    """Reload global configuration"""
    config.reload() 