from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import asyncio
import cv2
import logging
import os
import time

logger = logging.getLogger(__name__)

try:
    from .config import Config
except ImportError:
    from config import Config

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
db = None
current_frame = None
connected_clients = []
pipeline_start_time = time.time()

def init_db(database):
    """Initialize database reference"""
    global db
    db = database

def update_frame(frame):
    """Update current frame for streaming"""
    global current_frame
    try:
        current_frame = frame.copy()
    except:
        pass

def get_current_frame():
    """Get current frame"""
    global current_frame
    if current_frame is None:
        return None
    try:
        return current_frame.copy()
    except:
        return None

# ============= MJPEG STREAMING =============
async def generate_mjpeg():
    """Generate MJPEG stream"""
    while True:
        frame = get_current_frame()
        if frame is None:
            await asyncio.sleep(0.033)
            continue

        try:
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            jpeg_data = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(jpeg_data)).encode() + b'\r\n\r\n' +
                   jpeg_data + b'\r\n')
        except Exception as e:
            logger.error(f"JPEG encoding error: {e}")
            await asyncio.sleep(0.033)
            continue

        await asyncio.sleep(0.033)

@app.get("/video_feed")
async def video_feed():
    """Stream video as MJPEG"""
    try:
        return StreamingResponse(
            generate_mjpeg(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        logger.error(f"Video stream error: {e}")
        return {"error": "Video stream unavailable"}

# ============= STATIC FILES & FRONTEND =============
# Get paths
phenex_dir = Path(__file__).parent
project_root = phenex_dir.parent
frontend_dir = project_root / "frontend"

print()
print("=" * 60)
print("📁 PATH CONFIGURATION")
print("=" * 60)
print(f"Project root: {project_root}")
print(f"Frontend dir: {frontend_dir}")
print(f"Frontend exists: {frontend_dir.exists()}")

# Mount frontend files FIRST (before /api routes)
if frontend_dir.exists():
    print(f"✓ Mounting frontend from: {frontend_dir}")
    try:
        # Mount as static files with HTML support
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
        print(f"✓ Frontend mounted successfully")
    except Exception as e:
        print(f"❌ Error mounting frontend: {e}")
else:
    print(f"❌ Frontend folder not found: {frontend_dir}")

print("=" * 60)
print()

# ============= API ENDPOINTS =============

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    if db:
        stats = db.get_stats()
        return {
            "status": "ok",
            "database": "connected",
            "stats": stats
        }
    return {"status": "ok", "database": "not_initialized"}

@app.get("/api/health/detailed")
async def health_detailed():
    """Detailed health check"""
    if not db:
        return {"status": "ok", "database": "not_initialized"}
    
    stats = db.get_stats()
    return {
        "status": "healthy",
        "database": "connected",
        "api": "running",
        "events_stored": stats.get('total_events', 0),
        "objects_tracked": stats.get('total_objects', 0),
        "timestamp": time.time()
    }

@app.get("/api/stats")
async def get_stats():
    """Get statistics"""
    if not db:
        return {
            "total_events": 0,
            "total_objects": 0,
            "line_crossings": 0,
            "zone_entries": 0,
            "fps": 0
        }
    
    stats = db.get_stats()
    return stats

@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent events"""
    if not db:
        return {"events": [], "total": 0}
    
    try:
        events = db.get_recent_events(limit)
        return {"events": events, "total": len(events)}
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return {"events": [], "total": 0, "error": str(e)}

@app.get("/api/events/type/{event_type}")
async def get_events_by_type(event_type: str, limit: int = 50):
    """Get events by type"""
    if not db:
        return {"events": [], "event_type": event_type, "total": 0}
    
    try:
        events = db.get_events_by_type(event_type, limit)
        return {"events": events, "event_type": event_type, "total": len(events)}
    except Exception as e:
        logger.error(f"Error getting events by type: {e}")
        return {"events": [], "event_type": event_type, "total": 0}

@app.get("/api/events/export")
async def export_events(limit: int = 1000):
    """Export events as JSON"""
    if not db:
        return {"events": [], "count": 0}
    
    try:
        events = db.get_recent_events(limit)
        return {"events": events, "count": len(events)}
    except Exception as e:
        logger.error(f"Error exporting events: {e}")
        return {"events": [], "count": 0, "error": str(e)}

@app.post("/api/events/clear")
async def clear_events():
    """Clear all events"""
    if not db:
        return {"status": "error", "message": "Database not initialized"}
    
    try:
        db.cursor.execute("DELETE FROM events")
        db.connection.commit()
        return {"status": "success", "message": "All events cleared"}
    except Exception as e:
        logger.error(f"Error clearing events: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/metrics")
async def get_metrics():
    """Get performance metrics"""
    if not db:
        return {"uptime_seconds": 0, "database_size_mb": 0}
    
    try:
        uptime = time.time() - pipeline_start_time
        db_size = os.path.getsize('events.db') / (1024 * 1024) if os.path.exists('events.db') else 0
        return {
            "uptime_seconds": uptime,
            "database_size_mb": db_size,
            "total_events": db.get_stats().get('total_events', 0),
            "memory_status": "ok"
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"error": str(e)}

# ============= ANPR ENDPOINTS =============

@app.get("/api/anpr")
async def get_anpr_results(limit: int = 50):
    """Get recent ANPR results"""
    if not db:
        return {"status": "success", "count": 0, "data": []}
    
    try:
        try:
            results = db.cursor.execute('SELECT * FROM anpr_results ORDER BY timestamp DESC LIMIT ?', (limit,)).fetchall()
            return {"status": "success", "count": len(results) if results else 0, "data": results if results else []}
        except:
            return {"status": "success", "count": 0, "data": [], "message": "ANPR table not created yet"}
    except Exception as e:
        logger.error(f"ANPR API error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/anpr/vehicle/{track_id}")
async def get_vehicle_plate(track_id: int):
    """Get ANPR results for specific vehicle"""
    if not db:
        return {"status": "success", "track_id": track_id, "data": []}
    
    try:
        results = db.cursor.execute('SELECT * FROM anpr_results WHERE track_id = ?', (track_id,)).fetchall()
        return {"status": "success", "track_id": track_id, "data": results if results else []}
    except Exception as e:
        logger.error(f"Vehicle plate lookup error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/anpr/search/{plate_text}")
async def search_plate(plate_text: str):
    """Search by plate text"""
    if not db:
        return {"status": "success", "plate": plate_text, "count": 0, "data": []}
    
    try:
        results = db.cursor.execute('SELECT * FROM anpr_results WHERE plate_text = ?', (plate_text,)).fetchall()
        return {"status": "success", "plate": plate_text, "count": len(results) if results else 0, "data": results if results else []}
    except Exception as e:
        logger.error(f"Plate search error: {e}")
        return {"status": "error", "message": str(e)}

# ============= WEBSOCKET =============

@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time events"""
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"✓ WebSocket client connected. Total: {len(connected_clients)}")
    
    try:
        while True:
            await asyncio.sleep(5)
            try:
                await websocket.send_json({
                    "type": "heartbeat",
                    "clients": len(connected_clients),
                    "timestamp": time.time()
                })
            except:
                break
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(f"✓ WebSocket client disconnected. Total: {len(connected_clients)}")

async def broadcast_event(event):
    """Broadcast event to all connected clients"""
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json({"type": "event", "data": event})
        except Exception as e:
            logger.debug(f"Client send error: {e}")
            disconnected.append(client)
    
    for client in disconnected:
        if client in connected_clients:
            connected_clients.remove(client)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)