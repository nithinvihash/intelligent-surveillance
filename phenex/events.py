import logging
import time
import cv2
import numpy as np
from datetime import datetime
 
# ANPR imports - commented out until implementation complete
# from phenex.anpr.plate_detector import PlateDetector
# from phenex.anpr.ocr_engine import OCREngine
# from phenex.anpr.plate_validator import PlateValidator
 
logger = logging.getLogger(__name__)
 
class EventGenerator:
    def __init__(self, line_coords=None, zone_coords=None):
        """
        Initialize event generator
        
        Args:
            line_coords: Line crossing coordinates [x1, y1, x2, y2]
            zone_coords: Zone polygon coordinates [[x1,y1], [x2,y2], ...]
        """
        self.line = line_coords or [100, 100, 600, 100]
        self.zone = zone_coords or [[200, 200], [600, 200], [600, 400], [200, 400]]
        
        self.events = []
        self.crossed_tracks = set()
        
        # ANPR components - commented out until implementation
        # self.plate_detector = PlateDetector()
        # self.ocr = OCREngine()
        # self.plate_validator = PlateValidator()
        # self.anpr_enabled = True
        
        logger.info("✓ Event generator initialized")
    
    def process_frame(self, detections, tracks, frame=None):
        """
        Process frame and generate events
        
        Args:
            detections: List of detections from YOLOv8
            tracks: Dictionary of tracked objects
            frame: Current frame (optional, for ANPR)
        
        Returns:
            List of new events generated
        """
        new_events = []
        
        for track_id, track in tracks.items():
            centroid = track.get('centroid')
            bbox = track.get('bbox')
            class_name = track.get('class', 'unknown')
            confidence = track.get('confidence', 0.0)
            age = track.get('age', 0)
            
            if not centroid:
                continue
            
            # Check line crossing
            if self._line_crossed(track.get('history', []), centroid):
                event = {
                    'type': 'line_crossed',
                    'track_id': track_id,
                    'class': class_name,
                    'confidence': confidence,
                    'timestamp': time.time(),
                    'position': centroid,
                    'direction': self._get_direction(track.get('history', [])),
                    'risk_score': self._calculate_risk(class_name, confidence)
                }
                new_events.append(event)
                logger.info(f"✓ Event: Line crossed by {class_name} (ID: {track_id})")
            
            # Check zone entry/exit
            if self._point_in_zone(centroid):
                event = {
                    'type': 'zone_entry',
                    'track_id': track_id,
                    'class': class_name,
                    'confidence': confidence,
                    'timestamp': time.time(),
                    'position': centroid,
                    'risk_score': self._calculate_risk(class_name, confidence)
                }
                if track_id not in self.crossed_tracks:
                    new_events.append(event)
                    self.crossed_tracks.add(track_id)
                    logger.info(f"✓ Event: Zone entry by {class_name} (ID: {track_id})")
        
        # ANPR processing commented out until implementation
        # if frame is not None and self.anpr_enabled:
        #     for track_id, track in tracks.items():
        #         if track.get('class') in ['car', 'truck', 'bus', 'motorcycle']:
        #             anpr_result = self.process_anpr(frame, track['bbox'], track_id, track['class'])
        #             if anpr_result:
        #                 new_events.append(anpr_result)
        
        return new_events
    
    def _line_crossed(self, history, current_point):
        """
        Check if object has crossed the line
        Uses CCW (counter-clockwise) method for accurate line intersection
        """
        if len(history) < 1:
            return False
        
        prev_point = history[-1]
        x1, y1, x2, y2 = self.line
        
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
        
        line_p1 = (x1, y1)
        line_p2 = (x2, y2)
        
        return ccw(line_p1, prev_point, current_point) != ccw(line_p2, prev_point, current_point) and \
               ccw(line_p1, line_p2, prev_point) != ccw(line_p1, line_p2, current_point)
    
    def _point_in_zone(self, point):
        """Check if point is inside zone polygon"""
        x, y = point
        n = len(self.zone)
        inside = False
        
        p1x, p1y = self.zone[0]
        for i in range(1, n + 1):
            p2x, p2y = self.zone[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _get_direction(self, history):
        """Determine direction of movement"""
        if len(history) < 2:
            return "unknown"
        
        prev = history[-2]
        curr = history[-1]
        
        dx = curr[0] - prev[0]
        dy = curr[1] - prev[1]
        
        if abs(dx) > abs(dy):
            return "left_to_right" if dx > 0 else "right_to_left"
        else:
            return "top_to_bottom" if dy > 0 else "bottom_to_top"
    
    def _calculate_risk(self, class_name, confidence):
        """Calculate risk score based on class and confidence"""
        base_risk = {
            'person': 0.3,
            'car': 0.5,
            'truck': 0.7,
            'bus': 0.6,
            'motorcycle': 0.6,
            'bicycle': 0.2
        }
        
        risk = base_risk.get(class_name, 0.4)
        return min(risk * confidence, 1.0)
    
    # ANPR method - commented out until implementation
    # def process_anpr(self, frame, vehicle_bbox, track_id, class_name):
    #     """Process ANPR for vehicle"""
    #     if not self.anpr_enabled:
    #         return None
    #     
    #     try:
    #         x1, y1, x2, y2 = vehicle_bbox
    #         vehicle_roi = frame[int(y1):int(y2), int(x1):int(x2)]
    #         
    #         if vehicle_roi.size == 0:
    #             return None
    #         
    #         plates = self.plate_detector.detect_plates(vehicle_roi, confidence=0.5)
    #         if not plates:
    #             return None
    #         
    #         best_plate = max(plates, key=lambda p: p['confidence'])
    #         plate_crop = self.plate_detector.crop_plate(vehicle_roi, best_plate['bbox'])
    #         
    #         if plate_crop is None or plate_crop.size == 0:
    #             return None
    #         
    #         processed_plate = self.plate_detector.preprocess_plate(plate_crop)
    #         ocr_result = self.ocr.extract_text(processed_plate)
    #         
    #         if not ocr_result['text']:
    #             return None
    #         
    #         text = ocr_result['text']
    #         if not self.plate_validator.validate(text):
    #             text = self.plate_validator.clean_ocr_text(text)
    #             if not self.plate_validator.validate(text):
    #                 return None
    #         
    #         normalized = self.plate_validator.normalize(text)
    #         components = self.plate_validator.extract_components(normalized)
    #         
    #         return {
    #             'type': 'anpr',
    #             'plate_text': normalized,
    #             'ocr_confidence': ocr_result['confidence'],
    #             'plate_confidence': best_plate['confidence'],
    #             'combined_confidence': (ocr_result['confidence'] + best_plate['confidence']) / 2,
    #             'track_id': track_id,
    #             'class': class_name,
    #             'timestamp': time.time(),
    #             'components': components
    #         }
    #     except Exception as e:
    #         logger.error(f"ANPR error: {e}")
    #         return None