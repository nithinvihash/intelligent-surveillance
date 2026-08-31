import re
import logging

logger = logging.getLogger(__name__)

class PlateValidator:
    def __init__(self):
        """Initialize validator with Indian plate format"""
        # Indian format: TN 38 AB 1234 or TN38AB1234
        self.plate_pattern = r'^[A-Z]{2}\s*\d{2}\s*[A-Z]{2}\s*\d{4}$'
        
        # Common OCR character mistakes
        self.ocr_corrections = {
            'O': '0',  # O -> 0
            'o': '0',
            'l': '1',  # l -> 1
            'L': '1',
            'S': '5',  # S -> 5
            's': '5',
            'Z': '2',  # Z -> 2
            'G': '6',  # G -> 6
            'B': '8',  # B -> 8
        }
    
    def clean_ocr_text(self, text):
        """
        Clean OCR output by fixing common mistakes
        
        Args:
            text: Raw OCR output
        
        Returns:
            Cleaned text
        """
        text = text.upper().strip()
        
        # Fix common OCR errors
        for mistake, correction in self.ocr_corrections.items():
            text = text.replace(mistake, correction)
        
        # Remove special characters except spaces and digits
        text = re.sub(r'[^A-Z0-9\s]', '', text)
        
        return text.strip()
    
    def normalize(self, text):
        """
        Normalize plate to standard format
        
        Args:
            text: Plate text (may be dirty)
        
        Returns:
            Normalized format: "TN 38 AB 1234"
        """
        text = self.clean_ocr_text(text)
        
        # Remove all spaces
        text_no_space = text.replace(' ', '')
        
        # Check if valid format
        if len(text_no_space) == 10:
            # Assume format: TN38AB1234
            normalized = f"{text_no_space[0:2]} {text_no_space[2:4]} {text_no_space[4:6]} {text_no_space[6:10]}"
            return normalized
        elif len(text_no_space) < 10:
            # Try to pad with reasonable defaults
            logger.warning(f"Plate too short: {text_no_space}")
            return text
        else:
            # Too long, extract first 10 chars
            logger.warning(f"Plate too long: {text_no_space}")
            return f"{text_no_space[0:2]} {text_no_space[2:4]} {text_no_space[4:6]} {text_no_space[6:10]}"
    
    def validate(self, text):
        """
        Validate plate format
        
        Args:
            text: Plate text
        
        Returns:
            True if valid format, False otherwise
        """
        text = text.upper().strip()
        
        # Check pattern
        if re.match(self.plate_pattern, text):
            return True
        
        # Also validate cleaned version
        cleaned = self.clean_ocr_text(text)
        if re.match(self.plate_pattern, cleaned):
            return True
        
        return False
    
    def extract_components(self, text):
        """
        Extract plate components
        
        Args:
            text: Plate text
        
        Returns:
            {'state': 'TN', 'district': '38', 'series': 'AB', 'number': '1234'}
        """
        text = text.replace(' ', '').upper()
        
        if len(text) >= 10:
            return {
                'state': text[0:2],
                'district': text[2:4],
                'series': text[4:6],
                'number': text[6:10]
            }
        
        return None