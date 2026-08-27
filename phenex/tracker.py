import cv2
import numpy as np
from collections import defaultdict

class Tracker:
    def __init__(self, max_distance=50, max_age=30):
        self.tracks = {}
        self.next_id = 0
        self.max_distance = max_distance
        self.max_age = max_age
    
    def update(self, detections):
        """Update tracks with new detections"""
        
        # Get centroids of new detections
        new_centroids = {}
        for i, det in enumerate(detections):
            x1, y1, x2, y2 = det['bbox']
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            new_centroids[i] = (cx, cy)
        
        # Match detections to existing tracks
        matched_detections = set()
        
        for track_id, track in list(self.tracks.items()):
            last_centroid = track['centroid']
            
            # Find nearest unmatched detection
            best_dist = float('inf')
            best_idx = -1
            
            for det_idx, centroid in new_centroids.items():
                if det_idx in matched_detections:
                    continue
                
                dist = np.sqrt((last_centroid[0] - centroid[0])**2 + 
                              (last_centroid[1] - centroid[1])**2)
                
                if dist < best_dist and dist < self.max_distance:
                    best_dist = dist
                    best_idx = det_idx
            
            if best_idx != -1:
                # Update existing track
                self.tracks[track_id]['centroid'] = new_centroids[best_idx]
                self.tracks[track_id]['bbox'] = detections[best_idx]['bbox']
                self.tracks[track_id]['age'] += 1
                self.tracks[track_id]['class'] = detections[best_idx]['class']
                self.tracks[track_id]['confidence'] = detections[best_idx]['confidence']
                self.tracks[track_id]['frames_alive'] += 1
                matched_detections.add(best_idx)
            else:
                # Track lost, mark for deletion
                self.tracks[track_id]['age'] -= 1
        
        # Remove dead tracks
        self.tracks = {k: v for k, v in self.tracks.items() if v['age'] > -self.max_age}
        
        # Add new detections as new tracks
        for det_idx, centroid in new_centroids.items():
            if det_idx not in matched_detections:
                self.next_id += 1
                self.tracks[self.next_id] = {
                    'centroid': centroid,
                    'bbox': detections[det_idx]['bbox'],
                    'class': detections[det_idx]['class'],
                    'confidence': detections[det_idx]['confidence'],
                    'age': 0,
                    'frames_alive': 1,
                    'history': [centroid]
                }
        
        return self.tracks
    
    def draw_tracks(self, frame, tracks):
        """Draw track IDs and history on frame"""
        for track_id, track in tracks.items():
            x1, y1, x2, y2 = track['bbox']
            cx, cy = track['centroid']
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            
            # Draw track ID
            label = f"ID:{track_id}"
            cv2.putText(frame, label, (x1, y1 - 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Draw centroid
            cv2.circle(frame, (int(cx), int(cy)), 4, (0, 0, 255), -1)
            
            # Draw history (last 10 positions)
            if len(track['history']) > 1:
                pts = np.array(track['history'][-10:], dtype=np.int32)
                cv2.polylines(frame, [pts], False, (0, 0, 255), 1)
        
        return frame
    
    def reset(self):
        """Reset tracker"""
        self.tracks = {}
        self.next_id = 0