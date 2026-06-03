"""
Live Flight Data Models
Database models for real-time flight tracking
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class LiveFlight(db.Model):
    """
    Real-time flight data from OpenSky Network.
    Updated every 5-10 minutes, keeps only current day data.
    """
    __tablename__ = 'live_flights'
    
    id = db.Column(db.Integer, primary_key=True)
    icao24 = db.Column(db.String(6), unique=True, nullable=False)  # Aircraft unique ID
    callsign = db.Column(db.String(10), nullable=False)  # Flight number (e.g., 'AAL101')
    airline_code = db.Column(db.String(3), nullable=True)  # Extracted airline code
    origin_country = db.Column(db.String(50), nullable=True)
    
    # Position data
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    altitude = db.Column(db.Float, nullable=True)  # In meters
    geo_altitude = db.Column(db.Float, nullable=True)
    
    # Speed and direction
    velocity = db.Column(db.Float, nullable=True)  # m/s
    heading = db.Column(db.Float, nullable=True)  # degrees (0-360)
    vertical_rate = db.Column(db.Float, nullable=True)  # m/s
    
    # Status
    on_ground = db.Column(db.Boolean, default=False)
    flight_status = db.Column(db.String(20), default='IN_FLIGHT')  # IN_FLIGHT, ON_GROUND, LANDED
    
    # Timestamps
    time_position = db.Column(db.DateTime, nullable=True)
    last_contact = db.Column(db.DateTime, nullable=True)
    fetch_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<LiveFlight {self.callsign} - {self.flight_status}>"


class LiveFlightUpdate(db.Model):
    """
    Historical tracking of flight updates (keeps last 30 days).
    Used for trend analysis and delay patterns.
    """
    __tablename__ = 'live_flight_updates'
    
    id = db.Column(db.Integer, primary_key=True)
    icao24 = db.Column(db.String(6), nullable=False)
    callsign = db.Column(db.String(10), nullable=False)
    airline_code = db.Column(db.String(3), nullable=True)
    
    # Last known position
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    altitude = db.Column(db.Float, nullable=True)
    velocity = db.Column(db.Float, nullable=True)
    heading = db.Column(db.Float, nullable=True)
    
    # Status at this update
    on_ground = db.Column(db.Boolean, default=False)
    flight_status = db.Column(db.String(20))
    
    # Timestamp of this update
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    __table_args__ = (
        db.Index('idx_icao24_time', 'icao24', 'update_time'),
        db.Index('idx_callsign_time', 'callsign', 'update_time'),
    )
    
    def __repr__(self):
        return f"<LiveFlightUpdate {self.callsign} @ {self.update_time}>"


class LiveFlightStats(db.Model):
    """
    Aggregated statistics for live flights (updated every 10 minutes).
    Used for dashboard summaries and real-time metrics.
    """
    __tablename__ = 'live_flight_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    airline_code = db.Column(db.String(3), nullable=True, index=True)
    
    # Count statistics
    total_flights = db.Column(db.Integer, default=0)
    flights_on_ground = db.Column(db.Integer, default=0)
    flights_in_air = db.Column(db.Integer, default=0)
    
    # Delay metrics
    avg_altitude = db.Column(db.Float, nullable=True)
    max_altitude = db.Column(db.Float, nullable=True)
    avg_velocity = db.Column(db.Float, nullable=True)
    
    # Origin/Destination summary
    top_origin_country = db.Column(db.String(50), nullable=True)
    unique_origins = db.Column(db.Integer, default=0)
    
    # Timestamp
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    def __repr__(self):
        return f"<LiveFlightStats {self.airline_code} @ {self.recorded_at}>"


class APIFetchLog(db.Model):
    """
    Log of API fetch attempts for monitoring and debugging.
    Keeps track of when data was fetched and if there were errors.
    """
    __tablename__ = 'api_fetch_log'
    
    id = db.Column(db.Integer, primary_key=True)
    api_source = db.Column(db.String(50), default='OpenSky')  # API name
    
    # Fetch details
    status = db.Column(db.String(20), default='SUCCESS')  # SUCCESS, ERROR, TIMEOUT
    flights_fetched = db.Column(db.Integer, default=0)
    flights_stored = db.Column(db.Integer, default=0)
    
    # Error tracking
    error_message = db.Column(db.Text, nullable=True)
    response_time_ms = db.Column(db.Integer, nullable=True)
    
    # Timestamp
    fetch_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    def __repr__(self):
        return f"<APIFetchLog {self.api_source} - {self.status} ({self.flights_fetched} flights)>"
