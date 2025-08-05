# app.py
# This is the main file for our Flask web application with user authentication.

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
import os
from functools import wraps

# --- Configuration ---
# Create the Flask application instance
app = Flask(__name__)

# IMPORTANT: You must set a secret key for session management to work.
# Change this to a random string.
app.secret_key = 'your_very_secret_random_string_here'

# Database connection details
db_config = {
    'host': 'mysql6013.site4now.net',
    'user': 'abc901_koratv',
    'password': 'omarreda123',
    'database': 'db_abc901_koratv'
}

# --- Database Connection ---
def create_connection():
    """Create a database connection to the MySQL database."""
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection

# --- Decorators ---
def login_required(f):
    """
    Decorator to ensure a user is logged in before accessing a route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

# Home Page: Displays all the matches (Public)
@app.route('/')
def index():
    connection = create_connection()
    matches = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT m.id, m.match_time, t1.name AS team1_name, t1.logo_url AS team1_logo,
                       t2.name AS team2_name, t2.logo_url AS team2_logo, c.name AS championship_name
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.id
                JOIN teams t2 ON m.team2_id = t2.id
                JOIN championships c ON m.championship_id = c.id
                ORDER BY m.match_time DESC;
            """
            cursor.execute(query)
            matches = cursor.fetchall()
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return render_template('index.html', matches=matches)

# Match Detail Page: Displays a single match with its iframe (Public)
@app.route('/match/<int:match_id>')
def match(match_id):
    connection = create_connection()
    match_data = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT m.id, m.match_time, m.description, m.iframe_code, t1.name AS team1_name,
                       t1.logo_url AS team1_logo, t2.name AS team2_name, t2.logo_url AS team2_logo,
                       c.name AS championship_name
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.id
                JOIN teams t2 ON m.team2_id = t2.id
                JOIN championships c ON m.championship_id = c.id
                WHERE m.id = %s;
            """
            cursor.execute(query, (match_id,))
            match_data = cursor.fetchone()
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return render_template('match.html', match=match_data)

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration. Use this to create your first admin user."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hash the password for security
        hashed_password = generate_password_hash(password)
        
        connection = create_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
            connection.commit()
            flash('You have successfully registered! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Username already exists.', 'danger')
        except Error as e:
            flash(f"An error occurred: {e}", 'danger')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logs the user out."""
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

# --- Protected Dashboard Routes ---

@app.route('/dashboard')
@login_required
def dashboard():
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
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return render_template('dashboard.html', matches=matches)

@app.route('/add_match', methods=['GET', 'POST'])
@login_required
def add_match():
    connection = create_connection()
    if request.method == 'POST':
        team1_id = request.form['team1_id']
        team2_id = request.form['team2_id']
        championship_id = request.form['championship_id']
        match_time = request.form['match_time']
        description = request.form['description']
        iframe_code = request.form['iframe_code']

        if connection:
            try:
                cursor = connection.cursor()
                query = """
                    INSERT INTO matches (team1_id, team2_id, championship_id, match_time, description, iframe_code)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """
                cursor.execute(query, (team1_id, team2_id, championship_id, match_time, description, iframe_code))
                connection.commit()
                return redirect(url_for('dashboard'))
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
    
    teams = []
    championships = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM teams ORDER BY name;")
            teams = cursor.fetchall()
            cursor.execute("SELECT id, name FROM championships ORDER BY name;")
            championships = cursor.fetchall()
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
            
    return render_template('add_match.html', teams=teams, championships=championships)

# --- Run the Application ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
