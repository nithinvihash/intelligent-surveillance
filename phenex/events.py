import time
import importlib

try:
    np = importlib.import_module("numpy")
except ImportError:
    np = None

try:
    cv2 = importlib.import_module("cv2")
except ImportError:
    cv2 = None

class EventGenerator:
    def __init__(self, line_coords=None, zone_coords=None):
        """
        line_coords: (x1, y1, x2, y2) - define a line for crossing detection
        zone_coords: list of (x, y) points - define polygon zone for entry/exit
        """
        # Default geometry; can be overridden by caller-provided coordinates.
        self.line = line_coords if line_coords is not None else (100, 100, 600, 100)
        self.zone = zone_coords if zone_coords is not None else [
            (200, 200), (600, 200), (600, 400), (200, 400)
        ]

        self.crossed_ids = {}  # {track_id: last_crossing_time}
        self.zone_ids = {}     # {track_id: currently_in_zone}
    
    def generate_events(self, tracks):
        """Generate events from tracks"""
        events = []
        
        # Check line crossings
        line_events = self._check_line_crossings(tracks)
        events.extend(line_events)
        
        # Check zone entries/exits
        zone_events = self._check_zone_events(tracks)
        events.extend(zone_events)
        
        return events
    
    def _check_line_crossings(self, tracks):
        """Detect if any track crossed the line"""
        events = []
        current_time = time.time()
        
        for track_id, track in tracks.items():
            if len(track['history']) < 2:
                continue
            
            # Get previous and current position
            prev_pos = track['history'][-2]
            curr_pos = track['history'][-1]
            
            # Check if crossed line
            if self._line_crossed(prev_pos, curr_pos):
                # Avoid duplicate events (5 second cooldown)
                if track_id not in self.crossed_ids or \
                   (current_time - self.crossed_ids[track_id]) > 5:
                    
                    direction = self._get_direction(prev_pos, curr_pos)
                    
                    events.append({
                        'type': 'line_crossed',
                        'track_id': track_id,
                        'timestamp': current_time,
                        'confidence': track['confidence'],
                        'class': track['class'],
                        'direction': direction,
                        'risk_score': self._calculate_risk(track)
                    })
                    
                    self.crossed_ids[track_id] = current_time
        
        return events
    
    def _check_zone_events(self, tracks):
        """Detect zone entry and exit"""
        events = []
        current_time = time.time()
        
        for track_id, track in tracks.items():
            cx, cy = track['centroid']
            
            # Check if currently in zone
            in_zone = self._point_in_polygon((cx, cy), self.zone)
            was_in_zone = self.zone_ids.get(track_id, False)
            
            # Entry event
            if in_zone and not was_in_zone:
                events.append({
                    'type': 'zone_entry',
                    'track_id': track_id,
                    'timestamp': current_time,
                    'confidence': track['confidence'],
                    'class': track['class'],
                    'risk_score': self._calculate_risk(track)
                })
            
            # Exit event
            if not in_zone and was_in_zone:
                events.append({
                    'type': 'zone_exit',
                    'track_id': track_id,
                    'timestamp': current_time,
                    'confidence': track['confidence'],
                    'class': track['class'],
                    'risk_score': self._calculate_risk(track)
                })
            
            self.zone_ids[track_id] = in_zone
        
        return events
    
    def _line_crossed(self, p1, p2):
        """Check if line segment p1-p2 crosses the defined line"""
        x1, y1, x2, y2 = self.line

        def ccw(A, B, C):
            """Check if points A, B, C are in counter-clockwise order"""
            return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
        line_p1 = (x1, y1)
        line_p2 = (x2, y2)

        return ccw(p1, line_p1, line_p2) != ccw(p2, line_p1, line_p2) and \
               ccw(p1, p2, line_p1) != ccw(p1, p2, line_p2)
        
      
    def _get_direction(self, p1, p2):
        """Determine crossing direction"""
        x1, y1 = p1
        x2, y2 = p2
        
        if x2 > x1:
            return "left_to_right"
        else:
            return "right_to_left"
    
    def _point_in_polygon(self, point, polygon):
        """Ray casting algorithm for point in polygon"""
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _calculate_risk(self, track):
        """Calculate risk score (0.0 to 1.0)"""
        score = 0.0
        
        # Confidence-based (0.0 to 0.5)
        score += track['confidence'] * 0.5
        
        # Object type (0.0 to 0.2)
        if track['class'] == 'person':
            score += 0.1
        elif track['class'] in ['car', 'truck', 'bus']:
            score += 0.2
        
        return min(score, 1.0)
    
    def draw_zones_and_lines(self, frame):
        """Draw zones and lines on frame for visualization"""
        if cv2 is None:
            raise RuntimeError(
                "OpenCV is required for drawing zones and lines. "
                "Install it with 'pip install opencv-python'."
            )
        if np is None:
            raise RuntimeError(
                "NumPy is required for drawing zones and lines. "
                "Install it with 'pip install numpy'."
            )

        # Draw line
        x1, y1, x2, y2 = self.line
        cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        
        # Draw zone
        pts = np.array(self.zone, dtype=np.int32)
        cv2.polylines(frame, [pts], True, (255, 0, 0), 2)
        
        return frame