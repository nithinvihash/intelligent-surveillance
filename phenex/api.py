from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import cv2
import io
import logging
import os
import time
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)

try:
    from .config import Config
except ImportError:
    from config import Config

app = FastAPI()

# CORS for WebSocket
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
try:
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
except:
    pass

# Global state
db = None
event_queue = deque(maxlen=100)
connected_clients = []
current_frame = None
frame_lock = Lock()
pipeline_start_time = time.time()

def init_db(database):
    """Initialize database reference"""
    global db
    db = database

def update_frame(frame):
    """Update current frame for streaming"""
    global current_frame
    with frame_lock:
        current_frame = frame.copy()

def get_current_frame():
    """Get current frame"""
    global current_frame
    with frame_lock:
        return current_frame.copy() if current_frame is not None else None

def encode_frame_to_jpeg(frame):
    """Encode frame to JPEG"""
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return buffer.tobytes()

# MJPEG Streaming
async def generate_mjpeg():
    """Generate MJPEG stream"""
    while True:
        frame = get_current_frame()
        if frame is None:
            await asyncio.sleep(0.033)  # ~30 FPS
            continue

        jpeg_data = encode_frame_to_jpeg(frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(jpeg_data)).encode() + b'\r\n\r\n' +
               jpeg_data + b'\r\n')

        await asyncio.sleep(0.033)  # ~30 FPS

@app.get("/video_feed")
async def video_feed():
    """Stream video as MJPEG"""
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/")
async def root():
    """Serve dashboard"""
    return FileResponse('frontend/index.html')

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
    return {"status": "error", "database": "disconnected"}

@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent events"""
    if not db:
        return {"error": "Database not connected", "events": []}
    
    events = db.get_recent_events(limit)
    return {"events": events, "total": len(events)}

@app.get("/api/events/type/{event_type}")
async def get_events_by_type(event_type: str, limit: int = 50):
    """Get events by type"""
    if not db:
        return {"error": "Database not connected", "events": []}
    
    events = db.get_events_by_type(event_type, limit)
    return {"events": events, "event_type": event_type}

@app.get("/api/stats")
async def get_stats():
    """Get statistics"""
    if not db:
        return {"error": "Database not connected"}
    
    stats = db.get_stats()
    return stats
@app.get("/api/metrics")
async def get_metrics():
    """Get real-time performance metrics"""
    if not db:
        return {"error": "Database not connected"}
    
    return {
        "uptime_seconds": time.time() - pipeline_start_time,
        "database_size_mb": os.path.getsize('events.db') / (1024 * 1024) if os.path.exists('events.db') else 0,
        "total_events": db.get_stats()['total_events'],
        "memory_status": "ok"
    }

@app.post("/api/config/reload")
async def reload_config():
    """Reload configuration from file"""
    try:
        global config
        config = Config('config.json')
        return {"status": "config reloaded", "config": config.config}
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/api/events/export")
async def export_events(limit: int = 1000, format: str = "json"):
    """Export events as JSON or CSV"""
    if not db:
        return {"error": "Database not connected"}
    
    events = db.get_recent_events(limit)
    
    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        
        if not events:
            return {"error": "No events to export"}
        
        writer = csv.DictWriter(output, fieldnames=events[0].keys())
        writer.writeheader()
        writer.writerows(events)
        
        return {"csv": output.getvalue()}
    
    return {"events": events, "count": len(events)}

@app.get("/api/health/detailed")
async def health_detailed():
    """Detailed health check"""
    if not db:
        return {"error": "Database not connected", "status": "unhealthy"}
    
    stats = db.get_stats()
    
    return {
        "status": "healthy",
        "database": "connected",
        "api": "running",
        "events_stored": stats['total_events'],
        "objects_tracked": stats['total_objects'],
        "last_updated": time.time()
    }
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time events"""
    await websocket.accept()
    connected_clients.append(websocket)
    
    print(f"WebSocket client connected. Total: {len(connected_clients)}")
    
    try:
        while True:
            await asyncio.sleep(5)
            await websocket.send_json({
                "type": "heartbeat",
                "clients": len(connected_clients)
            })
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print(f"WebSocket client disconnected. Total: {len(connected_clients)}")

async def broadcast_event(event):
    """Broadcast event to all connected clients"""
    event_queue.append(event)
    
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json({
                "type": "event",
                "data": event
            })
        except Exception as e:
            disconnected.append(client)
    
    for client in disconnected:
        if client in connected_clients:
            connected_clients.remove(client)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
@app.get("/video_feed")
async def video_feed():
    """Stream video as MJPEG with error handling"""
    try:
        return StreamingResponse(
            generate_mjpeg(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        logger.error(f"Video stream error: {e}")
        return {"error": "Video stream unavailable"}
    from fastapi import HTTPException

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "error": "Internal server error",
        "details": str(exc)
    }