# PheNex Backend Documentation

## Architecture

RTSP Camera
↓
FFmpeg Decoder (OpenCV)
↓
YOLOv8n Detection
↓
ByteTrack Tracking
↓
Event Generator (Line Crossing, Zone Entry)
↓
SQLite Storage
↓
FastAPI WebSocket Broadcast
↓
Dashboard


## Files

- **detector.py** - YOLOv8n inference wrapper
- **tracker.py** - Centroid-based multi-object tracking
- **events.py** - Event generation logic (line crossing, zone detection)
- **storage.py** - SQLite database operations
- **api.py** - FastAPI REST + WebSocket endpoints
- **config.py** - Configuration management
- **main.py** - Main orchestration loop

## API Endpoints

### Health & Metrics
- `GET /api/health` - Basic health check
- `GET /api/health/detailed` - Detailed system status
- `GET /api/metrics` - Performance metrics
- `GET /api/stats` - Event statistics

### Events
- `GET /api/events?limit=50` - Get recent events
- `GET /api/events/type/{type}?limit=50` - Get events by type
- `GET /api/events/export?format=json` - Export events (JSON or CSV)

### Configuration
- `POST /api/config/reload` - Reload config from file

### WebSocket
- `WS /ws` - Real-time event streaming

## Configuration (config.json)

```json
{
  "video_source": 0,  // 0 = webcam, "path/to/video.mp4" = file
  "line_coords": [100, 100, 600, 100],  // x1, y1, x2, y2
  "zone_coords": [[200, 200], [600, 200], [600, 400], [200, 400]],  // polygon
  "detection_confidence": 0.5,
  "tracking_max_distance": 50,
  "api_port": 8000,
  "database_path": "events.db",
  "event_retention_days": 7
}
```

## Running

```bash
# Activate venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run pipeline
python phenex/main.py

# Access dashboard
http://localhost:8000
```

## Features

✅ Real-time person & vehicle detection (YOLOv8n)
✅ Multi-object tracking (Centroid-based)
✅ Line crossing detection
✅ Restricted zone entry/exit
✅ Risk scoring & alert classification
✅ SQLite persistent storage
✅ Automatic camera reconnection
✅ WebSocket real-time events
✅ Event export (JSON/CSV)
✅ Performance metrics

## Performance

- Detection: ~8-10ms per frame
- Tracking: ~2-3ms per frame
- Events: ~1-2ms per frame
- **Total: 12-16ms → ~15 FPS on CPU**

## Error Handling

- Camera disconnect → Auto-reconnect (exponential backoff)
- Database locked → Retry with logging
- API errors → Global exception handler
- Frame processing errors → Log and continue

## Logging

All logs written to `pipeline.log`:

2024-01-15 14:30:00 - root - INFO - Pipeline started
2024-01-15 14:30:05 - root - INFO - ✓ Camera connected
2024-01-15 14:30:10 - root - INFO - Event: line_crossed - Track 1 (Risk: 0.56)


## Database Schema

### events table
- id (PRIMARY KEY)
- timestamp (REAL)
- event_type (TEXT)
- track_id (INTEGER)
- class (TEXT)
- confidence (REAL)
- risk_score (REAL)
- direction (TEXT)
- metadata (TEXT JSON)

### tracks table
- id (PRIMARY KEY)
- class (TEXT)
- first_seen (REAL)
- last_seen (REAL)
- frames_alive (INTEGER)
- avg_confidence (REAL)

Indexes on: timestamp, track_id, event_type, risk_score

## Testing

```bash
# Run unit tests
python -m pytest tests/test_backend.py -v

# Or with unittest
python -m unittest tests.test_backend -v
```

## Future Enhancements

- [ ] Multi-camera support (thread pool)
- [ ] ANPR (license plate reading)
- [ ] Loitering detection
- [ ] Night mode detection
- [ ] PostgreSQL migration
- [ ] Redis caching
- [ ] Kubernetes deployment