# app.py
# Updated with more robust error handling and user feedback.

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
from functools import wraps
from datetime import datetime, timedelta

# --- Configuration ---
app = Flask(__name__)
app.secret_key = 'your_very_secret_random_string_here_change_me'

db_config = {
    'host': 'mysql6013.site4now.net',
    'user': 'abc901_koratv',
    'password': 'omarreda123',
    'database': 'db_abc901_koratv'
}

# --- Database Connection ---
def create_connection():
    """Creates a connection to the database."""
    try:
        # Use connection pooling for better performance and stability
        connection = mysql.connector.connect(**db_config, pool_name="mypool", pool_size=5)
        return connection
    except Error as e:
        print(f"Database connection error: '{e}'")
        return None

# --- Decorators & Helpers ---
def login_required(f):
    """Decorator to ensure a user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "info")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_match_status(match_time):
    """Calculates the match status based on its time."""
    if not match_time:
        return "غير محدد"
    now = datetime.now()
    match_end_time = match_time + timedelta(minutes=110) # Match duration
    if match_time > now:
        return "لم تبدأ"
    elif now >= match_time and now <= match_end_time:
        return "جارية الآن"
    else:
        return "انتهت"

# --- Public Routes ---
@app.route('/')
def index():
    connection = create_connection()
    matches_with_status = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT m.id, m.match_time, t1.name AS team1_name, t1.logo_url AS team1_logo,
                       t2.name AS team2_name, t2.logo_url AS team2_logo, c.name AS championship_name,
                       m.commentator
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.id
                JOIN teams t2 ON m.team2_id = t2.id
                JOIN championships c ON m.championship_id = c.id
                ORDER BY m.match_time ASC;
            """
            cursor.execute(query)
            matches = cursor.fetchall()
            for match in matches:
                match['status'] = get_match_status(match['match_time'])
                matches_with_status.append(match)
        except Error as e:
            print(f"Error fetching matches: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return render_template('index.html', matches=matches_with_status)

# --- Authentication Routes (No major changes needed here) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (Login logic remains the same)
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        connection = create_connection()
        user = None
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
            except Error as e:
                flash(f"Database error: {e}", "danger")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Please check your login details and try again.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# --- Protected Dashboard Routes ---
@app.route('/dashboard')
@login_required
def dashboard():
    """The main dashboard hub."""
    return render_template('dashboard.html')

# --- Manage Matches ---
@app.route('/dashboard/matches')
@login_required
def manage_matches():
    # ... (Code to list matches remains the same)
    connection = create_connection()
    matches = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT m.id, m.match_time, t1.name as team1, t2.name as team2 
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.id
                JOIN teams t2 ON m.team2_id = t2.id
                ORDER BY m.match_time DESC;
            """
            cursor.execute(query)
            matches = cursor.fetchall()
        except Error as e:
            print(f"Error fetching matches for dashboard: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return render_template('manage_matches.html', matches=matches)


@app.route('/dashboard/matches/add', methods=['GET', 'POST'])
@login_required
def add_match():
    # This function is now more robust.
    if request.method == 'POST':
        connection = None  # Initialize connection to None
        try:
            connection = create_connection()
            if not connection:
                flash("Database connection could not be established.", "danger")
                return redirect(url_for('add_match'))

            # Get form data
            team1_id = request.form['team1_id']
            team2_id = request.form['team2_id']
            championship_id = request.form['championship_id']
            match_time = request.form['match_time']
            description = request.form['description']
            iframe_code = request.form['iframe_code']
            commentator = request.form['commentator']
            
            cursor = connection.cursor()
            query = """
                INSERT INTO matches (team1_id, team2_id, championship_id, match_time, description, iframe_code, commentator)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            cursor.execute(query, (team1_id, team2_id, championship_id, match_time, description, iframe_code, commentator))
            connection.commit()
            flash('Match added successfully!', 'success')
            return redirect(url_for('manage_matches'))

        except Error as e:
            flash(f"An error occurred while adding the match: {e}", "danger")
            # Redirect back to the form so the user can try again
            return redirect(url_for('add_match'))

        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    # For GET request, fetch teams and championships to populate the form
    connection = None
    teams = []
    championships = []
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM teams ORDER BY name;")
            teams = cursor.fetchall()
            cursor.execute("SELECT id, name FROM championships ORDER BY name;")
            championships = cursor.fetchall()
    except Error as e:
        flash(f"Could not load data for the form: {e}", "danger")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            
    return render_template('add_match.html', teams=teams, championships=championships)

# --- Manage Teams & Championships (Similar error handling can be applied) ---
# ... (The rest of the functions like add_team, manage_teams, etc. would benefit from similar robust error handling)


# --- Run Application ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

