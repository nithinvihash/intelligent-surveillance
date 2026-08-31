import cv2
import time
import logging
from pathlib import Path

from detector import Detector
from tracker import Tracker
from events import EventGenerator
from storage import EventDatabase
from config import Config

# Try to import API frame update function
try:
    from api import update_frame
    api_available = True
except:
    api_available = False
    update_frame = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineRunner:
    def __init__(self, config_path='config.json'):
        """Initialize pipeline runner"""
        self.config = Config(config_path)
        
        logger.info("Initializing PheNex detection pipeline...")
        
        self.detector = Detector()
        self.tracker = Tracker()
        self.event_gen = EventGenerator(
            line_coords=self.config.get('line_coords'),
            zone_coords=self.config.get('zone_coords')
        )
        self.event_db = EventDatabase(self.config.get('database_path', 'events.db'))
        
        # Optimization settings
        self.detection_interval = self.config.get('detection_interval', 1)
        self.broadcast_enabled = self.config.get('broadcast_events', True)
        
        logger.info(f"✓ Pipeline initialized")
        logger.info(f"  Detection interval: {self.detection_interval}")
        logger.info(f"  Broadcasting: {'enabled' if self.broadcast_enabled else 'disabled'}")
        if api_available:
            logger.info(f"  API frame streaming: enabled")
    
    def run_detection_loop(self):
        """Main detection loop"""
        try:
            cap = cv2.VideoCapture(self.config.get('video_source', 0))
            
            if not cap.isOpened():
                logger.error("Failed to open video source")
                return
            
            logger.info("✓ Camera connected")
            
            # Get frame dimensions
            width = int(self.config.get('frame_width', 480))
            height = int(self.config.get('frame_height', 360))
            logger.info(f"✓ Processing at {width}x{height}")
            
            start_time = time.time()
            frame_count = 0
            detection_count = 0
            last_detections = []
            
            # Frame skipping
            detection_interval = self.detection_interval
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.info("Video ended or failed to read frame")
                    break
                
                try:
                    # Resize frame
                    frame_small = cv2.resize(frame, (width, height))
                    
                    # SEND FRAME TO API FOR VIDEO STREAMING
                    if api_available and update_frame:
                        try:
                            update_frame(frame_small)
                        except Exception as e:
                            logger.debug(f"API frame update error: {e}")
                    
                    # Frame skipping for detection
                    if frame_count % detection_interval == 0:
                        detections = self.detector.detect(frame_small)
                        last_detections = detections
                        detection_count += 1
                    else:
                        detections = last_detections
                    
                    # Update tracker
                    tracks = self.tracker.update(detections)
                    
                    # Generate events
                    new_events = self.event_gen.process_frame(detections, tracks, frame_small)
                    
                    # Store events
                    for event in new_events:
                        self.event_db.store_event(event)
                        if self.broadcast_enabled:
                            logger.info(f"✓ Event: {event['type']} - {event.get('class', 'unknown')} (ID: {event.get('track_id')})")
                    
                    frame_count += 1
                    
                    # Log statistics every 30 frames (~3 seconds)
                    if frame_count % 30 == 0:
                        elapsed = time.time() - start_time
                        fps = frame_count / elapsed
                        stats = self.event_db.get_stats()
                        logger.info(
                            f"Frame {frame_count} | "
                            f"FPS: {fps:.1f} | "
                            f"Detections: {detection_count} | "
                            f"Tracks: {len(tracks)} | "
                            f"Events: {stats.get('total_events', 0)}"
                        )
                
                except Exception as e:
                    logger.error(f"Frame processing error: {e}")
                    continue
            
            cap.release()
            logger.info("✓ Camera released")
        
        except KeyboardInterrupt:
            logger.info("Detection loop interrupted by user")
            cap.release()
        except Exception as e:
            logger.error(f"Error in detection loop: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Run pipeline"""
        self.run_detection_loop()

if __name__ == '__main__':
    runner = PipelineRunner('config.json')
    runner.run()