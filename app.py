import os
import time
import datetime
import random
import sqlite3
import zipfile
import io
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "enterprise_saas_super_secret_key_2026"

# জিমেইল ওটিপি পাঠানোর কনফিগারেশন (আপনার জিমেইল ও অ্যাপ পাসওয়ার্ড এখানে সেট করুন)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your_email@gmail.com"  # আপনার জিমেইল লিখুন
SENDER_PASSWORD = "your_app_password"   # জিমেইলের App Password লিখুন

# ডাটাবেজ ইনিশিয়ালাইজেশন
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # ইউজার টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            status TEXT DEFAULT 'Active',
            otp TEXT
        )
    ''')
    # রিপোর্ট বা টাস্ক টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            date TEXT,
            type TEXT,
            target TEXT,
            status TEXT,
            log TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ডিফল্ট অ্যাডমিন নিশ্চিত করা
def check_admin():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", ("admin@iprotect.com",))
    if not cursor.fetchone():
        hashed_pw = generate_password_hash("AdminMaster@2026")
        cursor.execute("INSERT INTO users (email, password, status) VALUES (?, ?, ?)", ("admin@iprotect.com", hashed_pw, "Active"))
        conn.commit()
    conn.close()

check_admin()

# ইমেইল ওটিপি পাঠানোর ফাংশন
def send_otp_email(receiver_email, otp_code):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = "IP Protect - Verification OTP"
        
        body = f"Your verification code is: {otp_code}. Please enter this code to complete your signup."
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False


# কমপ্লিট ফ্রন্টএন্ট ও ড্যাশবোর্ড টেমপ্লেট
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Enterprise IP Protect SaaS Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 font-sans">

    {% if page == 'login' %}
    <!-- Login Screen -->
    <div class="flex items-center justify-center h-screen bg-slate-900">
        <div class="bg-slate-900 border border-slate-800 p-8 rounded-2xl w-96 shadow-2xl">
            <h2 class="text-2xl font-bold text-blue-400 mb-6 text-center">🛡️ User / Admin Login</h2>
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="bg-red-500/20 text-red-400 p-3 rounded-lg text-sm mb-4 border border-red-500/30">
                  {{ messages[0] }}
                </div>
              {% endif %}
            {% endwith %}
            <form method="POST" action="/login" class="space-y-4">
                <div>
                    <label class="block text-xs text-slate-400 mb-1">Email Address</label>
                    <input type="email" name="email" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs text-slate-400 mb-1">Password</label>
                    <input type="password" name="password" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none">
                </div>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg text-sm transition shadow-lg">Login</button>
            </form>
            <p class="text-xs text-slate-400 text-center mt-4">Don't have an account? <a href="/signup" class="text-blue-400 hover:underline">Sign up</a></p>
        </div>
    </div>

    {% elif page == 'signup' %}
    <!-- Signup Screen -->
    <div class="flex items-center justify-center h-screen bg-slate-900">
        <div class="bg-slate-900 border border-slate-800 p-8 rounded-2xl w-96 shadow-2xl">
            <h2 class="text-2xl font-bold text-emerald-400 mb-6 text-center">📝 User Signup</h2>
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="bg-red-500/20 text-red-400 p-3 rounded-lg text-sm mb-4 border border-red-500/30">
                  {{ messages[0] }}
                </div>
              {% endif %}
            {% endwith %}
            <form method="POST" action="/signup" class="space-y-4">
                <div>
                    <label class="block text-xs text-slate-400 mb-1">Gmail Address</label>
                    <input type="email" name="email" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm focus:border-emerald-500 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs text-slate-400 mb-1">Password</label>
                    <input type="password" name="password" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm focus:border-emerald-500 focus:outline-none">
                </div>
                <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg text-sm transition shadow-lg">Register & Send OTP</button>
            </form>
            <p class="text-xs text-slate-400 text-center mt-4">Already registered? <a href="/login" class="text-blue-400 hover:underline">Login here</a></p>
        </div>
    </div>

    {% elif page == 'verify' %}
    <!-- OTP Verify Screen -->
    <div class="flex items-center justify-center h-screen bg-slate-900">
        <div class="bg-slate-900 border border-slate-800 p-8 rounded-2xl w-96 shadow-2xl">
            <h2 class="text-2xl font-bold text-yellow-400 mb-6 text-center">🔑 Email Verification</h2>
            <p class="text-xs text-slate-400 mb-4 text-center">We have sent a 6-digit verification code to your Gmail.</p>
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="bg-red-500/20 text-red-400 p-3 rounded-lg text-sm mb-4 border border-red-500/30">
                  {{ messages[0] }}
                </div>
              {% endif %}
            {% endwith %}
            <form method="POST" action="/verify-otp" class="space-y-4">
                <div>
                    <label class="block text-xs text-slate-400 mb-1">Enter OTP Code</label>
                    <input type="text" name="otp" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-center tracking-widest text-lg font-bold focus:border-yellow-500 focus:outline-none">
                </div>
                <button type="submit" class="w-full bg-yellow-600 hover:bg-yellow-500 text-white font-medium py-2.5 rounded-lg text-sm transition shadow-lg">Verify & Activate</button>
            </form>
        </div>
    </div>

    {% elif page == 'admin_panel' %}
    <!-- Admin Master Panel -->
    <div class="flex h-screen overflow-hidden">
        <div class="w-64 bg-slate-900 border-r border-slate-800 p-5 flex flex-col justify-between">
            <div>
                <h1 class="text-xl font-bold text-purple-400 mb-8">👑 Admin Control</h1>
                <ul class="space-y-2 text-sm text-slate-300">
                    <li class="bg-purple-600 text-white p-2.5 rounded-lg font-medium">👥 User Management</li>
                    <li class="hover:bg-slate-800 p-2.5 rounded-lg cursor-pointer text-slate-400"><a href="/admin-master-panel">📊 System Analytics</a></li>
                </ul>
            </div>
            <div>
                <a href="/download-source" class="block text-center bg-emerald-600 hover:bg-emerald-500 text-white py-2.5 rounded-xl text-xs font-semibold mb-3 shadow-lg">📥 Download Source (.zip)</a>
                <a href="/logout" class="block text-center bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 py-2 rounded-lg text-xs font-semibold">Logout</a>
            </div>
        </div>

        <div class="flex-1 flex flex-col overflow-y-auto p-8">
            <h2 class="text-xl font-bold mb-6 text-slate-200">Registered Users Control (Total: {{ users | length }})</h2>
            <div class="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
                <table class="w-full text-left border-collapse text-sm">
                    <thead>
                        <tr class="bg-slate-950 text-slate-400 border-b border-slate-800 text-xs">
                            <th class="p-4">ID</th>
                            <th class="p-4">User Gmail</th>
                            <th class="p-4">Status</th>
                            <th class="p-4">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for u in users %}
                        <tr class="border-b border-slate-800/50 hover:bg-slate-800/30">
                            <td class="p-4">{{ u[0] }}</td>
                            <td class="p-4 text-blue-400">{{ u[1] }}</td>
                            <td class="p-4">
                                <span class="px-2.5 py-1 rounded-full text-xs font-semibold {% if u[3] == 'Active' %} bg-green-500/20 text-green-400 {% else %} bg-red-500/20 text-red-400 {% endif %}">
                                    {{ u[3] }}
                                </span>
                            </td>
                            <td class="p-4">
                                {% if u[1] != 'admin@iprotect.com' %}
                                    {% if u[3] == 'Active' %}
                                    <a href="/ban-user/{{ u[0] }}" class="bg-red-600/20 text-red-400 px-3 py-1 rounded-lg text-xs font-semibold hover:bg-red-600 hover:text-white transition">Ban</a>
                                    {% else %}
                                    <a href="/unban-user/{{ u[0] }}" class="bg-green-600/20 text-green-400 px-3 py-1 rounded-lg text-xs font-semibold hover:bg-green-600 hover:text-white transition">Unban</a>
                                    {% endif %}
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    {% elif page == 'user_dashboard' %}
    <!-- User Dashboard -->
    <div class="flex h-screen overflow-hidden">
        <div class="w-64 bg-slate-900 border-r border-slate-800 p-5 flex flex-col justify-between">
            <div>
                <h1 class="text-xl font-bold text-blue-400 mb-8">🛡️ IP Protect User</h1>
                <ul class="space-y-2 text-sm text-slate-300">
                    <li class="bg-blue-600 text-white p-2.5 rounded-lg font-medium">📊 Dashboard</li>
                </ul>
            </div>
            <div>
                <p class="text-xs text-slate-400 mb-2 truncate">User: {{ session.get('user_email') }}</p>
                <a href="/logout" class="block text-center bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 py-2 rounded-lg text-xs font-semibold">Logout</a>
            </div>
        </div>

        <div class="flex-1 flex flex-col overflow-y-auto p-8">
            <h2 class="text-lg font-semibold mb-6">User Reporting Control Center</h2>
            <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 mb-8 shadow-xl">
                <form action="/create-report" method="POST" class="flex gap-4">
                    <select name="type" class="bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm flex-1 focus:outline-none">
                        <option value="Copyright">Copyright Violation</option>
                        <option value="Trademark">Trademark Infringement</option>
                    </select>
                    <input type="text" name="target" placeholder="Target Profile URL" required class="bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm flex-2 w-1/2 focus:outline-none">
                    <button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-xl text-sm font-medium">Submit Report</button>
                </form>
            </div>

            <div class="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
                <table class="w-full text-left border-collapse text-sm">
                    <thead>
                        <tr class="bg-slate-950 text-slate-400 border-b border-slate-800 text-xs">
                            <th class="p-4">Date</th>
                            <th class="p-4">Type</th>
                            <th class="p-4">Target</th>
                            <th class="p-4">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in reports %}
                        <tr class="border-b border-slate-800/50 hover:bg-slate-800/30">
                            <td class="p-4 text-xs text-slate-400">{{ r[2] }}</td>
                            <td class="p-4 font-medium">{{ r[3] }}</td>
                            <td class="p-4 text-blue-400">{{ r[4] }}</td>
                            <td class="p-4"><span class="bg-blue-500/20 text-blue-400 px-2.5 py-1 rounded-full text-xs">{{ r[5] }}</span></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    {% endif %}

</body>
</html>
"""


# রাউটসমূহ
@app.route('/')
def index():
    if 'user_email' in session:
        if session['user_email'] == 'admin@iprotect.com':
            return redirect(url_for('admin_panel'))
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        return render_template_string(HTML_TEMPLATE, page='login')
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        if user[3] == 'Banned':
            flash("Your account has been banned by admin!")
            return redirect(url_for('login_page'))
        
        session['user_email'] = email
        if email == 'admin@iprotect.com':
            return redirect(url_for('admin_panel'))
        return redirect(url_for('user_dashboard'))
    else:
        flash("Invalid email or password!")
        return redirect(url_for('login_page'))

@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    if request.method == 'GET':
        return render_template_string(HTML_TEMPLATE, page='signup')
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        flash("Email already registered!")
        return redirect(url_for('signup_page'))
    
    otp = str(random.randint(100000, 999999))
    hashed_pw = generate_password_hash(password)
    
    cursor.execute("INSERT INTO users (email, password, status, otp) VALUES (?, ?, ?, ?)", (email, hashed_pw, 'Pending', otp))
    conn.commit()
    conn.close()
    
    # জিমেইলে ওটিপি পাঠানো
    send_otp_email(email, otp)
    session['temp_email'] = email
    return redirect(url_for('verify_page'))

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_page():
    if request.method == 'GET':
        return render_template_string(HTML_TEMPLATE, page='verify')
    
    user_otp = request.form.get('otp')
    email = session.get('temp_email')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT otp FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    
    if row and row[0] == user_otp:
        cursor.execute("UPDATE users SET status = 'Active', otp = NULL WHERE email = ?", (email,))
        conn.commit()
        conn.close()
        session.pop('temp_email', None)
        flash("Account verified successfully! Please login.")
        return redirect(url_for('login_page'))
    else:
        conn.close()
        flash("Invalid OTP code!")
        return redirect(url_for('verify_page'))

@app.route('/admin-master-panel')
def admin_panel():
    if session.get('user_email') != 'admin@iprotect.com':
        return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password, status FROM users")
    users = cursor.fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, page='admin_panel', users=users)

@app.route('/ban-user/<int:user_id>')
def ban_user(user_id):
    if session.get('user_email') != 'admin@iprotect.com':
        return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'Banned' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/unban-user/<int:user_id>')
def unban_user(user_id):
    if session.get('user_email') != 'admin@iprotect.com':
        return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'Active' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/download-source')
def download_source():
    if session.get('user_email') != 'admin@iprotect.com':
        return redirect(url_for('login_page'))
    
    # বর্তমান app.py ফাইলটিকে জিপ ফাইলে রূপান্তর করে ডাউনলোড করার ব্যবস্থা
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(__file__, os.path.basename(__file__))
    memory_file.seek(0)
    
    return send_file(memory_file, download_name='ip_protect_saas_source.zip', as_attachment=True)

@app.route('/user-dashboard')
def user_dashboard():
    if 'user_email' not in session or session['user_email'] == 'admin@iprotect.com':
        return redirect(url_for('login_page'))
    
    email = session['user_email']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE user_email = ? ORDER BY id DESC", (email,))
    reports = cursor.fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, page='user_dashboard', reports=reports)

@app.route('/create-report', methods=['POST'])
def create_report():
    if 'user_email' not in session:
        return redirect(url_for('login_page'))
    
    email = session['user_email']
    rep_type = request.form.get('type')
    target = request.form.get('target')
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reports (user_email, date, type, target, status, log) VALUES (?, ?, ?, ?, ?, ?)",
                   (email, current_time, rep_type, target, 'Submitted', 'Processed by user'))
    conn.commit()
    conn.close()
    
    return redirect(url_for('user_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)