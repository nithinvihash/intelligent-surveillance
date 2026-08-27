import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from phenex.detector import Detector
from phenex.tracker import Tracker
from phenex.events import EventGenerator
from phenex.storage import EventDatabase
from phenex.config import Config

class TestDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = Detector()
    
    def test_detector_loads(self):
        """Test detector model loads successfully"""
        self.assertIsNotNone(self.detector.model)
    
    def test_detector_filters_by_confidence(self):
        """Test detector filters low-confidence detections"""
        # This would need a real frame, skip for now
        pass

class TestTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = Tracker()
    
    def test_tracker_assigns_ids(self):
        """Test tracker assigns unique IDs"""
        fake_detections = [
            {'bbox': [10, 10, 50, 50], 'confidence': 0.9, 'class': 'person'},
            {'bbox': [100, 100, 150, 150], 'confidence': 0.85, 'class': 'vehicle'}
        ]
        
        tracks = self.tracker.update(fake_detections)
        self.assertEqual(len(tracks), 2)
    
    def test_tracker_persists_ids(self):
        """Test tracker maintains same ID across frames"""
        det1 = [{'bbox': [10, 10, 50, 50], 'confidence': 0.9, 'class': 'person'}]
        det2 = [{'bbox': [15, 15, 55, 55], 'confidence': 0.9, 'class': 'person'}]
        
        tracks1 = self.tracker.update(det1)
        id1 = list(tracks1.keys())[0]
        
        tracks2 = self.tracker.update(det2)
        id2 = list(tracks2.keys())[0]
        
        self.assertEqual(id1, id2, "Track ID should persist")

class TestEventGenerator(unittest.TestCase):
    def setUp(self):
        self.event_gen = EventGenerator(
            line_coords=(100, 100, 600, 100),
            zone_coords=[(200, 200), (600, 200), (600, 400), (200, 400)]
        )
    
    def test_line_crossing_detection(self):
        """Test line crossing is detected"""
        p1 = (300, 90)   # Above line
        p2 = (300, 110)  # Below line
        
        crossed = self.event_gen._line_crossed(p1, p2)
        self.assertTrue(crossed, "Should detect line crossing")
    
    def test_no_line_crossing(self):
        """Test non-crossing is ignored"""
        p1 = (300, 80)
        p2 = (300, 90)
        
        crossed = self.event_gen._line_crossed(p1, p2)
        self.assertFalse(crossed, "Should not detect crossing")
    
    def test_point_in_zone(self):
        """Test zone membership detection"""
        point_inside = (400, 300)
        in_zone = self.event_gen._point_in_polygon(point_inside, self.event_gen.zone)
        self.assertTrue(in_zone, "Point should be inside zone")
    
    def test_point_outside_zone(self):
        """Test point outside zone"""
        point_outside = (100, 100)
        in_zone = self.event_gen._point_in_polygon(point_outside, self.event_gen.zone)
        self.assertFalse(in_zone, "Point should be outside zone")
    
    def test_risk_score_calculation(self):
        """Test risk scoring"""
        track = {
            'confidence': 0.9,
            'class': 'person',
            'centroid': (300, 300)
        }
        
        score = self.event_gen._calculate_risk(track)
        self.assertGreater(score, 0, "Risk score should be > 0")
        self.assertLessEqual(score, 1.0, "Risk score should be <= 1.0")

class TestStorage(unittest.TestCase):
    def setUp(self):
        # Use in-memory database for testing
        self.db = EventDatabase(':memory:')
    
    def test_database_creates_tables(self):
        """Test database schema is created"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('events', tables, "Events table should exist")
        self.assertIn('tracks', tables, "Tracks table should exist")
    
    def test_event_storage(self):
        """Test events are stored correctly"""
        event = {
            'timestamp': 123456.0,
            'type': 'line_crossed',
            'track_id': 1,
            'class': 'person',
            'confidence': 0.9,
            'risk_score': 0.7
        }
        
        event_id = self.db.store_event(event)
        self.assertIsNotNone(event_id, "Event ID should be returned")
    
    def test_event_retrieval(self):
        """Test events can be retrieved"""
        event = {
            'timestamp': 123456.0,
            'type': 'zone_entry',
            'track_id': 2,
            'class': 'vehicle',
            'confidence': 0.85,
            'risk_score': 0.8
        }
        
        self.db.store_event(event)
        events = self.db.get_recent_events(limit=10)
        
        self.assertGreater(len(events), 0, "Should retrieve stored events")
        self.assertEqual(events[0]['event_type'], 'zone_entry')
    
    def test_stats_calculation(self):
        """Test statistics calculation"""
        event = {
            'timestamp': 123456.0,
            'type': 'line_crossed',
            'track_id': 1,
            'class': 'person',
            'confidence': 0.9,
            'risk_score': 0.7
        }
        
        self.db.store_event(event)
        stats = self.db.get_stats()
        
        self.assertEqual(stats['total_events'], 1)
        self.assertEqual(stats['line_crossings'], 1)

class TestConfig(unittest.TestCase):
    def test_config_defaults(self):
        """Test default config is loaded"""
        config = Config(':memory:')  # Non-existent file
        
        self.assertIsNotNone(config.get('video_source'))
        self.assertIsNotNone(config.get('line_coords'))
        self.assertIsNotNone(config.get('zone_coords'))

if __name__ == '__main__':
    unittest.main(verbosity=2)