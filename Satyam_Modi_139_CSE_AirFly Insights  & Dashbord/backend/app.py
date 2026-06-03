"""
Global Income Distribution Analytics Dashboard
Flask Backend Application
"""

import os
import pandas as pd  # type: ignore
from datetime import datetime, date, timezone
import calendar
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify
from flask_sqlalchemy import SQLAlchemy  # type: ignore
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user  # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash  # type: ignore
from io import BytesIO

# --- App Configuration ---

base_dir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(base_dir, '..'))

app = Flask(__name__, 
            template_folder=os.path.join(project_root, 'frontend', 'templates'),
            static_folder=os.path.join(project_root, 'frontend', 'static'),
            instance_path=os.path.join(project_root, 'instance'))

# Import Chatbot
from chatbot import chatbot

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Chatbot API endpoint."""
    user_query = request.json.get('query', '')
    if not user_query:
        return jsonify({"response": "Please ask me something!"})
    
    response = chatbot.get_response(user_query)
    return jsonify({"response": response})

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db').replace("postgres://", "postgresql://")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# --- Database Models ---

class User(UserMixin, db.Model):
    """Users table for authentication."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_banned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Visitor(db.Model):
    """Visitors table for tracking site visits."""
    id = db.Column(db.Integer, primary_key=True)
    visit_date = db.Column(db.Date, nullable=False)
    visitor_count = db.Column(db.Integer, default=1)

class Feedback(db.Model):
    """Feedback table for storing user feedback and admin communication."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='General Feedback')
    message = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)
    status = db.Column(db.String(20), default='Pending') # Pending, Reviewed, Implemented
    admin_response = db.Column(db.Text, nullable=True)
    is_read_by_user = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = db.relationship('User', backref='feedbacks')

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))

# --- Helper Functions ---

def track_visitor():
    """Increment visitor count for today."""
    today = date.today()
    visitor = Visitor.query.filter_by(visit_date=today).first()
    if visitor:
        visitor.visitor_count += 1
    else:
        visitor = Visitor(visit_date=today, visitor_count=1)
        db.session.add(visitor)
    db.session.commit()

# --- Routes ---

@app.route('/')
def home():
    """Home page route."""
    track_visitor()
    return render_template('home.html')

@app.route('/about')
def about():
    """About page route."""
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        login_type = request.form.get('login_type', 'user') # default to user if not provided
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            # Strict role-based login separation
            if login_type == 'admin':
                if email != 'admin@airfly.com':
                    flash('Unauthorized Admin Access: Regular users must use the User login portal.', 'danger')
                    return redirect(url_for('login'))
            else: # login_type == 'user'
                if email == 'admin@airfly.com':
                    flash('Administrator Detected: Please use the Administrative login portal.', 'warning')
                    return redirect(url_for('login'))

            if getattr(user, 'is_banned', False):
                flash('Your account has been banned. Please contact the administrator.', 'danger')
                return redirect(url_for('login'))
            
            login_user(user)
            flash(f'Welcome back, {user.username}! Login successful.', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Derive username from email prefix
        username = email.split('@')[0] if email and '@' in email else 'user'

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already exists.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Account created successfully! Your username is {username}. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('login.html', register=True)

@app.route('/logout')
@login_required
def logout():
    """User logout route."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Native Web Dashboard."""
    return render_template('dashboard.html')

@app.route('/download-dataset')
@login_required
def download_dataset():
    """Download the cleaned flights dataset CSV."""
    dataset_path = os.path.join(project_root, 'Infosys Project', 'dataset', 'cleaned_flights.csv')
    if os.path.exists(dataset_path):
        return send_file(dataset_path, as_attachment=True, download_name='AirFly_Cleaned_Flights.csv', mimetype='text/csv')
    else:
        flash('Dataset file not found.', 'danger')
        return redirect(url_for('home'))

@app.route('/api/dashboard-data')
@login_required
def dashboard_data():
    """API endpoint providing aggregated JSON data for frontend charts."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    excel_path = os.path.join(base_dir, '..', 'dataset', 'Global Income Distribution Dataset.xlsx')
    
    # Use fallback structure perfectly mapped to the chart needs if pandas file missing
    data = {
        "years": ["2010", "2015", "2020", "2024"],
        "continents": ["Africa", "Asia", "Europe", "North America", "Oceania", "South America"],
        "countries": ["USA", "China", "India", "Germany", "Brazil", "South Africa"],
        "kpis": {
            "total_countries": 20, "total_gdp": 18080000, "total_gini": 18240, 
            "total_unemployment": 3820, "strength_score": -8.30, "gini_severity": 76.34
        },
        "charts": {
            "top10_gini": {
                "labels": ["South Africa", "Brazil", "Mexico", "Saudi Arabia", "China", "Turkiye", "United States", "Russia", "Indonesia", "Italy"],
                "data": [65, 54, 48, 46, 42, 41, 41, 38, 35, 34]
            },
            "donut_structure": {
                "labels": ["Lower Income", "Lower-Middle", "Upper-Middle", "High Income"],
                "data": [44.92, 21.77, 15.40, 8.59]
            },
            "regional_gdp": {
                "labels": ["Europe", "Asia", "North America", "Oceania", "South America", "Africa"],
                "data": [9000000, 3700000, 3300000, 1300000, 400000, 300000]
            },
            "regional_gini": {
                "labels": ["Africa", "South America", "North America", "Asia", "Europe", "Oceania"],
                "data": [65, 54, 41, 37, 33, 32]
            },
            "regional_unemp": {
                "labels": ["Africa", "South America", "Europe", "Asia", "North America", "Oceania"],
                "data": [26, 10, 8, 6, 6, 5]
            },
            "yoy_gdp": {
                "labels": ["2000", "2005", "2010", "2015", "2020", "2024"],
                "data": [-41.05, -42.15, -39.12, -39.61, -43.55, -41.34]
            },
            "yoy_gini": {
                "labels": ["2000", "2005", "2010", "2015", "2020", "2024"],
                "data": [37.65, -3.24, -3.21, -1.9, -3.73, -5.32]
            },
            "yoy_unemp": {
                "labels": ["2000", "2005", "2010", "2015", "2020", "2024"],
                "data": [8.04, 2.5, -1.05, 3.0, -0.14, 4.62]
            },
            "scatter": {
                "colors": ['#3b82f6', '#eab308', '#ec4899', '#f97316', '#8b5cf6', '#ef4444', '#10b981', '#14b8a6', '#f43f5e', '#6366f1'],
                "data": [
                    {"country": "South Africa", "gdp": 15000, "gini": 65},
                    {"country": "Brazil", "gdp": 20000, "gini": 54},
                    {"country": "Mexico", "gdp": 22000, "gini": 48},
                    {"country": "China", "gdp": 25000, "gini": 42},
                    {"country": "India", "gdp": 10000, "gini": 35},
                    {"country": "USA", "gdp": 75000, "gini": 41},
                    {"country": "Germany", "gdp": 60000, "gini": 31}
                ]
            }
        }
    }
    
    # Dynamic Improvement: Override data dictionary by actually loading Excel file via pandas
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            
            # Extract unique values for slicers
            unique_years = sorted([str(y) for y in df['year'].unique().tolist()])
            unique_continents = sorted(df['Country_Continent'].unique().tolist())
            unique_countries = sorted(df['Country_Name'].unique().tolist())
            
            data["years"] = unique_years
            data["continents"] = unique_continents
            data["countries"] = unique_countries
            
            # Map kpi aggregates from real data
            data["kpis"]["total_countries"] = len(unique_countries)
            data["kpis"]["total_gdp"] = float(df['GDP_Per_Capita ($)'].sum())
            data["kpis"]["total_gini"] = float(df['Gini_Index (0-100)'].sum())
            data["kpis"]["total_unemployment"] = float(df['Unemployement_Rate (%)'].sum())
            
        except Exception as e:
            print(f"Excel parse error: {e}")
            
    from flask import jsonify
    return jsonify(data)

@app.route('/api/country-comparison')
@login_required
def country_comparison():
    """API endpoint for side-by-side country comparison with independent years."""
    c1 = request.args.get('country1')
    c2 = request.args.get('country2')
    year1 = request.args.get('year1')
    year2 = request.args.get('year2')
    
    if not all([c1, c2, year1, year2]):
        return jsonify({"error": "Missing parameters (country1, country2, year1, year2)"}), 400
        
    base_dir = os.path.abspath(os.path.dirname(__file__))
    excel_path = os.path.join(base_dir, '..', 'dataset', 'Global Income Distribution Dataset.xlsx')
    
    if not os.path.exists(excel_path):
        return jsonify({"error": "Dataset file not found"}), 404
        
    try:
        df = pd.read_excel(excel_path)
        
        # Ensure years are integers
        try:
            y1_val = int(year1)
            y2_val = int(year2)
        except ValueError:
            return jsonify({"error": "Years must be numeric"}), 400
            
        # Filter for each country at its respective year
        res1 = df[(df['Country_Name'] == c1) & (df['year'] == y1_val)]
        res2 = df[(df['Country_Name'] == c2) & (df['year'] == y2_val)]
        
        if res1.empty or res2.empty:
            return jsonify({
                "error": "Data not found for one or both countries in selected years",
                "c1_found": not res1.empty,
                "c2_found": not res2.empty
            }), 404
            
        data1 = res1.iloc[0].to_dict()
        data2 = res2.iloc[0].to_dict()
        
        # Clean data for JSON (handle NaN)
        data1 = {k: (v if pd.notna(v) else None) for k, v in data1.items()}
        data2 = {k: (v if pd.notna(v) else None) for k, v in data2.items()}
        
        return jsonify({
            "country1": data1,
            "country2": data2
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    """Feedback form page with history."""
    if current_user.email == 'admin@airfly.com':
        return redirect(url_for('admin'))
    if request.method == 'POST':
        category = request.form.get('category', 'General Feedback')
        message = request.form.get('message')
        rating = request.form.get('rating', 5, type=int)
        new_feedback = Feedback(
            user_id=current_user.id,
            name=current_user.username,
            email=current_user.email,
            category=category,
            message=message,
            rating=rating
        )
        db.session.add(new_feedback)
        db.session.commit()
        flash('Thank you for your feedback! We will review it soon.', 'success')
        return redirect(url_for('feedback'))
    
    # Get user feedback history
    history = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.submitted_at.desc()).all()
    
    # Mark responses as read when user views the feedback page
    unread = Feedback.query.filter_by(user_id=current_user.id, is_read_by_user=False).filter(Feedback.admin_response.isnot(None)).all()
    for f in unread:
        f.is_read_by_user = True
    if unread:
        db.session.commit()
        
    return render_template('feedback.html', history=history)

@app.route('/api/user/notifications')
@login_required
def user_notifications():
    """Get count of unread admin responses for the current user."""
    count = Feedback.query.filter_by(user_id=current_user.id, is_read_by_user=False).filter(Feedback.admin_response.isnot(None)).count()
    return jsonify({"unread_count": count})

@app.route('/admin/feedback/reply/<int:feedback_id>', methods=['POST'])
@login_required
def admin_reply(feedback_id):
    """Admin endpoint to reply to feedback and update status."""
    if current_user.email != 'admin@airfly.com':
        return jsonify({"error": "Unauthorized"}), 403
        
    f = Feedback.query.get_or_404(feedback_id)
    response = request.form.get('response')
    status = request.form.get('status')
    
    if response:
        f.admin_response = response
        f.is_read_by_user = False # Trigger new notification for user
    
    if status:
        f.status = status
        
    db.session.commit()
    flash('Reply sent and status updated successfully.', 'success')
    return redirect(url_for('admin'))

@app.route('/api/admin/visits')
@login_required
def get_visits():
    """API endpoint for date-specific visitor counts."""
    if current_user.email != 'admin@airfly.com':
        return jsonify({"error": "Unauthorized"}), 403
    
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "Date required"}), 400
        
    try:
        # Parse the date string from YYYY-MM-DD
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        visitor = Visitor.query.filter_by(visit_date=query_date).first()
        count = visitor.visitor_count if visitor else 0
        return jsonify({"date": date_str, "count": count})
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

@app.route('/api/admin/user-growth')
@login_required
def get_user_growth_api():
    """API endpoint for daily user growth in a selected month."""
    if current_user.email != 'admin@airfly.com':
        return jsonify({"error": "Unauthorized"}), 403
    
    month_str = request.args.get('month') # Expected format: YYYY-MM
    if not month_str:
        now = datetime.now()
        year, month = now.year, now.month
    else:
        try:
            year, month = map(int, month_str.split('-'))
        except ValueError:
            return jsonify({"error": "Invalid month format"}), 400
            
    # Get number of days in the selected month
    num_days = calendar.monthrange(year, month)[1]
    
    # Initialize daily counts
    labels = [str(day) for day in range(1, num_days + 1)]
    data = [0] * num_days
    
    # Query users registered in that month and year
    users_in_month = User.query.filter(
        db.extract('year', User.created_at) == year,
        db.extract('month', User.created_at) == month
    ).all()
    
    for u in users_in_month:
        day = u.created_at.day
        if 1 <= day <= num_days:
            data[day-1] += 1
            
    # Calculate month-specific feedback metrics
    avg_rating = db.session.query(db.func.avg(Feedback.rating)).filter(
        db.extract('year', Feedback.submitted_at) == year,
        db.extract('month', Feedback.submitted_at) == month
    ).scalar() or 0
    
    total_users_system = User.query.count()
            
    return jsonify({
        "labels": labels, 
        "data": data, 
        "month": month_str,
        "avg_rating": round(float(avg_rating), 1),
        "total_users_system": total_users_system
    })

@app.route('/admin')
@login_required
def admin():
    """Admin analytics panel."""
    # Only allow the admin user to access this page
    if current_user.email != 'admin@airfly.com':
        flash('Access Denied: You do not have administrator privileges.', 'danger')
        return redirect(url_for('dashboard'))
    # Calculate total visits and today's visits
    total_visits = db.session.query(db.func.sum(Visitor.visitor_count)).scalar() or 0
    today_record = Visitor.query.filter_by(visit_date=date.today()).first()
    today_visits = today_record.visitor_count if today_record else 0
    
    # Total users for the table
    users = User.query.order_by(User.created_at.desc()).all()
    total_users = len(users)
    
    # Get recent feedback
    feedbacks = Feedback.query.order_by(Feedback.submitted_at.desc()).all()
    
    # Calculate growth intelligence metrics
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    new_users_month = User.query.filter(User.created_at >= first_day_of_month).count()
    
    # Use average rating from feedbacks or calculate via DB
    avg_rating = db.session.query(db.func.avg(Feedback.rating)).scalar() or 0
    
    # Calculate Growth Velocity (e.g., % of users joined in the last month)
    velocity = (new_users_month / total_users * 100) if total_users > 0 else 0
    
    today_date = date.today().strftime('%Y-%m-%d')
    return render_template('admin.html',
                           total_visits=total_visits,
                           today_visits=today_visits,
                           today_date=today_date,
                           total_users=total_users,
                           users=users,
                           feedbacks=feedbacks,
                           new_users_month=new_users_month,
                           avg_rating=round(float(avg_rating), 1),
                           velocity=round(float(velocity), 1))

@app.route('/admin/database')
@login_required
def admin_database():
    """Direct database viewer for the admin."""
    if current_user.email != 'admin@airfly.com':
        flash('Access Denied: You do not have administrator privileges.', 'danger')
        return redirect(url_for('dashboard'))
        
    users = User.query.all()
    feedbacks = Feedback.query.order_by(Feedback.submitted_at.desc()).all()
    visitors = Visitor.query.order_by(Visitor.visit_date.desc()).all()
    
    return render_template('admin_db.html', users=users, feedbacks=feedbacks, visitors=visitors)

@app.route('/admin/toggle-ban/<int:user_id>', methods=['POST'])
@login_required
def toggle_ban(user_id):
    """Toggle the banned status of a user."""
    if current_user.email != 'admin@airfly.com':
        flash('Access Denied: You do not have administrator privileges.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.email == 'admin@airfly.com':
        flash('Cannot ban the administrator account.', 'warning')
    else:
        user.is_banned = not getattr(user, 'is_banned', False)
        db.session.commit()
        status = 'banned' if user.is_banned else 'unbanned'
        flash(f'User {user.username} has been {status}.', 'success')
        
    return redirect(url_for('admin'))

@app.route('/download-report')
@login_required
def download_report():
    """Generate and download Excel report."""
    # Ensure we use the absolute path to point exactly to the correct file
    base_dir = os.path.abspath(os.path.dirname(__file__))
    excel_path = os.path.join(base_dir, '..', 'dataset', 'Global Income Distribution Dataset.xlsx')
    
    # If the exact file exists, send it directly to preserve all its original sheets and formatting
    if os.path.exists(excel_path):
        return send_file(excel_path,
                         download_name="Global Income Distribution Dataset.xlsx",
                         as_attachment=True,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                         
    # Fallback if the file doesn't exist
    data = {
        'Country': ['USA', 'China', 'India', 'Germany', 'Brazil'],
        'Income Level': ['High', 'Upper-Middle', 'Lower-Middle', 'High', 'Upper-Middle'],
        'Population': [331, 1441, 1380, 83, 212],
        'GDP per capita': [63543, 10500, 1900, 45724, 6796]
    }
    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Income Data')
    output.seek(0)

    return send_file(output,
                     download_name="Global_Income_Report.xlsx",
                     as_attachment=True,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- Application Entry Point ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Manual migration to add new columns to feedback table
        try:
            from sqlalchemy import text
            columns = [
                ("user_id", "INTEGER REFERENCES user(id)"),
                ("category", "VARCHAR(50) DEFAULT 'General Feedback'"),
                ("status", "VARCHAR(20) DEFAULT 'Pending'"),
                ("admin_response", "TEXT"),
                ("is_read_by_user", "BOOLEAN DEFAULT 0"),
                ("rating", "INTEGER DEFAULT 5")
            ]
            for col_name, col_type in columns:
                try:
                    db.session.execute(text(f"ALTER TABLE feedback ADD COLUMN {col_name} {col_type}"))
                    db.session.commit()
                    print(f"Successfully added '{col_name}' column to feedback table.")
                except Exception:
                    db.session.rollback() # Column likely exists
        except Exception as e:
            print(f"Migration error: {e}")

        # Update existing usernames to match email prefixes
        try:
            users_to_update = User.query.all()
            updated_count = 0
            for u in users_to_update:
                new_uname = u.email.split('@')[0]
                if u.username != new_uname:
                    u.username = new_uname
                    updated_count += 1
            if updated_count > 0:
                db.session.commit()
                print(f"Successfully updated {updated_count} usernames to match email prefixes.")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating existing usernames: {e}")

        # Update or create default admin account
        admin_email = 'admin@airfly.com'
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin_user = User(username='admin', email=admin_email, password=hashed_pw)
            db.session.add(admin_user)
            print('Admin account created: admin@airfly.com / admin123')
        else:
            admin_user.email = admin_email
        db.session.commit()
    app.run(debug=True)
