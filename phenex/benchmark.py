import time
import sys
sys.path.insert(0, '..')

from detector import Detector
from tracker import Tracker
from events import EventGenerator
try:
    import importlib

    np = importlib.import_module("numpy")
except ImportError as exc:
    raise RuntimeError(
        "The benchmark requires NumPy. Install it with: python -m pip install numpy"
    ) from exc

def benchmark():
    print("=" * 50)
    print("PheNex Backend Performance Benchmark")
    print("=" * 50)
    
    detector = Detector()
    tracker = Tracker()
    events = EventGenerator()
    
    # Create fake frame
    fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Benchmark detector
    start = time.time()
    for i in range(10):
        detections = detector.detect(fake_frame)
    detector_time = (time.time() - start) / 10 * 1000
    print(f"\n✓ Detector: {detector_time:.2f}ms per frame")
    
    # Benchmark tracker
    fake_detections = [
        {'bbox': [10, 10, 50, 50], 'confidence': 0.9, 'class': 'person'},
        {'bbox': [100, 100, 150, 150], 'confidence': 0.85, 'class': 'vehicle'}
    ]
    
    start = time.time()
    for i in range(100):
        tracks = tracker.update(fake_detections)
    tracker_time = (time.time() - start) / 100 * 1000
    print(f"✓ Tracker: {tracker_time:.2f}ms per frame")
    
    # Benchmark event generation
    start = time.time()
    for i in range(100):
        event_list = events.generate_events(tracks)
    events_time = (time.time() - start) / 100 * 1000
    print(f"✓ Event Generator: {events_time:.2f}ms per frame")
    
    total = detector_time + tracker_time + events_time
    fps = 1000 / total if total > 0 else 0
    
    print(f"\n📊 Total pipeline: {total:.2f}ms")
    print(f"📊 Estimated FPS: {fps:.1f}")
    print("=" * 50)

if __name__ == '__main__':
    benchmark()