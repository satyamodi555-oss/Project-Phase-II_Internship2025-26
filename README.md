# AirFly Insights

AirFly Insights is a comprehensive data analytics platform and web application built with Flask. The platform offers multi-faceted analytics capabilities ranging from global economic metrics to real-time aviation intelligence and interactive AI-driven data exploration.

## Features

- **Aviation Analytics & AI Chatbot Assistant:** 
  Query an extensive database of flight records seamlessly using the built-in AI chatbot. Ask operational questions regarding airlines, average delays (weather, carrier), specific routes, and airport statistics. The chatbot bridges natural language queries to backend SQLite analytics and static data breakdowns.
- **Real-Time Flight Tracking:**
  A background worker (`real_time_worker.py`) continuously polls the OpenSky Network API to fetch live flight data across the US. It updates real-time tracking statistics, manages historical flight updates, and calculates live flight metrics for distinct airlines.
- **Global Income Distribution Dashboard:**
  Interactive dashboard and reporting tools built over economic datasets, providing insights into global GDP, Gini Index, and unemployment rates across countries and continents. Includes side-by-side country comparisons.
- **User Authentication & Management:**
  Secure registration and role-based login system separating standard users from administrative personnel. Includes profile management and secure session handling via Flask-Login.
- **Admin Analytics Dashboard:**
  A dedicated administrative portal tracking site visits, user growth velocities, feedback ratings, and database monitoring with user ban/unban controls.

## Tech Stack

- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login, Pandas
- **Frontend:** HTML, CSS, JavaScript (Jinja2 Templates)
- **Database:** SQLite (default) / PostgreSQL, SQLAlchemy ORM
- **APIs:** OpenSky Network API for live flight telemetry

## Installation and Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd "AirFly Insights"
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Ensure you set necessary environment variables such as `SECRET_KEY` and `DATABASE_URL` (if not using the default SQLite).
   Create a `.env` file in the root directory if needed.

5. **Run the Flask Application:**
   ```bash
   cd backend
   python app.py
   ```
   The application will start on `http://127.0.0.1:5000/`.

6. **Run the Real-Time Flight Worker (Optional):**
   To enable live flight tracking, run the background worker in a separate terminal:
   ```bash
   cd backend
   python real_time_worker.py
   ```

## Project Structure

- `backend/` - Contains the Flask application logic (`app.py`), database models, OpenSky API connector (`opensky_api.py`), AI chatbot (`chatbot.py`), and the background worker (`real_time_worker.py`).
- `frontend/` - Contains all frontend assets.
  - `templates/` - HTML files and Jinja2 templates (e.g., `home.html`, `dashboard.html`, `admin.html`).
  - `static/` - Static assets like CSS, JS, and images.
- `instance/` - Contains the SQLite database file and instances.
- `requirements.txt` - Python dependencies.
- `Internship Report Final.pdf` - Project report detailing the architecture and development phases.
- 
## License

This project is intended for educational and analytical purposes.
