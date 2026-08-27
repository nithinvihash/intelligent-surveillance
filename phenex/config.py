import json
import os
import logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """Load from JSON, return defaults if missing"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file) as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
        
        return self._defaults()
    
    def _defaults(self):
        return {
            "video_source": 0,
            "line_coords": [100, 100, 600, 100],
            "zone_coords": [[200, 200], [600, 200], [600, 400], [200, 400]],
            "detection_confidence": 0.5,
            "tracking_max_distance": 50,
            "api_port": 8000,
            "database_path": "events.db",
            "event_retention_days": 7,
            "log_level": "INFO"
        }
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)