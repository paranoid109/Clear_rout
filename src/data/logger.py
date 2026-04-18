import sqlite3
import os
from datetime import datetime

class AQILogger:
    """
    Handles persistence of air quality readings to a local SQLite database.
    Used for historical logging and training the prediction engine.
    """
    def __init__(self, db_path="data/air_quality_history.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    city TEXT DEFAULT 'bengaluru',
                    fused_aqi REAL,
                    api_aqi REAL,
                    sensor_aqi REAL
                )
            """)
            conn.commit()

    def log_reading(self, city, fused_aqi, api_aqi, sensor_aqi):
        """Logs a new fusion result to the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO measurements (city, fused_aqi, api_aqi, sensor_aqi)
                VALUES (?, ?, ?, ?)
            """, (city, fused_aqi, api_aqi, sensor_aqi))
            conn.commit()

    def get_recent_history(self, city='bengaluru', limit=100):
        """Fetches the most recent readings."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, fused_aqi FROM measurements
                WHERE city = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (city, limit))
            return cursor.fetchall()

    def prune_old_records(self, days=90):
        """
        Deletes records older than the specified number of days to save disk space.
        SOP Requirement 8: Prune records older than 90 days.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Calculate the threshold timestamp
                cursor = conn.execute("DELETE FROM measurements WHERE timestamp < datetime('now', ? || ' days')", (f"-{days}",))
                deleted_rows = cursor.rowcount
                if deleted_rows > 0:
                    print(f"Maintenance: Pruned {deleted_rows} records older than {days} days from database.")
                else:
                    print("Maintenance: No old records to prune.")
                conn.commit()
        except Exception as e:
            print(f"Maintenance Warning: Failed to prune database: {e}")

if __name__ == "__main__":
    logger = AQILogger()
    logger.log_reading('bengaluru', 55.0, 50.0, 60.0)
    print("Logged test reading.")
    print(f"Recent history: {logger.get_recent_history('bengaluru', 5)}")
