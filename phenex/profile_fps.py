import cv2
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from detector import Detector
from tracker import Tracker
from events import EventGenerator
from storage import EventDatabase
from config import Config

def profile_components():
    """Profile each component individually"""
    
    config = Config('config.json')
    cap = cv2.VideoCapture(config.get('video_source', 0))
    
    detector = Detector()
    tracker = Tracker()
    events = EventGenerator()
    db = EventDatabase(config.get('database_path', 'events.db'))
    
    # Read first 100 frames
    frames = []
    for i in range(100):
        ret, frame = cap.read()
        if ret:
            frames.append(cv2.resize(frame, (480, 360)))
        else:
            break
    
    cap.release()
    
    print("\n" + "="*60)
    print("FPS PROFILING - Component Breakdown")
    print("="*60)
    
    # 1. FRAME I/O
    print("\n📹 1. FRAME I/O (read + resize)")
    cap = cv2.VideoCapture(config.get('video_source', 0))
    start = time.time()
    frame_count = 0
    for i in range(100):
        ret, frame = cap.read()
        if ret:
            frame_small = cv2.resize(frame, (480, 360))
            frame_count += 1
    io_time = time.time() - start
    io_fps = frame_count / io_time
    cap.release()
    print(f"   Time: {io_time:.2f}s | FPS: {io_fps:.1f}")
    print(f"   Per frame: {(io_time/frame_count)*1000:.1f}ms")
    
    # 2. DETECTION ONLY
    print("\n🎯 2. DETECTION ONLY (YOLOv8n)")
    start = time.time()
    detection_count = 0
    for frame in frames[:100]:
        detections = detector.detect(frame)
        detection_count += 1
    det_time = time.time() - start
    det_fps = detection_count / det_time
    print(f"   Time: {det_time:.2f}s | FPS: {det_fps:.1f}")
    print(f"   Per frame: {(det_time/detection_count)*1000:.1f}ms")
    
    # 3. TRACKING ONLY (without detection)
    print("\n🔗 3. TRACKING ONLY (with dummy detections)")
    dummy_detections = [{
        'bbox': [100, 100, 200, 200],
        'confidence': 0.9,
        'class': 'person',
        'class_id': 0
    }]
    start = time.time()
    track_count = 0
    for i in range(100):
        tracks = tracker.update(dummy_detections)
        track_count += 1
    track_time = time.time() - start
    track_fps = track_count / track_time
    print(f"   Time: {track_time:.2f}s | FPS: {track_fps:.1f}")
    print(f"   Per frame: {(track_time/track_count)*1000:.1f}ms")
    
    # 4. EVENT PROCESSING
    print("\n⚡ 4. EVENT PROCESSING")
    dummy_tracks = {1: {
        'centroid': (150, 150),
        'bbox': [100, 100, 200, 200],
        'class': 'person',
        'confidence': 0.9,
        'age': 5,
        'frames_alive': 5,
        'history': [(100, 100), (110, 110), (120, 120)]
    }}
    start = time.time()
    event_count = 0
    for i in range(100):
        events_list = events.process_frame(dummy_detections, dummy_tracks, frames[0])
        event_count += 1
    event_time = time.time() - start
    event_fps = event_count / event_time
    print(f"   Time: {event_time:.2f}s | FPS: {event_fps:.1f}")
    print(f"   Per frame: {(event_time/event_count)*1000:.1f}ms")
    
    # 5. DATABASE STORAGE
    print("\n💾 5. DATABASE STORAGE")
    test_event = {
        'type': 'line_crossed',
        'track_id': 1,
        'timestamp': time.time(),
        'confidence': 0.9,
        'class': 'person',
        'direction': 'left_to_right',
        'risk_score': 0.75
    }
    start = time.time()
    db_count = 0
    for i in range(100):
        db.store_event(test_event)
        db_count += 1
    db_time = time.time() - start
    db_fps = db_count / db_time
    print(f"   Time: {db_time:.2f}s | FPS: {db_fps:.1f}")
    print(f"   Per frame: {(db_time/db_count)*1000:.1f}ms")
    
    # 6. FULL PIPELINE
    print("\n🔄 6. FULL PIPELINE (all together)")
    cap = cv2.VideoCapture(config.get('video_source', 0))
    start = time.time()
    pipeline_count = 0
    for i in range(100):
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_small = cv2.resize(frame, (480, 360))
        detections = detector.detect(frame_small)
        tracks = tracker.update(detections)
        events_list = events.process_frame(detections, tracks, frame_small)
        
        for event in events_list:
            db.store_event(event)
        
        pipeline_count += 1
    
    pipeline_time = time.time() - start
    pipeline_fps = pipeline_count / pipeline_time
    cap.release()
    print(f"   Time: {pipeline_time:.2f}s | FPS: {pipeline_fps:.1f}")
    print(f"   Per frame: {(pipeline_time/pipeline_count)*1000:.1f}ms")
    
    # SUMMARY
    print("\n" + "="*60)
    print("📊 SUMMARY & BOTTLENECK ANALYSIS")
    print("="*60)
    print(f"\nFrame I/O:         {io_fps:.1f} FPS ({(io_time/100)*1000:.1f}ms)")
    print(f"Detection:         {det_fps:.1f} FPS ({(det_time/100)*1000:.1f}ms) ← BOTTLENECK?")
    print(f"Tracking:          {track_fps:.1f} FPS ({(track_time/100)*1000:.1f}ms)")
    print(f"Event Processing:  {event_fps:.1f} FPS ({(event_time/100)*1000:.1f}ms)")
    print(f"Database:          {db_fps:.1f} FPS ({(db_time/100)*1000:.1f}ms)")
    print(f"\nFull Pipeline:     {pipeline_fps:.1f} FPS ({(pipeline_time/100)*1000:.1f}ms)")
    
    # Identify bottleneck
    times = {
        'I/O': (io_time/100)*1000,
        'Detection': (det_time/100)*1000,
        'Tracking': (track_time/100)*1000,
        'Events': (event_time/100)*1000,
        'Database': (db_time/100)*1000
    }
    
    bottleneck = max(times, key=times.get)
    print(f"\n🔴 MAIN BOTTLENECK: {bottleneck} ({times[bottleneck]:.1f}ms per frame)")
    
    print("\n" + "="*60)
    print("Recommendations:")
    print("="*60)
    
    if bottleneck == 'Detection':
        print("✓ Use frame skipping (detection every N frames)")
        print("✓ Lower resolution")
        print("✓ Use GPU acceleration (if available)")
        print("✓ Switch to faster model (YOLOv8n-mobile)")
    elif bottleneck == 'I/O':
        print("✓ Check video file format")
        print("✓ Use lower resolution input")
        print("✓ Pre-process video offline")
    elif bottleneck == 'Tracking':
        print("✓ Simplify tracking algorithm")
        print("✓ Reduce history size")
    elif bottleneck == 'Events':
        print("✓ Skip event processing on some frames")
        print("✓ Simplify event logic")
    elif bottleneck == 'Database':
        print("✓ Batch database inserts")
        print("✓ Use in-memory queue, write periodically")
    
    print("\n")

if __name__ == '__main__':
    profile_components()