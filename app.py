# app.py
# Final, stable version with all features and bug fixes.

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error, pooling
from functools import wraps
from datetime import datetime, timedelta

# --- Configuration ---
app = Flask(__name__)
app.secret_key = 'your_very_secret_random_string_here_change_me'

# --- Database Connection Pool ---
try:
    db_pool = pooling.MySQLConnectionPool(pool_name="mypool",
                                          pool_size=5,
                                          host='mysql1003.site4now.net',
                                          user='abcbc9_matchss',
                                          password='omarreda123',
                                          database='db_abcbc9_matchss',
                                          charset='utf8mb4'
                                          )
    print("Database connection pool created successfully.")
except Error as e:
    print(f"Error creating connection pool: {e}")
    db_pool = None

def get_db_connection():
    """Gets a connection from the pool."""
    if not db_pool:
        print("Database pool is not available.")
        return None
    try:
        return db_pool.get_connection()
    except Error as e:
        print(f"Error getting connection from pool: {e}")
        return None

# --- Decorators & Helpers ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "info")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_match_status(match_time):
    if not isinstance(match_time, datetime):
        return "غير محدد"
    now = datetime.now()
    match_end_time = match_time + timedelta(minutes=110)
    if match_time > now:
        return "لم تبدأ"
    elif now >= match_time and now <= match_end_time:
        return "جارية الآن"
    else:
        return "انتهت"

# --- Public Routes ---
@app.route('/')
def index():
    connection = None
    cursor = None
    matches_with_status = []
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT m.id, m.match_time, t1.name AS team1_name, t1.logo_url AS team1_logo,
                       t2.name AS team2_name, t2.logo_url AS team2_logo, c.name AS championship_name,
                       m.commentator
                FROM matches m
                LEFT JOIN teams t1 ON m.team1_id = t1.id
                LEFT JOIN teams t2 ON m.team2_id = t2.id
                LEFT JOIN championships c ON m.championship_id = c.id
                ORDER BY m.match_time ASC;
            """
            cursor.execute(query)
            matches = cursor.fetchall()
            for match in matches:
                match['status'] = get_match_status(match.get('match_time'))
                matches_with_status.append(match)
    except Exception as e:
        print(f"Error in index route: {e}")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
    return render_template('index.html', matches=matches_with_status, current_year=datetime.now().year)

@app.route('/match/<int:match_id>')
def match(match_id):
    connection = None
    cursor = None
    match_data = None
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT m.id, m.match_time, m.description, m.iframe_code, t1.name AS team1_name,
                       t1.logo_url AS team1_logo, t2.name AS team2_name, t2.logo_url AS team2_logo,
                       c.name AS championship_name, m.commentator
                FROM matches m
                LEFT JOIN teams t1 ON m.team1_id = t1.id
                LEFT JOIN teams t2 ON m.team2_id = t2.id
                LEFT JOIN championships c ON m.championship_id = c.id
                WHERE m.id = %s;
            """, (match_id,))
            match_data = cursor.fetchone()
            if match_data:
                 match_data['status'] = get_match_status(match_data.get('match_time'))
    except Exception as e:
        print(f"Error in match route: {e}")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
    return render_template('match.html', match=match_data, current_year=datetime.now().year)

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        connection = None
        cursor = None
        user = None
        try:
            connection = get_db_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
        except Exception as e:
            print(f"Error in login route: {e}")
            flash("A server error occurred. Please try again later.", "danger")
        finally:
            if cursor: cursor.close()
            if connection: connection.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Please check your login details and try again.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
                connection.commit()
                flash('You have successfully registered! Please log in.', 'success')
                return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Username already exists.', 'danger')
        except Exception as e:
            print(f"Error in register route: {e}")
            flash(f"An error occurred: {e}", "danger")
        finally:
            if cursor: cursor.close()
            if connection: connection.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# --- Protected Dashboard Routes ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- Manage Matches ---
@app.route('/dashboard/matches')
@login_required
def manage_matches():
    connection = None
    cursor = None
    matches = []
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT m.id, m.match_time, t1.name as team1, t2.name as team2 
                FROM matches m
                LEFT JOIN teams t1 ON m.team1_id = t1.id
                LEFT JOIN teams t2 ON m.team2_id = t2.id
                ORDER BY m.match_time DESC;
            """
            cursor.execute(query)
            matches = cursor.fetchall()
    except Exception as e:
        print(f"Error in manage_matches route: {e}")
        flash(f"Error fetching matches: {e}", "danger")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
    return render_template('manage_matches.html', matches=matches)

@app.route('/dashboard/matches/add', methods=['GET', 'POST'])
@login_required
def add_match():
    connection = None
    cursor = None
    if request.method == 'POST':
        try:
            connection = get_db_connection()
            if not connection:
                flash("Database connection could not be established.", "danger")
                return redirect(url_for('add_match'))

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
        except Exception as e:
            print(f"Error in add_match (POST) route: {e}")
            flash(f"An error occurred while adding the match: {e}", "danger")
            return redirect(url_for('add_match'))
        finally:
            if cursor: cursor.close()
            if connection: connection.close()

    # For GET request
    teams = []
    championships = []
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM teams ORDER BY name;")
            teams = cursor.fetchall()
            cursor.execute("SELECT id, name FROM championships ORDER BY name;")
            championships = cursor.fetchall()
    except Exception as e:
        print(f"Error in add_match (GET) route: {e}")
        flash(f"Could not load data for the form: {e}", "danger")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
    return render_template('add_match.html', teams=teams, championships=championships)

@app.route('/dashboard/matches/edit/<int:match_id>', methods=['GET', 'POST'])
@login_required
def edit_match(match_id):
    connection = None
    cursor = None
    
    if request.method == 'POST':
        try:
            connection = get_db_connection()
            if not connection:
                flash("Database connection failed.", "danger")
                return redirect(url_for('edit_match', match_id=match_id))

            team1_id = request.form['team1_id']
            team2_id = request.form['team2_id']
            championship_id = request.form['championship_id']
            match_time = request.form['match_time']
            description = request.form['description']
            iframe_code = request.form['iframe_code']
            commentator = request.form['commentator']

            cursor = connection.cursor()
            query = """
                UPDATE matches SET team1_id=%s, team2_id=%s, championship_id=%s, match_time=%s, 
                description=%s, iframe_code=%s, commentator=%s WHERE id=%s
            """
            cursor.execute(query, (team1_id, team2_id, championship_id, match_time, description, iframe_code, commentator, match_id))
            connection.commit()
            flash('Match updated successfully!', 'success')
            return redirect(url_for('manage_matches'))
        except Exception as e:
            print(f"Error in edit_match (POST) route: {e}")
            flash(f"An error occurred while updating the match: {e}", "danger")
            return redirect(url_for('edit_match', match_id=match_id))
        finally:
            if cursor: cursor.close()
            if connection: connection.close()

    # For GET request
    match = None
    teams = []
    championships = []
    try:
        connection = get_db_connection()
        if not connection:
            flash("Database connection failed.", "danger")
            return redirect(url_for('manage_matches'))

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM matches WHERE id = %s", (match_id,))
        match = cursor.fetchone()
        
        if not match:
            flash("Match not found!", "danger")
            return redirect(url_for('manage_matches'))

        cursor.execute("SELECT id, name FROM teams ORDER BY name;")
        teams = cursor.fetchall()
        cursor.execute("SELECT id, name FROM championships ORDER BY name;")
        championships = cursor.fetchall()

        if match.get('match_time') and isinstance(match.get('match_time'), datetime):
            match['match_time_str'] = match['match_time'].strftime('%Y-%m-%dT%H:%M')

    except Exception as e:
        print(f"Error in edit_match (GET) route: {e}")
        flash(f"Could not load data for editing: {e}", "danger")
        return redirect(url_for('manage_matches'))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
        
    return render_template('edit_match.html', match=match, teams=teams, championships=championships)

@app.route('/dashboard/matches/delete/<int:match_id>', methods=['POST'])
@login_required
def delete_match(match_id):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM matches WHERE id = %s", (match_id,))
            connection.commit()
            flash("Match deleted successfully.", "success")
    except Exception as e:
        print(f"Error in delete_match route: {e}")
        flash(f"Error deleting match: {e}", "danger")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
    return redirect(url_for('manage_matches'))

# --- Manage Teams & Championships ---
@app.route('/dashboard/teams')
@login_required
def manage_teams():
    connection = None
    cursor = None
    teams = []
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name, logo_url FROM teams ORDER BY name;")
            teams = cursor.fetchall()
    except Exception as e:
        print(f"Error in manage_teams route: {e}")
        flash(f"Error fetching teams: {e}", "danger")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
    return render_template('manage_teams.html', teams=teams)

@app.route('/dashboard/teams/add', methods=['GET', 'POST'])
@login_required
def add_team():
    if request.method == 'POST':
        team_name = request.form['team_name']
        logo_url = request.form['logo_url']
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO teams (name, logo_url) VALUES (%s, %s)", (team_name, logo_url))
                connection.commit()
                flash(f"Team '{team_name}' added successfully!", "success")
        except mysql.connector.IntegrityError:
            flash(f"Team '{team_name}' already exists.", "danger")
        except Exception as e:
            print(f"Error in add_team route: {e}")
            flash(f"An error occurred: {e}", "danger")
        finally:
            if cursor: cursor.close()
            if connection: connection.close()
        return redirect(url_for('manage_teams'))
    return render_template('add_team.html')

@app.route('/dashboard/championships')
@login_required
def manage_championships():
    connection = None
    cursor = None
    championships = []
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM championships ORDER BY name;")
            championships = cursor.fetchall()
    except Exception as e:
        print(f"Error in manage_championships route: {e}")
        flash(f"Error fetching championships: {e}", "danger")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
    return render_template('manage_championships.html', championships=championships)

@app.route('/dashboard/championships/add', methods=['GET', 'POST'])
@login_required
def add_championship():
    if request.method == 'POST':
        championship_name = request.form['championship_name']
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO championships (name) VALUES (%s)", (championship_name,))
                connection.commit()
                flash(f"Championship '{championship_name}' added successfully!", "success")
        except mysql.connector.IntegrityError:
            flash(f"Championship '{championship_name}' already exists.", "danger")
        except Exception as e:
            print(f"Error in add_championship route: {e}")
            flash(f"An error occurred: {e}", "danger")
        finally:
            if cursor: cursor.close()
            if connection: connection.close()
        return redirect(url_for('manage_championships'))
    return render_template('add_championship.html')

# --- Run Application ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
