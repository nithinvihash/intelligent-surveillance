import cv2
from ultralytics import YOLO
import time
import warnings
warnings.filterwarnings('ignore')
class Detector:
    def __init__(self):
        print("Loading YOLOv8n model...")
        self.model = YOLO('yolov8n.pt')
        print("✓ Model loaded!")
    
    def detect(self, frame):
        """Run detection on single frame, return detections"""
        results = self.model(frame, verbose=False, conf=0.5)
        
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                class_name = self.model.names[cls]
                
                # Only keep person and vehicle
                if class_name in ['person', 'car', 'truck', 'bus', 'motorcycle']:
                    detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': conf,
                        'class': class_name,
                        'class_id': cls
                    })
        
        return detections
    
    def draw_boxes(self, frame, detections):
        """Draw bounding boxes on frame"""
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']
            cls_name = det['class']
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{cls_name} {conf:.2f}"
            cv2.putText(frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame

if __name__ == "__main__":
    detector = Detector()
    cap = cv2.VideoCapture("data/sample_video.mp4")
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        detections = detector.detect(frame)
        frame = detector.draw_boxes(frame, detections)
        
        frame_count += 1
        elapsed = time.time() - start_time
        fps = frame_count / elapsed
        
        cv2.imshow('Detector', frame)
        
        if frame_count % 30 == 0:
            print(f"Frame {frame_count}: {len(detections)} objects, FPS: {fps:.1f}")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"Done. Total FPS: {fps:.1f}")