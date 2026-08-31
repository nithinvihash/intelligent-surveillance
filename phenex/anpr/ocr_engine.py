import easyocr
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class OCREngine:
    def __init__(self, languages=['en']):
        """
        Initialize OCR engine
        
        Args:
            languages: List of languages to recognize
        """
        try:
            self.reader = easyocr.Reader(languages, gpu=False)  # Set gpu=True if available
            logger.info("✓ OCR engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OCR: {e}")
            self.reader = None
    
    def extract_text(self, plate_image, confidence_threshold=0.3):
        """
        Extract text from plate image
        
        Args:
            plate_image: Plate image (preprocessed recommended)
            confidence_threshold: Minimum confidence for text
        
        Returns:
            {'text': '...', 'confidence': 0.9, 'raw_results': [...]}
        """
        if self.reader is None:
            return {'text': '', 'confidence': 0.0, 'raw_results': []}
        
        try:
            results = self.reader.readtext(plate_image)
            
            if not results:
                return {'text': '', 'confidence': 0.0, 'raw_results': []}
            
            # Filter by confidence
            filtered = [r for r in results if r[2] >= confidence_threshold]
            
            if not filtered:
                filtered = results  # Fall back to all results
            
            # Extract text
            text_parts = [r[1] for r in filtered]
            text = ''.join(text_parts).strip()
            
            # Calculate average confidence
            confidence = sum([r[2] for r in filtered]) / len(filtered) if filtered else 0.0
            
            return {
                'text': text,
                'confidence': confidence,
                'raw_results': filtered
            }
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return {'text': '', 'confidence': 0.0, 'raw_results': []}