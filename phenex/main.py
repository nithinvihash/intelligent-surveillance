import cv2
import time
import threading
import asyncio
import json
from detector import Detector
from tracker import Tracker
from events import EventGenerator
from storage import EventDatabase
from config import Config

# Load configuration before making it available to the API module.
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Make start time globally available
import api as api_module
api_module.pipeline_start_time = time.time()
api_module.config = config  # Pass config to API
from api import app, init_db, broadcast_event, update_frame

import logging
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PipelineRunner:
    def __init__(self, video_source=0):  # 0 = webcam
        self.config = Config('config.json')
        self.video_source = self.config.get('video_source', video_source)
        self.detector = Detector()
        self.tracker = Tracker()
        self.start_time = time.time()
        self.event_gen = EventGenerator()
        self.db = EventDatabase('events.db')
        self.db.add_indexes()
        
        init_db(self.db)
        
        self.running = True
        self.fps = 0
        self.frame_count = 0
    
    def run_detection_loop(self):
        """Main detection loop with error handling"""
        cap = None
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        self.start_time = time.time()
        
        while self.running:
            try:
                if cap is None or not cap.isOpened():
                    print(f"Opening video source: {self.video_source}")
                    cap = cv2.VideoCapture(self.video_source)
                    
                    if not cap.isOpened():
                        reconnect_attempts += 1
                        if reconnect_attempts > max_reconnect_attempts:
                            logger.error("MAX RECONNECTION ATTEMPTS EXCEEDED")
                            break
                        
                        wait_time = min(2 ** reconnect_attempts, 30)  # Exponential backoff
                        logger.warning(f"Failed to open camera. Retry in {wait_time}s (attempt {reconnect_attempts}/{max_reconnect_attempts})")
                        time.sleep(wait_time)
                        continue
                    
                    reconnect_attempts = 0  # Reset on successful connection
                    logger.info("✓ Camera connected")
                
                # Read frame with timeout
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read frame, attempting reconnection...")
                    cap.release()
                    cap = None
                    continue
                
                # Process frame
                try:
                    frame_small = cv2.resize(frame, (480, 360))
                    detections = self.detector.detect(frame_small)
                    tracks = self.tracker.update(detections)
                    events = self.event_gen.generate_events(tracks)
                    
                    # Store events
                    for event in events:
                        try:
                            self.db.store_event(event)
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(broadcast_event(event))
                        except Exception as e:
                            logger.error(f"Failed to store event: {e}")
                    
                    # Draw and update
                    frame_small = self.detector.draw_boxes(frame_small, detections)
                    frame_small = self.tracker.draw_tracks(frame_small, tracks)
                    frame_small = self.event_gen.draw_zones_and_lines(frame_small)
                    
                    self.frame_count += 1
                    elapsed = time.time() - self.start_time
                    self.fps = self.frame_count / elapsed
                    
                    cv2.putText(frame_small, f"FPS: {self.fps:.1f}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    update_frame(frame_small)
                    
                    if self.frame_count % 30 == 0:
                        stats = self.db.get_stats()
                        logger.info(f"Frame {self.frame_count} | FPS: {self.fps:.1f} | Tracks: {len(tracks)} | Events: {stats['total_events']}")
                    
                    # Periodic cleanup
                    if self.frame_count % (1800 * 20) == 0:
                        deleted = self.db.cleanup_old_events(days=7)
                        logger.info(f"Cleanup: deleted {deleted} old events")
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                except Exception as e:
                    logger.error(f"Frame processing error: {e}", exc_info=True)
                    continue
            
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                time.sleep(2)
        
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        self.db.close()
        logger.info("Pipeline stopped")
    
    def start_api_server(self):
        """Start FastAPI server"""
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    print("=" * 50)
    print("PheNex - AI Video Analytics Platform")
    print("=" * 50)
    
    # Use webcam (0) or video file path
    runner = PipelineRunner(video_source=config["video_source"])
    # Start API server in background
    api_thread = threading.Thread(target=runner.start_api_server, daemon=True)
    api_thread.start()
    print("✓ API server starting on http://localhost:8000")
    
    time.sleep(2)
    
    # Start detection pipeline
    print("✓ Starting detection pipeline...")
    runner.run_detection_loop()
    