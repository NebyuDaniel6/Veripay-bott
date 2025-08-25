"""
Bank Verifier for VeriPay - Verifies transactions with bank APIs
"""
import requests
import json
import re
from typing import Dict, Optional, List
import yaml
from loguru import logger
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import hashlib


class BankVerifier:
    """Bank API verification for transactions"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize bank verifier"""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        self.banks_config = self.config['banks']
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'VeriPay/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def verify_transaction(self, stn_number: str, amount: float, 
                          bank_type: str, transaction_date: datetime = None) -> Dict:
        """
        Verify transaction with bank API
        
        Args:
            stn_number: Transaction reference number
            amount: Transaction amount
            bank_type: Type of bank (cbe, telebirr, dashen)
            transaction_date: Transaction date
            
        Returns:
            Dict containing verification results
        """
        try:
            if bank_type not in self.banks_config:
                return {
                    'verified': False,
                    'error': f"Unsupported bank type: {bank_type}",
                    'bank_response': None
                }
            
            bank_config = self.banks_config[bank_type]
            if not bank_config.get('enabled', False):
                return {
                    'verified': False,
                    'error': f"Bank {bank_type} is not enabled",
                    'bank_response': None
                }
            
            # Try different verification methods
            verification_methods = [
                self._verify_via_api,
                self._verify_via_web_scraping,
                self._verify_via_embedded_link
            ]
            
            for method in verification_methods:
                try:
                    result = method(stn_number, amount, bank_type, transaction_date)
                    if result['verified'] or result.get('error') != 'Method not available':
                        return result
                except Exception as e:
                    logger.warning(f"Verification method {method.__name__} failed: {e}")
                    continue
            
            return {
                'verified': False,
                'error': 'All verification methods failed',
                'bank_response': None
            }
            
        except Exception as e:
            logger.error(f"Error in transaction verification: {e}")
            return {
                'verified': False,
                'error': str(e),
                'bank_response': None
            }
    
    def _verify_via_api(self, stn_number: str, amount: float, 
                       bank_type: str, transaction_date: datetime = None) -> Dict:
        """Verify transaction via bank API"""
        try:
            bank_config = self.banks_config[bank_type]
            api_url = bank_config.get('api_url')
            api_key = bank_config.get('api_key')
            
            if not api_url or not api_key:
                return {
                    'verified': False,
                    'error': 'Method not available',
                    'bank_response': None
                }
            
            # Prepare request payload
            payload = {
                'transaction_id': stn_number,
                'amount': amount,
                'date': transaction_date.isoformat() if transaction_date else None,
                'api_key': api_key
            }
            
            # Make API request
            response = self.session.post(
                f"{api_url}/verify",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'verified': data.get('verified', False),
                    'bank_response': data,
                    'verification_method': 'api'
                }
            else:
                return {
                    'verified': False,
                    'error': f"API request failed with status {response.status_code}",
                    'bank_response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'verified': False,
                'error': f'API request failed: {str(e)}',
                'bank_response': None
            }
        except Exception as e:
            return {
                'verified': False,
                'error': f'API verification error: {str(e)}',
                'bank_response': None
            }
    
    def _verify_via_web_scraping(self, stn_number: str, amount: float,
                                bank_type: str, transaction_date: datetime = None) -> Dict:
        """Verify transaction via web scraping"""
        try:
            bank_config = self.banks_config[bank_type]
            verification_url = bank_config.get('verification_url')
            
            if not verification_url:
                return {
                    'verified': False,
                    'error': 'Method not available',
                    'bank_response': None
                }
            
            # Prepare form data for web scraping
            form_data = {
                'transaction_id': stn_number,
                'amount': str(amount),
                'date': transaction_date.strftime('%Y-%m-%d') if transaction_date else ''
            }
            
            # Make POST request to verification page
            response = self.session.post(
                verification_url,
                data=form_data,
                timeout=30
            )
            
            if response.status_code == 200:
                # Parse response content
                content = response.text.lower()
                
                # Look for verification indicators
                success_indicators = ['success', 'verified', 'confirmed', 'valid']
                failure_indicators = ['failed', 'invalid', 'not found', 'error']
                
                success_found = any(indicator in content for indicator in success_indicators)
                failure_found = any(indicator in content for indicator in failure_indicators)
                
                if success_found and not failure_found:
                    return {
                        'verified': True,
                        'bank_response': {'status': 'verified via web scraping'},
                        'verification_method': 'web_scraping'
                    }
                elif failure_found:
                    return {
                        'verified': False,
                        'bank_response': {'status': 'not found via web scraping'},
                        'verification_method': 'web_scraping'
                    }
                else:
                    return {
                        'verified': False,
                        'error': 'Could not determine verification status from web page',
                        'bank_response': {'content_length': len(content)}
                    }
            else:
                return {
                    'verified': False,
                    'error': f'Web scraping failed with status {response.status_code}',
                    'bank_response': None
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'verified': False,
                'error': f'Web scraping request failed: {str(e)}',
                'bank_response': None
            }
        except Exception as e:
            return {
                'verified': False,
                'error': f'Web scraping error: {str(e)}',
                'bank_response': None
            }
    
    def _verify_via_embedded_link(self, stn_number: str, amount: float,
                                 bank_type: str, transaction_date: datetime = None) -> Dict:
        """Verify transaction via embedded verification links"""
        try:
            # This method would be used when screenshots contain embedded verification URLs
            # For now, we'll implement a basic version
            
            bank_config = self.banks_config[bank_type]
            base_url = bank_config.get('verification_url', '')
            
            if not base_url:
                return {
                    'verified': False,
                    'error': 'Method not available',
                    'bank_response': None
                }
            
            # Construct verification URL
            verification_url = f"{base_url}?ref={stn_number}&amount={amount}"
            
            # Make GET request to verification URL
            response = self.session.get(verification_url, timeout=30)
            
            if response.status_code == 200:
                # Parse response
                try:
                    data = response.json()
                    return {
                        'verified': data.get('verified', False),
                        'bank_response': data,
                        'verification_method': 'embedded_link'
                    }
                except json.JSONDecodeError:
                    # Try to parse HTML response
                    content = response.text.lower()
                    if 'success' in content or 'verified' in content:
                        return {
                            'verified': True,
                            'bank_response': {'status': 'verified via embedded link'},
                            'verification_method': 'embedded_link'
                        }
                    else:
                        return {
                            'verified': False,
                            'bank_response': {'status': 'not verified via embedded link'},
                            'verification_method': 'embedded_link'
                        }
            else:
                return {
                    'verified': False,
                    'error': f'Embedded link verification failed with status {response.status_code}',
                    'bank_response': None
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'verified': False,
                'error': f'Embedded link request failed: {str(e)}',
                'bank_response': None
            }
        except Exception as e:
            return {
                'verified': False,
                'error': f'Embedded link verification error: {str(e)}',
                'bank_response': None
            }
    
    def extract_verification_url(self, screenshot_text: str, bank_type: str) -> Optional[str]:
        """Extract verification URL from screenshot text"""
        try:
            # Common URL patterns for Ethiopian banks
            url_patterns = {
                'cbe': [
                    r'https?://[^\s]*cbe[^\s]*\.com[^\s]*',
                    r'https?://[^\s]*birr[^\s]*\.com[^\s]*',
                ],
                'telebirr': [
                    r'https?://[^\s]*telebirr[^\s]*\.et[^\s]*',
                    r'https?://[^\s]*ethiotelecom[^\s]*\.et[^\s]*',
                ],
                'dashen': [
                    r'https?://[^\s]*dashenbank[^\s]*\.com[^\s]*',
                    r'https?://[^\s]*dashen[^\s]*\.com[^\s]*',
                ]
            }
            
            patterns = url_patterns.get(bank_type, [])
            
            for pattern in patterns:
                matches = re.findall(pattern, screenshot_text, re.IGNORECASE)
                if matches:
                    return matches[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting verification URL: {e}")
            return None
    
    def batch_verify_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Verify multiple transactions in batch"""
        results = []
        
        for transaction in transactions:
            result = self.verify_transaction(
                stn_number=transaction['stn_number'],
                amount=transaction['amount'],
                bank_type=transaction['bank_type'],
                transaction_date=transaction.get('transaction_date')
            )
            
            result['transaction_id'] = transaction.get('id')
            results.append(result)
        
        return results
    
    def get_bank_status(self, bank_type: str) -> Dict:
        """Get bank API status and configuration"""
        if bank_type not in self.banks_config:
            return {
                'available': False,
                'error': f"Bank {bank_type} not configured"
            }
        
        bank_config = self.banks_config[bank_type]
        
        return {
            'available': bank_config.get('enabled', False),
            'name': bank_config.get('name', bank_type.upper()),
            'api_url': bank_config.get('api_url'),
            'verification_url': bank_config.get('verification_url'),
            'has_api_key': bool(bank_config.get('api_key'))
        }
    
    def test_bank_connection(self, bank_type: str) -> Dict:
        """Test connection to bank API"""
        try:
            bank_config = self.banks_config.get(bank_type)
            if not bank_config:
                return {
                    'success': False,
                    'error': f"Bank {bank_type} not configured"
                }
            
            api_url = bank_config.get('api_url')
            if not api_url:
                return {
                    'success': False,
                    'error': "No API URL configured"
                }
            
            # Test basic connectivity
            response = self.session.get(f"{api_url}/health", timeout=10)
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 