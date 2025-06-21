# 🧱 Core Flask & Extensions
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for, session
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message

# 🗃️ Database
import mysql.connector

# 📅 Scheduling & Time
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
import parsedatetime as pdt
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# 📊 Analytics & Plots
import matplotlib
matplotlib.use('Agg')  # For non-GUI environments
import matplotlib.pyplot as plt

# 🧠 AI & Prediction
from AI.suggestor import suggest_task_with_ml

# 🔐 Auth & Google API
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# 🛠️ Utilities
import os
import math
import re
import io
import base64
import pickle
import logging

logging.basicConfig(level=logging.INFO)

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'db_name' 
}

# Flask-Bcrypt for Password Hashing
bcrypt = Bcrypt(app)

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'
# You can just use a plain email or a tuple (Name, Email) if you want a display name
# Example: 'your-email@gmail.com' OR ('TaskForge', 'your-email@gmail.com')
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'

mail = Mail(app)

scheduler = BackgroundScheduler()

# Shows the dashboard
@app.route('/')
def dashboard():
    return render_template('dashboard.html')
    
# Main page
@app.route('/index')
def index():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    username = user_data['username'] if user_data else 'Unknown'

    cursor.execute("""
        SELECT * FROM tasks 
        WHERE user_id = %s AND status = 0
        ORDER BY 
            CASE 
                WHEN priority = 'Urgent' THEN 1
                WHEN priority = 'High' THEN 2
                WHEN priority = 'Medium' THEN 3
                WHEN priority = 'Low' THEN 4
                ELSE 5
            END,
            due_datetime ASC
    """, (user_id,))
    tasks = cursor.fetchall()

    # Pagination params for personal tasks
    page = int(request.args.get('page', 1))
    per_page = 5
    offset = (page - 1) * per_page

    tasks_page = get_tasks_paginated(user_id, per_page, offset)
    total_tasks = get_total_task_count(user_id)
    total_pages = math.ceil(total_tasks / per_page)

    # Pagination params for shared tasks
    shared_page = int(request.args.get('shared_page', 1))
    shared_per_page = 5
    shared_offset = (shared_page - 1) * shared_per_page

    cursor.execute("""
        SELECT st.* FROM shared_tasks st
        JOIN shared_with_users swu ON st.id = swu.shared_task_id
        WHERE swu.user_id = %s
        ORDER BY st.id DESC
        LIMIT %s OFFSET %s
    """, (user_id, shared_per_page, shared_offset))
    shared_tasks = cursor.fetchall()

    for task in shared_tasks:
        cursor.execute("""
            SELECT u.username FROM users u
            JOIN shared_with_users swu ON u.id = swu.user_id
            WHERE swu.shared_task_id = %s AND u.id != %s
        """, (task['id'], user_id))
        shared_users = cursor.fetchall()
        task['shared_with'] = [user['username'] for user in shared_users]

    cursor.execute("""
        SELECT COUNT(*) AS total FROM shared_tasks st
        JOIN shared_with_users swu ON st.id = swu.shared_task_id
        WHERE swu.user_id = %s
    """, (user_id,))
    total_shared = cursor.fetchone()['total']
    shared_total_pages = math.ceil(total_shared / shared_per_page)

    cursor.execute("""
        SELECT DISTINCT category 
        FROM tasks 
        WHERE user_id = %s AND category IS NOT NULL AND category != ''
    """, (user_id,))
    user_categories = [row['category'] for row in cursor.fetchall()]

    suggestions = suggest_task_with_ml(user_id, cursor)

    calendar_linked = os.path.exists('token.pkl')

    cursor.close()
    connection.close()

    return render_template(
        'index.html',
        tasks=tasks, username=username, user_categories=user_categories,
        calendar_linked=calendar_linked, suggestions=suggestions, page=page,
        total_pages=total_pages, tasks_page=tasks_page, shared_tasks=shared_tasks,
        shared_page=shared_page, shared_total_pages=shared_total_pages,
    )

# Gets only a few tasks at a time for the user (like page-by-page)
def get_tasks_paginated(user_id, limit, offset):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM tasks WHERE user_id = %s ORDER BY id DESC LIMIT %s OFFSET %s",
        (user_id, limit, offset)
    )
    tasks = cursor.fetchall()
    cursor.close()
    connection.close()
    return tasks

# Returns the total number of tasks (used for pagination/count display)
def get_total_task_count(user_id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (user_id,))
    total = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    return total
    
# Fetches tasks that have been shared with the other user
def get_shared_tasks(user_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT st.* FROM shared_tasks st
        JOIN shared_with_users swu ON st.id = swu.shared_task_id
        WHERE swu.user_id = %s
        ORDER BY st.id DESC
    """, (user_id,))
    shared_tasks = cursor.fetchall()

    # Fetch usernames with whom the task is shared (excluding the current user)
    for task in shared_tasks:
        cursor.execute("""
            SELECT u.username FROM users u
            JOIN shared_with_users swu ON u.id = swu.user_id
            WHERE swu.shared_task_id = %s AND u.id != %s
        """, (task['id'], user_id))
        shared_users = cursor.fetchall()
        task['shared_with'] = [user['username'] for user in shared_users]

    cursor.close()
    conn.close()
    return shared_tasks

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                           (username, email, hashed_password))
            connection.commit()

            # Send a Welcome Email
            msg = Message('Welcome to TaskForge!', recipients=[email])
            msg.body = 'Thank you for registering! Log in now and start managing your tasks.'
            mail.send(msg)

            flash('Registration successful! Check your email for confirmation.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Username or email already exists. Please use a different one.', 'danger')
        finally:
            cursor.close()
            connection.close()

    return render_template('register.html')

# To send in-app reminders
def send_due_reminders():
    with app.app_context():
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        now = datetime.now()
        print(f"[{now}] Checking for due tasks...")

        cursor.execute("""
            SELECT t.id, t.description, t.reminder_datetime, u.id as user_id, u.email 
            FROM tasks t
            JOIN users u ON t.user_id = u.id
            WHERE t.reminder_datetime IS NOT NULL AND t.reminder_datetime <= %s AND t.status = 0
        """, (now,))
        tasks = cursor.fetchall()

        print(f"Found {len(tasks)} due task(s).")

        for task in tasks:
            # ✅ Prevent duplicate notifications
            cursor.execute("""
                SELECT COUNT(*) as count FROM notifications 
                WHERE user_id = %s AND message = %s AND is_read = 0
            """, (task['user_id'], f"⏰ {task['description']} is due!"))
            exists = cursor.fetchone()['count']

            if exists == 0:
                # Insert in-app notification
                cursor.execute("""
                    INSERT INTO notifications (user_id, message, created_at, is_read)
                    VALUES (%s, %s, %s, 0)
                """, (task['user_id'], f"⏰ {task['description']} is due!", now))

                # Send email reminder
                msg = Message("⏰ Task Reminder!",
                              sender=("TaskForge", "taskforge971@gmail.com"),
                              recipients=[task['email']])
                msg.body = f"Reminder: You have a task - {task['description']}."
                mail.send(msg)

                # Clear reminder to avoid repeat
                cursor.execute("UPDATE tasks SET reminder_datetime = NULL WHERE id = %s", (task['id'],))

        connection.commit()
        cursor.close()
        connection.close()

# For login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user and bcrypt.check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'danger')

        finally:
            cursor.close()
            connection.close()

    return render_template('login.html')

# Forgot Password Route
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('forgot_password'))

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user:
                hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_password, username))
                connection.commit()

                flash('Password reset successful! You can now log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Username not found!', 'danger')

        finally:
            cursor.close()
            connection.close()

    return render_template('forgot_password.html')

#Logout Route
@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('dashboard'))
    
# Add tasks
@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if 'user_id' not in session:
        flash('Please log in to add a task.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        description = request.form['description']
        due_datetime = request.form.get('due_datetime', None)
        category = request.form.get('category', 'General')
        priority = request.form.get('priority', 'Medium')
        reminder_str = request.form.get('reminder_datetime') 
        recurring = request.form.get('recurring') or None
        user_id = session['user_id']

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO tasks (user_id, description, due_datetime, category, priority, reminder_datetime, recurring) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                (user_id, description, due_datetime, category, priority, reminder_str, recurring)
            )
            connection.commit()
            flash('Task added successfully!', 'success')

            suggested_time = suggest_task_time()
            if os.path.exists('token.pkl'):
                add_to_google_calendar(description, suggested_time)
            else:
                flash("Calendar not linked! Please connect Google Calendar first.", "warning")
                
        except Exception as e:
            flash(f"Error adding task: {e}", 'danger')
        finally:
            cursor.close()
            connection.close()
            
        return redirect(url_for('index'))

    return render_template('index.html')
    
# For category page
@app.route('/category/<string:category>')
def category(category):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM tasks 
        WHERE user_id = %s AND category = %s AND status = 0
    """, (user_id, category))
    tasks = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('category_tasks.html', tasks=tasks, category=category)

#Daily add section
@app.route('/add_daily_task', methods=['POST', 'GET'])
def add_daily_task():
    if 'user_id' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))

    description = request.form.get('description')
    if not description:
        flash("Task description is required.", "danger")
        return redirect(url_for('index'))

    user_id = session['user_id']
    
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO daily_tasks (user_id, description) VALUES (%s, %s)",
        (user_id, description)
    )
    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('show_daily_tasks'))

# Show daily tasks
@app.route('/show_daily_tasks')
def show_daily_tasks():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    #  Get incomplete daily tasks
    cursor.execute("SELECT * FROM daily_tasks WHERE user_id = %s AND status = 0", (user_id,))
    daily_tasks = cursor.fetchall()

    #  Count total daily tasks
    cursor.execute("SELECT COUNT(*) AS count FROM daily_tasks WHERE user_id = %s", (user_id,))
    total_tasks_today = cursor.fetchone()['count'] or 0

    #  Count completed daily tasks
    cursor.execute("SELECT COUNT(*) AS count FROM daily_tasks WHERE user_id = %s AND status = 1", (user_id,))
    completed_today = cursor.fetchone()['count'] or 0

    #  Calculate progress
    progress_percent = int((completed_today / total_tasks_today) * 100) if total_tasks_today else 0
    pie_chart = create_pie_chart(progress_percent)

    cursor.close()
    connection.close()
    
    return render_template(
        'daily_tasks.html',
        daily_tasks=daily_tasks,
        total_tasks_today=total_tasks_today,
        completed_today=completed_today,
        progress_percent=progress_percent,
        pie_chart=pie_chart
    )

def clear_daily_tasks():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM daily_tasks")
    connection.commit()
    cursor.close()
    connection.close()
    print("✅ Daily tasks cleared at midnight.")
    logging.info(f"[{datetime.now()}] ✅ Cleared daily_tasks table.")

# Delete tasks
@app.route('/delete_task/<int:task_id>', methods=['POST', 'GET'])
def delete_task(task_id):
    user_id = session.get('user_id')

    if not user_id:
        flash("You must be logged in to delete a task.", "danger")
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM tasks WHERE id = %s AND user_id = %s", (task_id, user_id))
    task = cursor.fetchone()

    if task:
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        connection.commit()
        flash("Task deleted successfully from tasks!", "success")
        cursor.close()
        connection.close()
        return redirect(url_for('index'))

    flash("Task not found or you don't have permission to delete it.", "danger")
    cursor.close()
    connection.close()
    return redirect(url_for('index'))

# Edit tasks
@app.route('/edit-task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    if 'user_id' not in session:
        flash("You must be logged in to edit tasks.", "danger")
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        description = request.form['description']
        due_datetime = request.form['due_datetime']
        status = request.form.get('status')
        category = request.form.get('category')
        priority = request.form.get('priority')
        recurring = request.form.get('recurring')
        reminder_datetime = request.form.get('reminder_datetime')
        last_created = request.form.get('last_created')

        update_query = """
            UPDATE tasks SET 
                description = %s,
                due_datetime = %s,
                status = %s,
                category = %s,
                priority = %s,
                recurring = %s,
                reminder_datetime = %s,
                last_created = %s
            WHERE id = %s AND user_id = %s
        """
        cursor.execute(update_query, (
            description, due_datetime, status, category, priority,
            recurring, reminder_datetime, last_created, task_id, session['user_id']
        ))
        connection.commit()
        cursor.close()
        connection.close()
        flash("Task updated successfully!", "success")
        return redirect(url_for('index'))

    # fetch all tasks + the task to edit
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s", (session['user_id'],))
    all_tasks = cursor.fetchall()

    cursor.execute("SELECT * FROM tasks WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    task_to_edit = cursor.fetchone()

    cursor.close()
    connection.close()

    if not task_to_edit:
        flash("Task not found or you don't have permission to edit it.", "danger")
        return redirect(url_for('index'))

    return render_template('index.html', tasks=all_tasks, edit_task=task_to_edit)

# Mark tasks as completed
@app.route('/mark-completed/<int:task_id>', methods=['POST', 'GET'])
def mark_completed(task_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    completed_at = datetime.now()

    cursor.execute('UPDATE tasks SET status = 1, completed_at = %s WHERE id = %s', (completed_at, task_id))
    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for('index'))

# Mark daily tasks completed
@app.route('/daily_mark_completed/<int:task_id>', methods=['POST'])
def daily_mark_completed(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute("UPDATE daily_tasks SET status = TRUE WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('show_daily_tasks'))

# Delete daily tasks
@app.route('/delete_daily_task/<int:task_id>', methods=['GET', 'POST'])
def delete_daily_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM daily_tasks WHERE id = %s AND user_id = %s", (task_id, user_id))
    task = cursor.fetchone()

    if task:
        cursor.execute("DELETE FROM daily_tasks WHERE id = %s", (task_id,))
        connection.commit()
        flash("Task deleted successfully from daily_tasks!", "success")
    else:
        flash("Task not found or already deleted.", "danger")

    cursor.close()
    connection.close()
    return redirect(url_for('show_daily_tasks'))

# Show completed tasks
@app.route('/completed_tasks', methods=['POST', 'GET'])
def completed_tasks():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))  

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Fetch completed regular tasks
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s AND status = 1", (user_id,))
    completed_tasks = cursor.fetchall()

    # Fetch completed daily tasks
    cursor.execute("SELECT * FROM daily_tasks WHERE user_id = %s AND status = 1", (user_id,))
    daily_completed_tasks = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('completed_tasks.html', tasks=completed_tasks, daily_completed_tasks=daily_completed_tasks)

# Pie chart
def create_pie_chart(progress_percent):
    remaining = 100 - progress_percent
    colors = ['#4caf50', '#e0e0e0']

    # Pie chart
    fig, ax = plt.subplots(figsize=(3, 3), dpi=100)
    ax.pie(
        [progress_percent, remaining],
        colors=colors,
        startangle=90,
        wedgeprops={'width': 0.4},
    )
    ax.axis('equal')

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    buf.seek(0)
    chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()

    return chart_base64

# Create Shared tasks route
@app.route('/create_shared_task', methods=['POST'])
def create_shared_task():
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    due_time = request.form.get('due_time')
    current_user_id = session.get("user_id")
    user_ids = request.form.getlist('shared_with[]') 
    priority = request.form.get('priority', 'Medium')
    if not description:
        return "Description is required", 400

    if str(current_user_id) not in user_ids:
        user_ids.append(str(current_user_id))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("INSERT INTO shared_tasks (description, due_date, due_time, priority) VALUES (%s, %s, %s, %s)", (description, due_date or None, due_time or None, priority))

    task_id = cursor.lastrowid 

    for uid in user_ids:
        cursor.execute("INSERT INTO shared_with_users (shared_task_id, user_id) VALUES (%s, %s)", (task_id, uid))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('shared_tasks'))

# Show shared tasks
@app.route('/shared_tasks', methods=['POST', 'GET'])
def shared_tasks():
    user_id = session.get("user_id")
    show_popup = request.args.get("popup") == "1"
    search_query = request.args.get("search", "").strip()

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE id != %s", (user_id,))
    all_users = cursor.fetchall()
    
    cursor.execute("""
        SELECT st.* FROM shared_tasks st
        JOIN shared_with_users swu ON st.id = swu.shared_task_id
        WHERE swu.user_id = %s
        ORDER BY st.id DESC
    """, (user_id,))
    shared_tasks = cursor.fetchall()

    for task in shared_tasks:
        cursor.execute("""
            SELECT u.username FROM users u
            JOIN shared_with_users swu ON u.id = swu.user_id
            WHERE swu.shared_task_id = %s AND u.id != %s
        """, (task['id'], user_id))  # exclude current user

        shared_users = cursor.fetchall()
        task['shared_with'] = [user['username'] for user in shared_users]

    cursor.close()
    conn.close()

    return render_template("shared_tasks.html",all_users=all_users,shared_tasks=shared_tasks,
        current_user_id=user_id,show_popup=show_popup,search_query=search_query)

# To search user for share tasks
@app.route('/search_users')
def search_users():
    query = request.args.get('query')
    user_id = session.get('user_id')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username FROM users WHERE username LIKE %s AND id != %s LIMIT 5", (f"%{query}%", user_id))
    users = cursor.fetchall()
    conn.close()

    return jsonify(users)

# Show completed shared tasks
@app.route('/complete_shared_task/<int:task_id>', methods=['POST'])
def complete_shared_task(task_id):
    user_id = session.get("user_id")
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("UPDATE shared_tasks SET status = 1 WHERE id = %s", (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('shared_tasks'))

# Delete shared tasks
@app.route('/delete_shared_task/<int:task_id>', methods=['POST'])
def delete_shared_task(task_id):
    user_id = session.get("user_id")
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM shared_with_users 
        WHERE shared_task_id = %s AND user_id = %s
    """, (task_id, user_id))

    if cursor.fetchone():
        cursor.execute("""
            DELETE FROM shared_with_users 
            WHERE shared_task_id = %s AND user_id = %s
        """, (task_id, user_id))
        conn.commit()
        
        cursor.execute("""
            SELECT COUNT(*) FROM shared_with_users 
            WHERE shared_task_id = %s
        """, (task_id,))
        count = cursor.fetchone()[0]

        if count == 0:
            cursor.execute("DELETE FROM shared_tasks WHERE id = %s", (task_id,))
            conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for('shared_tasks'))

# Flask route to show suggestions
@app.route('/suggest')
def show_suggestion():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please login to get suggestions.", "warning")
        return redirect(url_for("login"))

    conn = mysql.connector.connect(**db_config)
    try:
        cursor = conn.cursor(dictionary=True)
        suggestions = suggest_task_with_ml(user_id, cursor)
    finally:
        cursor.close()
        conn.close()

    return render_template("index.html", suggestions=suggestions)

# Flask route to add suggested task
@app.route('/add_suggested_task', methods=['POST'])
def add_suggested_task():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to add tasks.", "danger")
        return redirect(url_for('login'))

    description = request.form.get('description')
    category = request.form.get('category', 'General')
    priority = request.form.get('priority', 'Medium')
    due_datetime = request.form.get('due_datetime')

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO tasks (user_id, description, category, priority, due_datetime, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, description, category, priority, due_datetime, 0))

    connection.commit()
    cursor.close()
    connection.close()

    flash("Suggested task added!", "success")
    return redirect(url_for('index'))

cal = pdt.Calendar()

# Process the voice of the user
@app.route('/process-voice', methods=['POST'])
def process_voice():
    data = request.get_json()
    transcript = data.get('transcript', '').lower()

    description = ""
    category = "General"
    priority = "Medium"
    due_datetime = None
    reminder_datetime = None
    recurring = None

    # Extract description (mandatory)
    task_match = re.search(r'add a task (.+?)(?: in category| with priority| with due| with recurring|$)', transcript)
    if task_match:
        description = task_match.group(1).strip()

    # Category (optional)
    category_match = re.search(r'in category (.+?)(?: with priority| with due| with recurring|$)', transcript)
    if category_match:
        category = category_match.group(1).strip()

    # Priority (optional)
    priority_match = re.search(r'with priority (.+?)(?: with due| with recurring|$)', transcript)
    if priority_match:
        priority = priority_match.group(1).strip().capitalize()

    # Due date (optional)
    due_match = re.search(r'with due (.+?)(?: with recurring|$)', transcript)
    if due_match:
        due_str = due_match.group(1).strip()
        due_datetime = None
        try:
            due_datetime = date_parser.parse(due_str, fuzzy=True)
            if due_datetime.time() == datetime.min.time():
                due_datetime = due_datetime.replace(hour=18, minute=0)  # default 6 PM
        except Exception:
            time_struct, parse_status = cal.parse(due_str)
            if parse_status:
                due_datetime = datetime(*time_struct[:6])

    # Reminder date (optional)
    reminder_match = re.search(r'with reminder (.+?)(?: recurring|$)', transcript)
    if reminder_match:
        reminder_str = reminder_match.group(1).strip()
        reminder_datetime = None
        try:
            reminder_datetime = date_parser.parse(reminder_str, fuzzy=True)
            if reminder_datetime.time() == datetime.min.time():
                reminder_datetime = reminder_datetime.replace(hour=9, minute=0)  # default 9 AM reminder
        except Exception:
            time_struct, parse_status = cal.parse(reminder_str)
            if parse_status:
                reminder_datetime = datetime(*time_struct[:6])

    # Recurring (optional)
    recurring_match = re.search(r'recurring (daily|weekly|monthly)', transcript)
    if recurring_match:
        recurring = recurring_match.group(1).lower()

    # Validate description
    if not description:
        return jsonify({"status": "error", "message": "Description missing"})
        
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO tasks (user_id, description, category, priority, due_datetime, reminder_datetime, recurring, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
    """, (user_id, description, category, priority, due_datetime, reminder_datetime, recurring))
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({"status": "ok"})

# checking if there are any task due to send reminders
def check_and_send_reminders():
    now = datetime.now()
    soon = now + timedelta(minutes=5)

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM tasks
        WHERE reminder_datetime BETWEEN %s AND %s AND status = 0
    """, (now, soon))

    tasks = cursor.fetchall()
    cursor.close()
    connection.close()

    for task in tasks:
        print(f"Reminder: Task '{task['description']}' is due soon!")

# Handles recurring tasks
def handle_recurring_tasks():
    with app.app_context():
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        now = datetime.now()

        # Get all due recurring tasks
        cursor.execute("""
            SELECT * FROM tasks
            WHERE recurring IS NOT NULL
            AND due_datetime IS NOT NULL
            AND due_datetime <= %s
            AND status = 0
        """, (now,))
        tasks = cursor.fetchall()

        for task in tasks:
            new_due = task['due_datetime']
            if task['recurring'] == 'daily':
                new_due += relativedelta(days=1)
            elif task['recurring'] == 'weekly':
                new_due += relativedelta(weeks=1)
            elif task['recurring'] == 'monthly':
                new_due += relativedelta(months=1)
            else:
                continue
                
            cursor.execute("""
                INSERT INTO tasks (user_id, description, category, priority, due_datetime, recurring, status)
                VALUES (%s, %s, %s, %s, %s, %s, 0)
            """, (task['user_id'], task['description'], task['category'], task['priority'], new_due, task['recurring']))

        connection.commit()
        cursor.close()
        connection.close()

        logging.info(f"[{datetime.now()}] 🔁 Recurring tasks processed.")

# Resets daily tasks after 12
def daily_reset():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Get last reset date
    cursor.execute("SELECT last_reset_date FROM system_state WHERE id = 1")
    row = cursor.fetchone()
    last_reset = row['last_reset_date']
    today = datetime.now().date()

    if last_reset != today:
        clear_daily_tasks()
        handle_recurring_tasks() 
        # Update last reset
        cursor.execute("UPDATE system_state SET last_reset_date = %s WHERE id = 1", (today,))
        connection.commit()

    cursor.close()
    connection.close()

# To get reminders
@app.route('/get_reminders')
def get_reminders():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, message, created_at 
        FROM notifications 
        WHERE user_id = %s AND is_read = 0 
        ORDER BY created_at DESC
    """, (user_id,))
    reminders = cursor.fetchall()

    # Convert datetime to ISO format
    for r in reminders:
        r['created_at'] = r['created_at'].isoformat()

    cursor.close()
    connection.close()

    return jsonify(reminders)

# Marking notifications
@app.route('/mark_notifications_read', methods=['POST'])
def mark_notifications_read():
    user_id = session.get('user_id')
    if not user_id:
        return '', 401

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = %s AND is_read = 0
    """, (user_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return '', 204

with app.app_context():
    # Clear daily tasks at midnight
    scheduler.add_job(
        clear_daily_tasks,
        CronTrigger(hour=0, minute=0),
        id="clear_daily",
        replace_existing=True
    )

    # Handles recurring tasks at midnight
    scheduler.add_job(
        handle_recurring_tasks,
        CronTrigger(hour=0, minute=0),
        id="recurring_tasks",
        replace_existing=True
    )

    # Check and send due reminders every 1 minute
    scheduler.add_job(
        send_due_reminders,
        IntervalTrigger(minutes=1),
        id="due_reminders",
        replace_existing=True
    )

    scheduler.start()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # Allows OAuth to work over HTTP (for development only, not secure for production)

SCOPES = ['https://www.googleapis.com/auth/calendar.events'] # Permission scope to create and manage calendar events using Google Calendar API
CLIENT_SECRETS_FILE = 'google_calendar_credentials.json' # Path to your Google OAuth 2.0 credentials JSON file

# Sends the user to Google to ask for permission to access their account.
@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['state'] = state
    return redirect(authorization_url)
    
# After Google gives access, this gets the info and sends user back.
@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    with open('token.pkl', 'wb') as token_file:
        pickle.dump(credentials, token_file)

    return redirect(url_for('index'))
    
# Syncing with google calender
def add_to_google_calendar(summary, start_time):
    try:
        with open('token.pkl', 'rb') as token:
            creds = pickle.load(token)

        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': (datetime.fromisoformat(start_time) + timedelta(hours=1)).isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"✅ Task added to Google Calendar: {created_event.get('htmlLink')}")
        return True
    except Exception as e:
        print("❌ Google Calendar error:", e)
        return False
        
# Suggests a task time that's 1 hour from now
def suggest_task_time():
    now = datetime.now()
    suggested_time = now + timedelta(hours=1)
    return suggested_time.strftime('%Y-%m-%dT%H:%M:%S')
    
# Predicts the next task value based on previous progress
def simple_task_prediction(data):
    days = list(data.values())
    diffs = [days[i+1] - days[i] for i in range(len(days)-1)]
    if len(diffs) == 0:
        return days[-1] if days else 0
    avg_change = sum(diffs) / len(diffs)
    predicted = max(0, days[-1] + avg_change)
    return round(predicted)

# Get weekly statistics
def get_weekly_stats():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    today = datetime.now()
    seven_days_ago = today - timedelta(days=6)

    data = {}
    total_completed = 0
    total_high_priority = 0
    total_tasks = 0

    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        formatted_day = day.strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT description, priority, completed_at
            FROM tasks
            WHERE DATE(completed_at) = %s AND status = 1
        ''', (formatted_day,))
        tasks = cursor.fetchall()

        count = len(tasks)
        high_priority_count = sum(1 for task in tasks if task['priority'] == 'High')

        total_completed += count
        total_high_priority += high_priority_count
        total_tasks += count

        data[day.strftime('%A')] = tasks

    cursor.close()
    connection.close()

    avg = total_completed / 7 if total_completed else 0
    insight = []

    if total_completed == 0:
        insight.append("You didn’t complete any tasks this week. Let’s aim higher!")
    else:
        insight.append(f"You completed a total of {total_completed} tasks this week.")
        insight.append(f"Your daily average is {avg} tasks.")

        if data:
            max_day = max(data, key=lambda d: len(data[d]))
            min_day = min(data, key=lambda d: len(data[d]))

            if max_day and len(data[max_day]) > avg:
                insight.append(f"You were most productive on {max_day}.")

            if min_day and len(data[min_day]) < avg / 2:
                insight.append(f"Your {min_day}s are less productive; consider boosting focus that day.")

            weekend_days = ['Saturday', 'Sunday']
            weekend_tasks = sum(len(data.get(day, [])) for day in weekend_days)
            if weekend_tasks < avg * 2:
                insight.append("Try scheduling lighter tasks on weekends to stay consistent.")

            if max_day and len(data[max_day]) > avg * 1.5:
                insight.append(f"Great job on {max_day}! Schedule tough tasks on your productive days.")

    predicted_tasks = simple_task_prediction({day: len(tasks) for day, tasks in data.items()})
    insight.append(f"Based on your recent trend, you might complete about {predicted_tasks} tasks tomorrow.")

    if total_tasks > 0:
        high_priority_ratio = total_high_priority / total_tasks
        if high_priority_ratio < 0.3:
            insight.append("You completed fewer high-priority tasks this week; try tackling them first.")

    return data, insight

# Shows weekly analytics
@app.route('/weekly-analytics')
def weekly_analytics():
    data, insights = get_weekly_stats()
    return render_template('weekly_analytics.html', data=data, data_json=data, insights=insights)

if __name__ == "__main__":
    daily_reset()
    app.run(debug=True, use_reloader=False) 
