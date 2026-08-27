import sqlite3
import json
from datetime import datetime

class EventDatabase:
    def __init__(self, db_path='events.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.setup_schema()
    
    def setup_schema(self):
        """Create tables if they don't exist"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                track_id INTEGER NOT NULL,
                class TEXT NOT NULL,
                confidence REAL,
                risk_score REAL,
                direction TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY,
                class TEXT,
                first_seen REAL,
                last_seen REAL,
                frames_alive INTEGER,
                avg_confidence REAL
            )
        """)
        
        self.conn.commit()
    
    def store_event(self, event):
        """Store single event to database"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO events 
            (timestamp, event_type, track_id, class, confidence, risk_score, direction, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event['timestamp'],
            event['type'],
            event['track_id'],
            event['class'],
            event['confidence'],
            event['risk_score'],
            event.get('direction', ''),
            json.dumps(event)
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_recent_events(self, limit=50):
        """Get last N events"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, event_type, track_id, class, confidence, risk_score
            FROM events
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row[0],
                'timestamp': row[1],
                'event_type': row[2],
                'track_id': row[3],
                'class': row[4],
                'confidence': row[5],
                'risk_score': row[6]
            })
        
        return events
    
    def get_events_by_type(self, event_type, limit=50):
        """Get events of specific type"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, event_type, track_id, class, confidence, risk_score
            FROM events
            WHERE event_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (event_type, limit))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row[0],
                'timestamp': row[1],
                'event_type': row[2],
                'track_id': row[3],
                'class': row[4],
                'confidence': row[5],
                'risk_score': row[6]
            })
        
        return events
    
    def get_stats(self):
        """Get database statistics"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM events")
        total_events = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT track_id) FROM events")
        total_objects = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'line_crossed'")
        line_crossings = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'zone_entry'")
        zone_entries = cursor.fetchone()[0]
        
        return {
            'total_events': total_events,
            'total_objects': total_objects,
            'line_crossings': line_crossings,
            'zone_entries': zone_entries
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()

    def cleanup_old_events(self, days=7):
        """Delete events older than N days"""
        import time
        timestamp_limit = time.time() - (days * 86400)
        cursor = self.conn.cursor()

        cursor.execute("DELETE FROM events WHERE timestamp < ?", (timestamp_limit,))
        self.conn.commit()

        return cursor.rowcount

    def add_indexes(self):
        """Add database indexes for faster queries"""
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON events(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_track_id
                ON events(track_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type
                ON events(event_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_risk_score
                ON events(risk_score DESC)
            """)

            self.conn.commit()
            print("✓ Database indexes created")
        except Exception as e:
            print(f"Index creation skipped: {e}")

    def get_database_size(self):
        """Get database file size in MB"""
        import os
        if os.path.exists(self.db_path):
            return os.path.getsize(self.db_path) / (1024 * 1024)
        return 0