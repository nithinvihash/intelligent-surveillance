from asyncio.log import logger
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

    def create_anpr_table(self):
        """Create ANPR results table"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS anpr_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            plate_text TEXT NOT NULL,
            ocr_confidence REAL,
            plate_confidence REAL,
            combined_confidence REAL,
            vehicle_class TEXT,
            timestamp REAL,
            state TEXT,
            district TEXT,
            series TEXT,
            number TEXT,
            camera_id TEXT,
            FOREIGN KEY(track_id) REFERENCES events(track_id)
        )
    ''')
        
        # Create indexes
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_anpr_plate ON anpr_results(plate_text)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_anpr_track ON anpr_results(track_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_anpr_timestamp ON anpr_results(timestamp DESC)')
        
        self.connection.commit()
        logger.info("✓ ANPR table created")

    def store_anpr_result(self, anpr_data):
        """Store ANPR result"""
        try:
            self.cursor.execute('''
                INSERT INTO anpr_results 
                (track_id, plate_text, ocr_confidence, plate_confidence, combined_confidence, 
                 vehicle_class, timestamp, state, district, series, number, camera_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                anpr_data['track_id'],
                anpr_data['plate_text'],
                anpr_data['ocr_confidence'],
                anpr_data['plate_detection_confidence'],
                anpr_data['combined_confidence'],
                anpr_data['class'],
                anpr_data['timestamp'],
                anpr_data['components'].get('state') if anpr_data.get('components') else None,
                anpr_data['components'].get('district') if anpr_data.get('components') else None,
                anpr_data['components'].get('series') if anpr_data.get('components') else None,
                anpr_data['components'].get('number') if anpr_data.get('components') else None,
                'CAM-01'  # Default camera ID
            ))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error storing ANPR result: {e}")

def get_anpr_results(self, limit=50):
    """Get recent ANPR results"""
    self.cursor.execute('SELECT * FROM anpr_results ORDER BY timestamp DESC LIMIT ?', (limit,))
    columns = [desc[0] for desc in self.cursor.description]
    return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

def search_by_plate(self, plate_text):
    """Search ANPR results by plate text"""
    self.cursor.execute('SELECT * FROM anpr_results WHERE plate_text = ?', (plate_text,))
    columns = [desc[0] for desc in self.cursor.description]
    return [dict(zip(columns, row)) for row in self.cursor.fetchall()]