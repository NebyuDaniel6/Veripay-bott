"""
Fraud Detector for VeriPay - Detects manipulated payment screenshots
"""
import cv2
import numpy as np
from PIL import Image, ImageFilter
import hashlib
from typing import Dict, List, Tuple, Optional
import yaml
from loguru import logger
import os
from datetime import datetime


class FraudDetector:
    """AI-powered fraud detection for payment screenshots"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize fraud detector"""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        self.fraud_config = self.config['ai']['fraud_detection']
        self.confidence_threshold = self.fraud_config['confidence_threshold']
        
        # Load pre-trained model if available
        self.model = None
        if os.path.exists(self.fraud_config['model_path']):
            try:
                import tensorflow as tf
                self.model = tf.keras.models.load_model(self.fraud_config['model_path'])
                logger.info("Loaded fraud detection model")
            except Exception as e:
                logger.warning(f"Could not load fraud detection model: {e}")
    
    def analyze_screenshot(self, image_path: str) -> Dict:
        """
        Analyze screenshot for potential fraud
        
        Returns:
            Dict containing fraud analysis results
        """
        try:
            fraud_indicators = []
            fraud_score = 0.0
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            # 1. Check EXIF data
            if self.fraud_config['check_exif']:
                exif_analysis = self._check_exif_data(image_path)
                if exif_analysis['suspicious']:
                    fraud_indicators.append(exif_analysis['reason'])
                    fraud_score += 0.3
            
            # 2. Check for noise inconsistencies
            if self.fraud_config['check_noise']:
                noise_analysis = self._check_noise_patterns(image)
                if noise_analysis['suspicious']:
                    fraud_indicators.append(noise_analysis['reason'])
                    fraud_score += 0.4
            
            # 3. Check for font inconsistencies
            if self.fraud_config['check_fonts']:
                font_analysis = self._check_font_consistency(image)
                if font_analysis['suspicious']:
                    fraud_indicators.append(font_analysis['reason'])
                    fraud_score += 0.3
            
            # 4. Check for compression artifacts
            compression_analysis = self._check_compression_artifacts(image)
            if compression_analysis['suspicious']:
                fraud_indicators.append(compression_analysis['reason'])
                fraud_score += 0.2
            
            # 5. Check for duplicate regions
            duplicate_analysis = self._check_duplicate_regions(image)
            if duplicate_analysis['suspicious']:
                fraud_indicators.append(duplicate_analysis['reason'])
                fraud_score += 0.5
            
            # 6. Check for edge inconsistencies
            edge_analysis = self._check_edge_consistency(image)
            if edge_analysis['suspicious']:
                fraud_indicators.append(edge_analysis['reason'])
                fraud_score += 0.3
            
            # 7. Use ML model if available
            if self.model:
                ml_analysis = self._ml_fraud_detection(image)
                fraud_score += ml_analysis['score'] * 0.4
                if ml_analysis['suspicious']:
                    fraud_indicators.append(ml_analysis['reason'])
            
            # Normalize fraud score to 0-1 range
            fraud_score = min(fraud_score, 1.0)
            
            # Determine overall suspicion level
            if fraud_score >= self.confidence_threshold:
                is_suspicious = True
                suspicion_level = "HIGH"
            elif fraud_score >= 0.3:
                is_suspicious = True
                suspicion_level = "MEDIUM"
            else:
                is_suspicious = False
                suspicion_level = "LOW"
            
            return {
                'fraud_score': fraud_score,
                'is_suspicious': is_suspicious,
                'suspicion_level': suspicion_level,
                'fraud_indicators': fraud_indicators,
                'analysis_details': {
                    'exif_analysis': exif_analysis if self.fraud_config['check_exif'] else None,
                    'noise_analysis': noise_analysis if self.fraud_config['check_noise'] else None,
                    'font_analysis': font_analysis if self.fraud_config['check_fonts'] else None,
                    'compression_analysis': compression_analysis,
                    'duplicate_analysis': duplicate_analysis,
                    'edge_analysis': edge_analysis,
                    'ml_analysis': ml_analysis if self.model else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error in fraud analysis: {e}")
            return {
                'fraud_score': 0.0,
                'is_suspicious': False,
                'suspicion_level': "UNKNOWN",
                'fraud_indicators': [f"Analysis error: {str(e)}"],
                'analysis_details': {}
            }
    
    def _check_exif_data(self, image_path: str) -> Dict:
        """Check EXIF data for inconsistencies"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            image = Image.open(image_path)
            exif_data = image._getexif()
            
            if exif_data is None:
                return {
                    'suspicious': False,
                    'reason': "No EXIF data found (normal for screenshots)"
                }
            
            # Check for suspicious EXIF data
            suspicious_fields = []
            
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                
                # Check for editing software
                if tag in ['Software', 'ProcessingSoftware']:
                    if any(editor in str(value).lower() for editor in ['photoshop', 'gimp', 'paint', 'edit']):
                        suspicious_fields.append(f"Editing software detected: {value}")
                
                # Check for unusual timestamps
                if tag in ['DateTime', 'DateTimeOriginal']:
                    try:
                        exif_time = datetime.strptime(str(value), '%Y:%m:%d %H:%M:%S')
                        current_time = datetime.now()
                        if exif_time > current_time:
                            suspicious_fields.append(f"Future timestamp in EXIF: {value}")
                    except:
                        pass
            
            if suspicious_fields:
                return {
                    'suspicious': True,
                    'reason': f"EXIF inconsistencies: {'; '.join(suspicious_fields)}"
                }
            else:
                return {
                    'suspicious': False,
                    'reason': "EXIF data appears normal"
                }
                
        except Exception as e:
            return {
                'suspicious': False,
                'reason': f"Could not analyze EXIF data: {str(e)}"
            }
    
    def _check_noise_patterns(self, image: np.ndarray) -> Dict:
        """Check for noise pattern inconsistencies"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise detection filters
            # 1. Check for uniform noise patterns
            noise_variance = np.var(gray)
            
            # 2. Check for noise distribution
            noise_hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            noise_entropy = -np.sum(noise_hist * np.log2(noise_hist + 1e-10))
            
            # 3. Check for noise consistency across regions
            height, width = gray.shape
            regions = [
                gray[:height//2, :width//2],  # Top-left
                gray[:height//2, width//2:],  # Top-right
                gray[height//2:, :width//2],  # Bottom-left
                gray[height//2:, width//2:]   # Bottom-right
            ]
            
            region_variances = [np.var(region) for region in regions]
            variance_std = np.std(region_variances)
            
            # Determine if noise patterns are suspicious
            suspicious_indicators = []
            
            if noise_variance < 100:  # Very low noise
                suspicious_indicators.append("Unusually low noise variance")
            
            if noise_entropy < 4.0:  # Low entropy
                suspicious_indicators.append("Low noise entropy")
            
            if variance_std > 500:  # Inconsistent noise across regions
                suspicious_indicators.append("Inconsistent noise patterns across regions")
            
            if suspicious_indicators:
                return {
                    'suspicious': True,
                    'reason': f"Noise pattern issues: {'; '.join(suspicious_indicators)}"
                }
            else:
                return {
                    'suspicious': False,
                    'reason': "Noise patterns appear normal"
                }
                
        except Exception as e:
            return {
                'suspicious': False,
                'reason': f"Could not analyze noise patterns: {str(e)}"
            }
    
    def _check_font_consistency(self, image: np.ndarray) -> Dict:
        """Check for font consistency issues"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze text regions
            text_regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if 10 < w < 200 and 10 < h < 50:  # Reasonable text region size
                    text_regions.append((x, y, w, h))
            
            if len(text_regions) < 3:
                return {
                    'suspicious': False,
                    'reason': "Insufficient text regions for analysis"
                }
            
            # Check for font size consistency
            heights = [h for _, _, _, h in text_regions]
            height_std = np.std(heights)
            height_mean = np.mean(heights)
            
            # Check for unusual font size variations
            if height_std > height_mean * 0.5:
                return {
                    'suspicious': True,
                    'reason': "Inconsistent font sizes detected"
                }
            
            return {
                'suspicious': False,
                'reason': "Font consistency appears normal"
            }
            
        except Exception as e:
            return {
                'suspicious': False,
                'reason': f"Could not analyze font consistency: {str(e)}"
            }
    
    def _check_compression_artifacts(self, image: np.ndarray) -> Dict:
        """Check for compression artifacts"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply DCT to detect compression artifacts
            # This is a simplified version - in practice, you'd use more sophisticated methods
            
            # Check for block artifacts
            height, width = gray.shape
            block_size = 8
            
            artifacts_found = 0
            total_blocks = 0
            
            for y in range(0, height - block_size, block_size):
                for x in range(0, width - block_size, block_size):
                    block = gray[y:y+block_size, x:x+block_size]
                    
                    # Check for sudden intensity changes at block boundaries
                    if x > 0:
                        left_edge_diff = np.mean(np.abs(block[:, 0] - gray[y:y+block_size, x-1]))
                        if left_edge_diff > 30:
                            artifacts_found += 1
                    
                    if y > 0:
                        top_edge_diff = np.mean(np.abs(block[0, :] - gray[y-1, x:x+block_size]))
                        if top_edge_diff > 30:
                            artifacts_found += 1
                    
                    total_blocks += 1
            
            artifact_ratio = artifacts_found / total_blocks if total_blocks > 0 else 0
            
            if artifact_ratio > 0.1:  # More than 10% of blocks show artifacts
                return {
                    'suspicious': True,
                    'reason': f"High compression artifacts detected ({artifact_ratio:.2%})"
                }
            else:
                return {
                    'suspicious': False,
                    'reason': "Compression artifacts appear normal"
                }
                
        except Exception as e:
            return {
                'suspicious': False,
                'reason': f"Could not analyze compression artifacts: {str(e)}"
            }
    
    def _check_duplicate_regions(self, image: np.ndarray) -> Dict:
        """Check for duplicate or copied regions"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Use template matching to find similar regions
            height, width = gray.shape
            template_size = min(50, width // 4, height // 4)
            
            # Sample regions and compare
            suspicious_regions = 0
            total_comparisons = 0
            
            for y1 in range(0, height - template_size, template_size // 2):
                for x1 in range(0, width - template_size, template_size // 2):
                    template = gray[y1:y1+template_size, x1:x1+template_size]
                    
                    for y2 in range(y1 + template_size, height - template_size, template_size // 2):
                        for x2 in range(0, width - template_size, template_size // 2):
                            # Skip if regions overlap
                            if (x1 < x2 + template_size and x1 + template_size > x2 and
                                y1 < y2 + template_size and y1 + template_size > y2):
                                continue
                            
                            region = gray[y2:y2+template_size, x2:x2+template_size]
                            
                            # Calculate similarity
                            correlation = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
                            similarity = np.max(correlation)
                            
                            if similarity > 0.95:  # Very high similarity
                                suspicious_regions += 1
                            
                            total_comparisons += 1
            
            duplicate_ratio = suspicious_regions / total_comparisons if total_comparisons > 0 else 0
            
            if duplicate_ratio > 0.05:  # More than 5% similarity
                return {
                    'suspicious': True,
                    'reason': f"Duplicate regions detected ({duplicate_ratio:.2%})"
                }
            else:
                return {
                    'suspicious': False,
                    'reason': "No significant duplicate regions found"
                }
                
        except Exception as e:
            return {
                'suspicious': False,
                'reason': f"Could not analyze duplicate regions: {str(e)}"
            }
    
    def _check_edge_consistency(self, image: np.ndarray) -> Dict:
        """Check for edge consistency issues"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Check for edge density consistency
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            
            # Check for edge direction consistency
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
            gradient_direction = np.arctan2(sobely, sobelx)
            
            # Check for unusual edge patterns
            if edge_density < 0.01:  # Very few edges
                return {
                    'suspicious': True,
                    'reason': "Unusually low edge density"
                }
            
            if edge_density > 0.3:  # Too many edges
                return {
                    'suspicious': True,
                    'reason': "Unusually high edge density"
                }
            
            return {
                'suspicious': False,
                'reason': "Edge consistency appears normal"
            }
            
        except Exception as e:
            return {
                'suspicious': False,
                'reason': f"Could not analyze edge consistency: {str(e)}"
            }
    
    def _ml_fraud_detection(self, image: np.ndarray) -> Dict:
        """Use machine learning model for fraud detection"""
        try:
            if self.model is None:
                return {
                    'suspicious': False,
                    'reason': "ML model not available",
                    'score': 0.0
                }
            
            # Preprocess image for ML model
            resized = cv2.resize(image, (224, 224))
            normalized = resized / 255.0
            input_tensor = np.expand_dims(normalized, axis=0)
            
            # Get prediction
            prediction = self.model.predict(input_tensor, verbose=0)
            fraud_probability = prediction[0][0]
            
            if fraud_probability > self.confidence_threshold:
                return {
                    'suspicious': True,
                    'reason': f"ML model detected fraud (confidence: {fraud_probability:.2f})",
                    'score': fraud_probability
                }
            else:
                return {
                    'suspicious': False,
                    'reason': f"ML model found no fraud (confidence: {1-fraud_probability:.2f})",
                    'score': fraud_probability
                }
                
        except Exception as e:
            return {
                'suspicious': False,
                'reason': f"ML analysis failed: {str(e)}",
                'score': 0.0
            } 