import pandas as pd
import sqlite3
import os
import re

class AirFlyChatbot:
    def __init__(self):
        self.base_dir = os.path.abspath(os.path.dirname(__file__))
        self.db_path = os.path.join(self.base_dir, '..', 'instance', 'database', 'database.db')
        # Check standard path if not found
        if not os.path.exists(self.db_path):
            self.db_path = os.path.join(self.base_dir, '..', 'instance', 'database.db')
            
        self.excel_path = os.path.join(self.base_dir, '..', 'Infosys Project', 'dataset', 'PowerBI_Dashboard_Summary.xlsx')
        
        # Load IATA airline mapping
        self.airline_mapping = {
            "AA": "American Airlines",
            "AS": "Alaska Airlines",
            "B6": "JetBlue",
            "DL": "Delta Air Lines",
            "EV": "ExpressJet",
            "F9": "Frontier Airlines",
            "HA": "Hawaiian Airlines",
            "MQ": "Envoy Air",
            "NK": "Spirit Airlines",
            "OO": "SkyWest Airlines",
            "UA": "United Airlines",
            "US": "US Airways",
            "VX": "Virgin America",
            "WN": "Southwest Airlines"
        }

        # Months list
        self.months = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sept": 9, "sep": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12
        }

    def query_db(self, query_str, params=()):
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query_str, conn, params=params)
            conn.close()
            return df
        except Exception as e:
            print(f"Chatbot SQLite query error: {e}")
            return pd.DataFrame()

    def query_db(self, query_str, params=()):
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query_str, conn, params=params)
            conn.close()
            return df
        except Exception as e:
            print(f"Chatbot SQLite query error: {e}")
            return pd.DataFrame()

    def get_response(self, query):
        query = query.lower().strip()

        # Check if SQLite analytics tables are populated
        test_df = self.query_db("SELECT name FROM sqlite_master WHERE type='table' AND name='airline_analytics'")
        has_sql = not test_df.empty

        # Match airlines
        matched_airlines = []
        for code, name in self.airline_mapping.items():
            if code.lower() in query or name.lower() in query:
                matched_airlines.append((code, name))

        # Match months
        matched_month = None
        for m_name, m_num in self.months.items():
            if m_name in query:
                matched_month = (m_name, m_num)
                break

        # Match routes
        route_match = re.search(r'\b([a-z]{3})[- ]+to[- ]+([a-z]{3})\b|\b([a-z]{3})-([a-z]{3})\b', query)
        route_str = None
        if route_match:
            if route_match.group(1):
                org, dest = route_match.group(1).upper(), route_match.group(2).upper()
            else:
                org, dest = route_match.group(3).upper(), route_match.group(4).upper()
            route_str = f"{org}-{dest}"

        # Match airport
        airport_match = None
        airport_cand = re.findall(r'\b([a-z]{3})\b', query)
        for code in airport_cand:
            if code not in self.months and code.upper() in self.airline_mapping:
                continue
            if code not in self.months:
                airport_match = code.upper()
                break

        # ----------------------------------------------------
        # 1. DETAILED SQL BACKED ANALYTICS (IF DATABASE READY)
        # ----------------------------------------------------
        if has_sql:
            # Top Airlines / Carriers Ranking
            if "top" in query or "list" in query or "show" in query or "best" in query or "all" in query:
                if "airline" in query or "carrier" in query or "operator" in query:
                    if "delay" in query or "worst" in query:
                        # Rank by delay descending
                        df = self.query_db("SELECT * FROM airline_analytics ORDER BY Avg_Arrival_Delay DESC LIMIT 10")
                        title = "Worst 10 Airlines by Average Arrival Delay"
                    elif "punctual" in query or "best" in query or "on time" in query:
                        # Rank by delay ascending
                        df = self.query_db("SELECT * FROM airline_analytics ORDER BY Avg_Arrival_Delay ASC LIMIT 10")
                        title = "Top 10 Most Punctual Airlines"
                    else:
                        # Default: Rank by total flight volume descending
                        df = self.query_db("SELECT * FROM airline_analytics ORDER BY Total_Flights DESC LIMIT 10")
                        title = "Top 10 Airlines by Flight Volume"

                    if not df.empty:
                        rows = []
                        for idx, r in df.iterrows():
                            code = r['AIRLINE']
                            name = self.airline_mapping.get(code, code)
                            rows.append(
                                f"<tr>"
                                f"<td><b>{idx+1}</b></td>"
                                f"<td>{name} ({code})</td>"
                                f"<td class='text-end'>{r['Total_Flights']:,}</td>"
                                f"<td class='text-end'>{r['Avg_Arrival_Delay']:.2f} min</td>"
                                f"</tr>"
                            )
                        
                        table_html = (
                            f"📋 <b>{title}</b><br><br>"
                            f"<table class='table table-sm table-striped table-bordered text-dark' style='font-size: 0.85rem; background: #fff;'>"
                            f"<thead>"
                            f"<tr>"
                            f"<th>#</th>"
                            f"<th>Airline</th>"
                            f"<th class='text-end'>Total Flights</th>"
                            f"<th class='text-end'>Avg Arrival Delay</th>"
                            f"</tr>"
                            f"</thead>"
                            f"<tbody>"
                            f"{''.join(rows)}"
                            f"</tbody>"
                            f"</table>"
                        )
                        return table_html

            # A. Global Stats Query (Overall flights, delay sums, cancellation rates, longest flights)
            if "overall" in query or "total flights" in query or "global" in query or "how many flights" in query and not matched_airlines and not matched_month and not route_str:
                df = self.query_db("SELECT * FROM global_analytics")
                if not df.empty:
                    r = df.iloc[0]
                    cancel_rate = (r['total_cancelled'] / r['total_flights']) * 100
                    return (
                        f"📊 <b>AirFly Global Operational Metrics (Entire Dataset)</b><br><br>"
                        f"• Total Scheduled Flights: <b>{r['total_flights']:,}</b> flights<br>"
                        f"• Total Cancellations: <b>{r['total_cancelled']:,}</b> (Rate: <b>{cancel_rate:.2f}%</b>)<br>"
                        f"• Total Diversions: <b>{r['total_diverted']:,}</b> flights<br>"
                        f"• Average Departure Delay: <b>{r['sum_departure_delay']/r['total_flights']:.2f} min</b><br>"
                        f"• Average Arrival Delay: <b>{r['sum_arrival_delay']/r['total_flights']:.2f} min</b><br>"
                        f"• Max Scheduled Flight Distance: <b>{r['max_distance']:,} miles</b><br>"
                        f"• Max Recorded Flight Delay: <b>{r['max_arrival_delay']:.0f} min</b>"
                    )

            # B. Delays broken down by causes (Weather, NAS, Security, Carrier, Late Aircraft)
            if "weather delay" in query or "storm" in query or "rain" in query or "snow" in query:
                if len(matched_airlines) == 1:
                    code, name = matched_airlines[0]
                    df = self.query_db("SELECT Avg_Weather_Delay, Avg_Arrival_Delay FROM airline_analytics WHERE AIRLINE=?", (code,))
                    if not df.empty:
                        r = df.iloc[0]
                        return f"🌦️ <b>Weather Delay for {name} ({code})</b><br><br>• Average Weather Delay: <b>{r['Avg_Weather_Delay']:.2f} minutes</b> per flight (out of <b>{r['Avg_Arrival_Delay']:.2f} min</b> average total delay)."
                
                # Global weather delays
                df = self.query_db("SELECT sum_weather_delay, total_flights FROM global_analytics")
                if not df.empty:
                    r = df.iloc[0]
                    return f"🌦️ <b>Global Weather Delays</b><br><br>Across all flights, weather anomalies caused an average of <b>{r['sum_weather_delay']/r['total_flights']:.2f} minutes</b> of delay per departure."

            if "carrier delay" in query or "maintenance" in query or "airline delay" in query:
                if len(matched_airlines) == 1:
                    code, name = matched_airlines[0]
                    df = self.query_db("SELECT Avg_Carrier_Delay, Avg_Arrival_Delay FROM airline_analytics WHERE AIRLINE=?", (code,))
                    if not df.empty:
                        r = df.iloc[0]
                        return f"✈️ <b>Carrier/Airline Delay for {name} ({code})</b><br><br>• Average Carrier Delay: <b>{r['Avg_Carrier_Delay']:.2f} minutes</b> (due to maintenance, crew shortages, or administrative issues)."

            if "taxi" in query or "taxi out" in query or "taxi in" in query:
                if len(matched_airlines) == 1:
                    code, name = matched_airlines[0]
                    df = self.query_db("SELECT Avg_Taxi_In, Avg_Taxi_Out FROM airline_analytics WHERE AIRLINE=?", (code,))
                    if not df.empty:
                        r = df.iloc[0]
                        return f"🚕 <b>Taxi Duration for {name} ({code})</b><br><br>• Average Taxi-In (landing to gate): <b>{r['Avg_Taxi_In']:.2f} min</b><br>• Average Taxi-Out (gate to takeoff): <b>{r['Avg_Taxi_Out']:.2f} min</b>"

            if "air time" in query or "duration" in query or "elapsed time" in query:
                if len(matched_airlines) == 1:
                    code, name = matched_airlines[0]
                    df = self.query_db("SELECT Avg_Air_Time, Avg_Elapsed_Time FROM airline_analytics WHERE AIRLINE=?", (code,))
                    if not df.empty:
                        r = df.iloc[0]
                        return f"⏱️ <b>Flight Duration for {name} ({code})</b><br><br>• Average Air Time: <b>{r['Avg_Air_Time']:.2f} min</b> (wheels-up to wheels-down)<br>• Average Elapsed Time: <b>{r['Avg_Elapsed_Time']:.2f} min</b> (gate-to-gate)."

            if "distance" in query or "how far" in query:
                if len(matched_airlines) == 1:
                    code, name = matched_airlines[0]
                    df = self.query_db("SELECT Avg_Distance FROM airline_analytics WHERE AIRLINE=?", (code,))
                    if not df.empty:
                        return f"📏 <b>Average Flight Distance for {name} ({code})</b>: <b>{df.iloc[0]['Avg_Distance']:.2f} miles</b>."
                if route_str:
                    df = self.query_db("SELECT Avg_Distance FROM route_analytics WHERE ROUTE=?", (route_str,))
                    if not df.empty:
                        return f"📏 <b>Flight Distance for Route {route_str}</b>: <b>{df.iloc[0]['Avg_Distance']:.2f} miles</b>."

            # Head-to-Head Airline Comparison
            if len(matched_airlines) >= 2:
                code1, name1 = matched_airlines[0]
                code2, name2 = matched_airlines[1]
                df1 = self.query_db("SELECT * FROM airline_analytics WHERE AIRLINE=?", (code1,))
                df2 = self.query_db("SELECT * FROM airline_analytics WHERE AIRLINE=?", (code2,))
                
                if not df1.empty and not df2.empty:
                    r1 = df1.iloc[0]
                    r2 = df2.iloc[0]
                    
                    c_rate1 = (r1['Cancellations'] / r1['Total_Flights']) * 100
                    c_rate2 = (r2['Cancellations'] / r2['Total_Flights']) * 100
                    
                    compare_table = (
                        f"⚖️ <b>Carrier Comparison: {name1} vs {name2}</b><br><br>"
                        f"<table class='table table-sm table-striped table-bordered text-dark' style='font-size: 0.85rem; background: #fff;'>"
                        f"<thead>"
                        f"<tr>"
                        f"<th>Operational Metric</th>"
                        f"<th class='text-end'>{code1}</th>"
                        f"<th class='text-end'>{code2}</th>"
                        f"</tr>"
                        f"</thead>"
                        f"<tbody>"
                        f"<tr><td><b>Scheduled Flights</b></td><td class='text-end'>{r1['Total_Flights']:,}</td><td class='text-end'>{r2['Total_Flights']:,}</td></tr>"
                        f"<tr><td><b>Cancellations (Rate)</b></td><td class='text-end'>{r1['Cancellations']:,} ({c_rate1:.2f}%)</td><td class='text-end'>{r2['Cancellations']:,} ({c_rate2:.2f}%)</td></tr>"
                        f"<tr><td><b>Avg Arrival Delay</b></td><td class='text-end'>{r1['Avg_Arrival_Delay']:.2f} min</td><td class='text-end'>{r2['Avg_Arrival_Delay']:.2f} min</td></tr>"
                        f"<tr><td><b>Avg Departure Delay</b></td><td class='text-end'>{r1['Avg_Departure_Delay']:.2f} min</td><td class='text-end'>{r2['Avg_Departure_Delay']:.2f} min</td></tr>"
                        f"<tr><td><b>Avg Weather Delay</b></td><td class='text-end'>{r1['Avg_Weather_Delay']:.2f} min</td><td class='text-end'>{r2['Avg_Weather_Delay']:.2f} min</td></tr>"
                        f"<tr><td><b>Avg Carrier Delay</b></td><td class='text-end'>{r1['Avg_Carrier_Delay']:.2f} min</td><td class='text-end'>{r2['Avg_Carrier_Delay']:.2f} min</td></tr>"
                        f"<tr><td><b>Avg Air Time</b></td><td class='text-end'>{r1['Avg_Air_Time']:.2f} min</td><td class='text-end'>{r2['Avg_Air_Time']:.2f} min</td></tr>"
                        f"<tr><td><b>Avg Distance Flown</b></td><td class='text-end'>{r1['Avg_Distance']:.1f} mi</td><td class='text-end'>{r2['Avg_Distance']:.1f} mi</td></tr>"
                        f"</tbody>"
                        f"</table>"
                    )
                    return compare_table

            # F. Airport Specifics Overview (JFK, LAX, ATL, ORD)
            if airport_match:
                try:
                    xl = pd.ExcelFile(self.excel_path)
                    map_data = xl.parse('MapData')
                    row = map_data[map_data['ORIGIN_AIRPORT'] == airport_match]
                    if not row.empty:
                        r = row.iloc[0]
                        return (
                            f"📍 <b>Airport Operations Profile: {airport_match} Hub</b><br><br>"
                            f"• Total Scheduled Departures: <b>{r['Total_Flights']:,}</b> flights<br>"
                            f"• Average Arrival Delay: <b>{r['Avg_Arrival_Delay']:.2f} minutes</b><br>"
                            f"• Geographic Location: <b>({r['Latitude']:.4f}° N, {r['Longitude']:.4f}° W)</b>"
                        )
                except Exception:
                    pass

            # C. Airline-specific multi-attribute query
            if len(matched_airlines) == 1:
                code, name = matched_airlines[0]
                df = self.query_db("SELECT * FROM airline_analytics WHERE AIRLINE=?", (code,))
                if not df.empty:
                    r = df.iloc[0]
                    cancel_rate = (r['Cancellations'] / r['Total_Flights']) * 100
                    return (
                        f"✈️ <b>Airline Intelligence Profile: {name} ({code})</b><br><br>"
                        f"• Scheduled Flights: <b>{r['Total_Flights']:,}</b><br>"
                        f"• Cancellations: <b>{r['Cancellations']:,}</b> (Rate: <b>{cancel_rate:.2f}%</b>)<br>"
                        f"• Average Arrival Delay: <b>{r['Avg_Arrival_Delay']:.2f} min</b><br>"
                        f"• Average Departure Delay: <b>{r['Avg_Departure_Delay']:.2f} min</b><br>"
                        f"• Weather Delay Factor: <b>{r['Avg_Weather_Delay']:.2f} min</b><br>"
                        f"• NAS Delay Factor: <b>{r['Avg_NAS_Delay']:.2f} min</b><br>"
                        f"• Average Distance Flown: <b>{r['Avg_Distance']:.1f} miles</b>"
                    )

            # D. Month-specific multi-attribute query
            if matched_month:
                m_name, m_num = matched_month
                df = self.query_db("SELECT * FROM monthly_analytics WHERE MONTH=?", (m_num,))
                if not df.empty:
                    r = df.iloc[0]
                    cancel_rate = (r['Cancellations'] / r['Total_Flights']) * 100
                    return (
                        f"📅 <b>Monthly Intelligence Profile: {r['MONTH']} ({m_name.title()})</b><br><br>"
                        f"• Total Flights: <b>{r['Total_Flights']:,}</b><br>"
                        f"• Cancellations: <b>{r['Cancellations']:,}</b> (Rate: <b>{cancel_rate:.2f}%</b>)<br>"
                        f"• Avg Departure Delay: <b>{r['Avg_Departure_Delay']:.2f} min</b><br>"
                        f"• Avg Arrival Delay: <b>{r['Avg_Arrival_Delay']:.2f} min</b><br>"
                        f"• Avg Weather Delay: <b>{r['Avg_Weather_Delay']:.2f} min</b><br>"
                        f"• Average Distance Traveled: <b>{r['Avg_Distance']:.1f} miles</b>"
                    )

            # E. Route inquiries
            if route_str:
                df = self.query_db("SELECT * FROM route_analytics WHERE ROUTE=?", (route_str,))
                if not df.empty:
                    r = df.iloc[0]
                    cancel_rate = (r['Cancellations'] / r['Total_Flights']) * 100
                    return (
                        f"🛣️ <b>Route Analysis Profile: {route_str}</b><br><br>"
                        f"• Total Scheduled Flights: <b>{r['Total_Flights']:,}</b><br>"
                        f"• Cancellations: <b>{r['Cancellations']:,}</b> (Rate: <b>{cancel_rate:.2f}%</b>)<br>"
                        f"• Average Arrival Delay: <b>{r['Avg_Arrival_Delay']:.2f} min</b><br>"
                        f"• Average Departure Delay: <b>{r['Avg_Departure_Delay']:.2f} min</b><br>"
                        f"• Flight Distance: <b>{r['Avg_Distance']:.1f} miles</b>"
                    )

        # ----------------------------------------------------
        # 2. EXCEL POWER BI STATIC BREAKDOWN (FALLBACK)
        # ----------------------------------------------------
        try:
            xl = pd.ExcelFile(self.excel_path)
            map_data = xl.parse('MapData')
            monthly_trends = xl.parse('MonthlyTrends')
            cancellation_causes = xl.parse('CancellationCauses')
            top_routes = xl.parse('TopRoutes')
            airline_stats = xl.parse('AirlineStats')
            
            # Match Airlines
            if len(matched_airlines) == 1:
                code, name = matched_airlines[0]
                row = airline_stats[airline_stats['AIRLINE'] == code]
                if not row.empty:
                    r = row.iloc[0]
                    return (
                        f"<b>Airline Profile: {name} ({code})</b><br><br>"
                        f"• Total Flights: <b>{r['Total_Flights']:,}</b><br>"
                        f"• Average Arrival Delay: <b>{r['Avg_Arrival_Delay']:.2f} minutes</b>"
                    )

            # Match Month
            if matched_month:
                m_name, m_num = matched_month
                row = monthly_trends[monthly_trends['MONTH'] == m_num]
                if not row.empty:
                    r = row.iloc[0]
                    return (
                        f"<b>Monthly Trend: {r['MonthLabel']}</b><br><br>"
                        f"• Total Flights: <b>{r['Total_Flights']:,}</b><br>"
                        f"• Cancellations: <b>{r['Cancellations']:,}</b> (Rate: <b>{r['Cancel_Rate']*100:.2f}%</b>)<br>"
                        f"• Avg Arrival Delay: <b>{r['Avg_Arrival_Delay']:.2f} min</b>"
                    )
        except Exception:
            pass

        # 3. Help/Greetings
        if "summary" in query or "overview" in query or "dashboard" in query or "hello" in query or "help" in query:
            return (
                f"👋 <b>Welcome to AirFly Insights AI Operations Assistant!</b><br><br>"
                f"I can query the entire 5.8 million flight records database instantly to answer:<br>"
                f"• <b>Airline Specifics</b>: average delay, weather/carrier delays, flight distances, taxi durations.<br>"
                f"• <b>Routes & Airports</b>: busiest routes, cancellation rates, arrival delays.<br>"
                f"• <b>Temporal Trends</b>: month-by-month cancellations, delays, operational load.<br><br>"
                f"Try asking: <i>'What is the average weather delay for American Airlines?'</i> or <i>'Tell me overall flight statistics.'</i>"
            )

        # Final Fallback
        return "The requested information is not available in the dataset."

# Singleton instance
chatbot = AirFlyChatbot()
