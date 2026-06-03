"""
Real-Time Flight Data Worker
Background scheduler for fetching live flight data from OpenSky Network
Runs every 10 minutes and updates the database with current flight info
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from opensky_api import OpenSkyConnector, format_flight_data
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import models
from live_data_models import (
    LiveFlight, LiveFlightUpdate, LiveFlightStats, APIFetchLog
)


class RealTimeFlightWorker:
    """
    Background worker that fetches live flight data and updates database.
    """
    
    def __init__(self, db_url="sqlite:///instance/database.db", username=None, password=None):
        """
        Initialize worker with database connection and API credentials.
        
        Args:
            db_url (str): SQLAlchemy database URL
            username (str): Optional OpenSky username
            password (str): Optional OpenSky password
        """
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        self.opensky = OpenSkyConnector(username=username, password=password)
        
        # US bounding box (covers continental US)
        self.us_bbox = (25, 50, -130, -70)
        
        print(f"✓ Worker initialized with DB: {db_url}")
    
    def create_tables(self):
        """Create database tables if they don't exist."""
        try:
            from live_data_models import db as db_model
            db_model.metadata.create_all(self.engine)
            print("✓ Database tables created/verified")
        except Exception as e:
            print(f"✗ Error creating tables: {e}")
    
    def fetch_and_store_live_flights(self):
        """
        Main worker function: Fetch live flights and update database.
        """
        session = self.Session()
        start_time = time.time()
        
        try:
            print(f"\n📡 Fetching live flights at {datetime.now(timezone.utc).isoformat()}")
            
            # Fetch from OpenSky API
            flights_df = self.opensky.get_live_flights(bbox=self.us_bbox)
            
            if flights_df.empty:
                print("✗ No flights fetched from API")
                self._log_fetch(session, flights_fetched=0, flights_stored=0, status="ERROR", error="No data returned")
                return
            
            print(f"✓ Fetched {len(flights_df)} flights from API")
            
            # Format data
            flights_df = format_flight_data(flights_df)
            
            # Update database
            stored_count = self._update_live_flights_table(session, flights_df)
            
            # Store update history (every update for 30-day retention)
            history_count = self._store_flight_updates(session, flights_df)
            
            # Calculate and update stats
            self._update_flight_stats(session)
            
            # Log successful fetch
            response_time = int((time.time() - start_time) * 1000)
            self._log_fetch(
                session,
                flights_fetched=len(flights_df),
                flights_stored=stored_count,
                status="SUCCESS",
                response_time_ms=response_time
            )
            
            print(f"✓ Stored {stored_count} flights in database")
            print(f"✓ Recorded {history_count} historical updates")
            print(f"✓ Response time: {response_time}ms")
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error in fetch_and_store: {e}")
            response_time = int((time.time() - start_time) * 1000)
            self._log_fetch(
                session,
                flights_fetched=0,
                flights_stored=0,
                status="ERROR",
                error_message=str(e),
                response_time_ms=response_time
            )
            session.commit()
        
        finally:
            session.close()
    
    def _update_live_flights_table(self, session, flights_df):
        """
        Update LiveFlight table with current flight data.
        Replaces old data with new data for same aircraft.
        """
        count = 0
        
        # Delete old data (older than 1 hour) to keep table clean
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        session.query(LiveFlight).filter(LiveFlight.fetch_time < cutoff_time).delete()
        
        for _, row in flights_df.iterrows():
            try:
                # Check if flight exists
                existing = session.query(LiveFlight).filter_by(icao24=row['icao24']).first()
                
                if existing:
                    # Update existing
                    existing.callsign = row.get('callsign', existing.callsign)
                    existing.latitude = row.get('latitude')
                    existing.longitude = row.get('longitude')
                    existing.altitude = row.get('altitude')
                    existing.geo_altitude = row.get('geo_altitude')
                    existing.velocity = row.get('velocity')
                    existing.heading = row.get('heading')
                    existing.vertical_rate = row.get('vertical_rate')
                    existing.on_ground = row.get('on_ground', False)
                    existing.flight_status = row.get('flight_status', 'IN_FLIGHT')
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new
                    flight = LiveFlight(
                        icao24=row['icao24'],
                        callsign=row.get('callsign'),
                        airline_code=row.get('airline_code'),
                        origin_country=row.get('origin_country'),
                        latitude=row.get('latitude'),
                        longitude=row.get('longitude'),
                        altitude=row.get('altitude'),
                        geo_altitude=row.get('geo_altitude'),
                        velocity=row.get('velocity'),
                        heading=row.get('heading'),
                        vertical_rate=row.get('vertical_rate'),
                        on_ground=row.get('on_ground', False),
                        flight_status=row.get('flight_status', 'IN_FLIGHT'),
                        fetch_time=datetime.now(timezone.utc)
                    )
                    session.add(flight)
                
                count += 1
                
            except Exception as e:
                print(f"✗ Error storing flight {row.get('icao24')}: {e}")
        
        return count
    
    def _store_flight_updates(self, session, flights_df):
        """
        Store flight positions in historical update table for trend analysis.
        """
        count = 0
        
        for _, row in flights_df.iterrows():
            try:
                update = LiveFlightUpdate(
                    icao24=row['icao24'],
                    callsign=row.get('callsign'),
                    airline_code=row.get('airline_code'),
                    latitude=row.get('latitude'),
                    longitude=row.get('longitude'),
                    altitude=row.get('altitude'),
                    velocity=row.get('velocity'),
                    heading=row.get('heading'),
                    on_ground=row.get('on_ground', False),
                    flight_status=row.get('flight_status', 'IN_FLIGHT'),
                    update_time=datetime.now(timezone.utc)
                )
                session.add(update)
                count += 1
                
            except Exception as e:
                print(f"✗ Error storing update for {row.get('icao24')}: {e}")
        
        # Clean old updates (keep only 30 days)
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
        session.query(LiveFlightUpdate).filter(LiveFlightUpdate.update_time < cutoff_time).delete()
        
        return count
    
    def _update_flight_stats(self, session):
        """
        Calculate and update flight statistics from current live data.
        """
        try:
            flights = session.query(LiveFlight).all()
            
            if not flights:
                return
            
            # Group by airline
            airline_groups = {}
            for flight in flights:
                code = flight.airline_code or 'UNKNOWN'
                if code not in airline_groups:
                    airline_groups[code] = []
                airline_groups[code].append(flight)
            
            # Clear old stats (older than 30 days)
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
            session.query(LiveFlightStats).filter(LiveFlightStats.recorded_at < cutoff_time).delete()
            
            # Create new stats for each airline
            for airline_code, airline_flights in airline_groups.items():
                try:
                    total = len(airline_flights)
                    on_ground = sum(1 for f in airline_flights if f.on_ground)
                    in_air = total - on_ground
                    
                    altitudes = [f.altitude for f in airline_flights if f.altitude]
                    velocities = [f.velocity for f in airline_flights if f.velocity]
                    
                    stats = LiveFlightStats(
                        airline_code=airline_code,
                        total_flights=total,
                        flights_on_ground=on_ground,
                        flights_in_air=in_air,
                        avg_altitude=sum(altitudes) / len(altitudes) if altitudes else None,
                        max_altitude=max(altitudes) if altitudes else None,
                        avg_velocity=sum(velocities) / len(velocities) if velocities else None,
                        recorded_at=datetime.now(timezone.utc)
                    )
                    session.add(stats)
                    
                except Exception as e:
                    print(f"✗ Error calculating stats for {airline_code}: {e}")
        
        except Exception as e:
            print(f"✗ Error in _update_flight_stats: {e}")
    
    def _log_fetch(self, session, flights_fetched=0, flights_stored=0, status="SUCCESS", 
                   error_message=None, response_time_ms=None):
        """Log API fetch attempt for monitoring."""
        try:
            log = APIFetchLog(
                api_source='OpenSky',
                status=status,
                flights_fetched=flights_fetched,
                flights_stored=flights_stored,
                error_message=error_message,
                response_time_ms=response_time_ms
            )
            session.add(log)
        except Exception as e:
            print(f"✗ Error logging fetch: {e}")
    
    def cleanup_old_data(self):
        """
        Clean up old data to manage database size.
        Keeps: 30 days of updates, 1 hour of live flights
        """
        session = self.Session()
        try:
            # Clean live flights older than 1 hour
            cutoff_live = datetime.now(timezone.utc) - timedelta(hours=1)
            deleted_live = session.query(LiveFlight).filter(
                LiveFlight.fetch_time < cutoff_live
            ).delete()
            
            # Clean updates older than 30 days
            cutoff_updates = datetime.now(timezone.utc) - timedelta(days=30)
            deleted_updates = session.query(LiveFlightUpdate).filter(
                LiveFlightUpdate.update_time < cutoff_updates
            ).delete()
            
            # Clean stats older than 30 days
            deleted_stats = session.query(LiveFlightStats).filter(
                LiveFlightStats.recorded_at < cutoff_updates
            ).delete()
            
            session.commit()
            
            if deleted_live + deleted_updates + deleted_stats > 0:
                print(f"✓ Cleanup: Removed {deleted_live} live flights, {deleted_updates} updates, {deleted_stats} stats")
        
        except Exception as e:
            session.rollback()
            print(f"✗ Error during cleanup: {e}")
        
        finally:
            session.close()


def run_worker():
    """
    Run worker continuously (for use with process manager like supervisor/systemd)
    """
    # Determine database URL
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, '..', 'instance', 'database.db')
    db_url = f"sqlite:///{db_path}"
    
    worker = RealTimeFlightWorker(db_url=db_url)
    
    # Create tables on first run
    worker.create_tables()
    
    print("🚀 Real-Time Flight Worker started!")
    print(f"📍 Tracking US flights (bbox: {worker.us_bbox})")
    print("⏱️  Update interval: 10 minutes")
    print("Ctrl+C to stop\n")
    
    # Run continuously
    iteration = 0
    try:
        while True:
            iteration += 1
            print(f"\n[Iteration {iteration}] ", end="")
            
            # Fetch and store flights
            worker.fetch_and_store_live_flights()
            
            # Cleanup old data every 10 iterations (every ~100 minutes)
            if iteration % 10 == 0:
                worker.cleanup_old_data()
            
            # Wait 10 minutes
            print("⏳ Waiting 10 minutes until next update...")
            time.sleep(600)  # 10 minutes
    
    except KeyboardInterrupt:
        print("\n\n✓ Worker stopped by user")
    except Exception as e:
        print(f"\n✗ Worker error: {e}")
        raise


if __name__ == "__main__":
    run_worker()
