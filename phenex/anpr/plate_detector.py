import cv2
import numpy as np
from ultralytics import YOLO
import logging

logger = logging.getLogger(__name__)

class PlateDetector:
    def __init__(self, model_path=None):
        """
        Initialize plate detector
        
        Args:
            model_path: Path to YOLO license plate model
                       If None, will use general object detection
        """
        try:
            if model_path:
                self.model = YOLO(model_path)
            else:
                # Fallback: Use YOLOv8n for general detection
                # You can train a custom model for better plate detection
                self.model = YOLO('yolov8n.pt')
            logger.info("✓ Plate detector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize plate detector: {e}")
            self.model = None
    
    def detect_plates(self, vehicle_roi, confidence=0.5):
        """
        Detect license plates in vehicle ROI
        
        Args:
            vehicle_roi: Cropped vehicle image
            confidence: Detection confidence threshold
        
        Returns:
            List of plates: [{'bbox': [x1,y1,x2,y2], 'confidence': float}, ...]
        """
        if self.model is None:
            return []
        
        try:
            results = self.model(vehicle_roi, verbose=False, conf=confidence)
            plates = []
            
            for r in results:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    if conf >= confidence:
                        bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                        plates.append({
                            'bbox': bbox,
                            'confidence': conf
                        })
            
            return plates
        except Exception as e:
            logger.error(f"Error detecting plates: {e}")
            return []
    
    def crop_plate(self, frame, bbox):
        """
        Crop plate region from frame
        
        Args:
            frame: Input frame
            bbox: Bounding box [x1, y1, x2, y2]
        
        Returns:
            Cropped plate image
        """
        try:
            x1, y1, x2, y2 = bbox
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Add padding for better OCR
            padding = 5
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(frame.shape[1], x2 + padding)
            y2 = min(frame.shape[0], y2 + padding)
            
            return frame[y1:y2, x1:x2]
        except Exception as e:
            logger.error(f"Error cropping plate: {e}")
            return None
    
    def preprocess_plate(self, plate_image):
        """
        Preprocess plate image for better OCR
        
        Args:
            plate_image: Cropped plate image
        
        Returns:
            Preprocessed image
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Resize for better OCR
            height = enhanced.shape[0]
            if height < 50:
                enhanced = cv2.resize(enhanced, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            # Threshold
            _, thresh = cv2.threshold(enhanced, 150, 255, cv2.THRESH_BINARY)
            
            return thresh
        except Exception as e:
            logger.error(f"Error preprocessing plate: {e}")
            return plate_image