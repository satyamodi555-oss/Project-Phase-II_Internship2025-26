"""
OpenSky Network API Integration
Fetches real-time flight data from OpenSky Network API
"""

import requests
import pandas as pd
from datetime import datetime, timezone
import json

class OpenSkyConnector:
    """
    Connects to OpenSky Network API and retrieves live flight data.
    Free tier: ~400 requests/hour, data refresh ~5 minutes
    """
    
    BASE_URL = "https://opensky-network.org/api"
    
    def __init__(self, username=None, password=None):
        """
        Initialize OpenSky connector.
        
        Args:
            username (str): Optional OpenSky username for authenticated requests
            password (str): Optional OpenSky password for authenticated requests
        """
        self.username = username
        self.password = password
        self.auth = (username, password) if username and password else None
        self.timeout = 30
        
    def get_live_flights(self, bbox=None, callsign=None):
        """
        Fetch live flight states from OpenSky Network.
        
        Args:
            bbox (tuple): Bounding box (min_lat, max_lat, min_lon, max_lon) 
                         for US coverage: (25, 50, -130, -70)
            callsign (str): Specific flight callsign to track
            
        Returns:
            pd.DataFrame: Flight data with columns: icao24, callsign, origin_country, 
                         time_position, last_contact, longitude, latitude, altitude, 
                         on_ground, velocity, heading, vertical_rate, sensors, baro_altitude
        """
        try:
            url = f"{self.BASE_URL}/states/all"
            
            params = {}
            if bbox:
                lamin, lamax, lomin, lomax = bbox
                params["lamin"] = lamin
                params["lamax"] = lamax
                params["lomin"] = lomin
                params["lomax"] = lomax
            
            response = requests.get(
                url,
                params=params,
                auth=self.auth,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("states"):
                return pd.DataFrame()
            
            # Parse states into dataframe
            states = data["states"]
            df = pd.DataFrame(states, columns=[
                'icao24', 'callsign', 'origin_country', 'time_position',
                'last_contact', 'longitude', 'latitude', 'altitude',
                'on_ground', 'velocity', 'heading', 'vertical_rate',
                'sensors', 'geo_altitude'
            ])
            
            # Clean callsign (remove trailing whitespace)
            df['callsign'] = df['callsign'].str.strip()
            
            # Add timestamp
            df['fetch_time'] = datetime.now(timezone.utc)
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching from OpenSky API: {e}")
            return pd.DataFrame()
    
    def get_flights_by_airline(self, airline_code, bbox=None):
        """
        Get live flights for specific airline.
        
        Args:
            airline_code (str): IATA airline code (e.g., 'AA', 'DL', 'UA')
            bbox (tuple): Optional bounding box
            
        Returns:
            pd.DataFrame: Filtered flight data for airline
        """
        try:
            # Map IATA to callsign prefix
            iata_to_callsign = {
                "AA": "AAL",    # American Airlines
                "DL": "DAL",    # Delta
                "UA": "UAL",    # United
                "SW": "SWA",    # Southwest
                "B6": "JBU",    # JetBlue
                "AS": "ASA",    # Alaska
                "F9": "FFT",    # Frontier
                "NK": "NKS",    # Spirit
                "HA": "HAL",    # Hawaiian
            }
            
            callsign_prefix = iata_to_callsign.get(airline_code.upper(), airline_code.upper())
            
            all_flights = self.get_live_flights(bbox=bbox)
            
            if all_flights.empty:
                return all_flights
            
            # Filter by callsign prefix
            airline_flights = all_flights[
                all_flights['callsign'].str.startswith(callsign_prefix, na=False)
            ].copy()
            
            return airline_flights
            
        except Exception as e:
            print(f"Error filtering flights by airline: {e}")
            return pd.DataFrame()
    
    def get_flight_track(self, icao24):
        """
        Get track history for specific flight (ICAO24 address).
        
        Args:
            icao24 (str): ICAO24 aircraft address (hexadecimal)
            
        Returns:
            pd.DataFrame: Flight track with coordinates and times
        """
        try:
            url = f"{self.BASE_URL}/tracks/all"
            
            params = {"icao24": icao24}
            
            response = requests.get(
                url,
                params=params,
                auth=self.auth,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("path"):
                return pd.DataFrame()
            
            # Parse track data
            df = pd.DataFrame(data["path"], columns=['time', 'latitude', 'longitude', 'altitude', 'on_ground'])
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching flight track: {e}")
            return pd.DataFrame()
    
    def health_check(self):
        """
        Check if OpenSky API is accessible.
        
        Returns:
            bool: True if API is reachable, False otherwise
        """
        try:
            url = f"{self.BASE_URL}/states/all"
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except:
            return False


def format_flight_data(df):
    """
    Format OpenSky raw data to match AirFly schema.
    
    Args:
        df (pd.DataFrame): Raw OpenSky data
        
    Returns:
        pd.DataFrame: Formatted flight data
    """
    if df.empty:
        return df
    
    formatted = df.copy()
    
    # Add derived columns
    formatted['flight_status'] = formatted.apply(
        lambda row: 'ON_GROUND' if row.get('on_ground', False) else 'IN_FLIGHT',
        axis=1
    )
    
    # Convert altitude to feet if in meters
    if 'altitude' in formatted.columns:
        formatted['altitude_ft'] = formatted['altitude'] * 3.28084
    
    # Extract airline code from callsign (first 3 chars typically)
    formatted['airline_code'] = formatted['callsign'].str[:2]
    
    return formatted
