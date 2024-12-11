from flask import Flask, render_template, request, redirect, url_for, session, flash
from authlib.integrations.flask_client import OAuth
import os
import pytz
from datetime import datetime
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Konfigurasi OAuth
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Hanya untuk pengembangan lokal
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='260418655884-g8qql6osd9hclkof5835g4hv6j8qekib.apps.googleusercontent.com',
    client_secret='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',
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'}
)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # Ganti dengan password MySQL Anda
app.config['MYSQL_DB'] = 'db_webfp'


mysql = MySQL(app)

# Fungsi untuk mendapatkan koneksi MySQL
def get_db_connection():
    return mysql.connection.cursor()

def get_wib_timestamp():
    wib = pytz.timezone('Asia/Jakarta')  # Zona waktu WIB
    return datetime.now(wib).strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        cursor = get_db_connection()
        cursor.execute('INSERT INTO users (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = get_db_connection()
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            if username == 'admin123' and password == 'admin123':
                session['username'] = username
                session['role'] = 'admin'
                return redirect(url_for('admin_dashboard'))
            else:
                session['username'] = username
                session['role'] = 'user'
                return redirect(url_for('user_dashboard'))

    return render_template('login.html')

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()

    cursor = get_db_connection()
    cursor.execute('INSERT IGNORE INTO users (username, email, password) VALUES (%s, %s, %s)', 
                   (user_info['name'], user_info['email'], 'google_user'))
    mysql.connection.commit()
    cursor.close()

    session['username'] = user_info['name']
    return redirect(url_for('user_dashboard'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' in session and session.get('role') == 'admin':
        cursor = get_db_connection()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE recipient = 'admin123'")
        new_messages_count = cursor.fetchone()[0]
        cursor.close()
        return render_template('admin_dashboard.html', new_messages_count=new_messages_count)
    return redirect(url_for('home'))

@app.route('/manage_users')
def manage_users():
    if 'username' in session and session['username'] == 'admin123':
        cursor = get_db_connection()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        cursor.close()
        users_list = []
        for user in users:
            user_dict = {
                'id': user[0],  # Kolom pertama (id)
                'username': user[1],  # Kolom kedua (username)
                'email': user[2],  # Kolom ketiga (email)
                'password': user[3],  # Kolom keempat (password)
            }
            users_list.append(user_dict)

        return render_template('manage_users.html', users=users_list)

    return redirect(url_for('home'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'username' in session and session['username'] == 'admin123':
        cursor = get_db_connection()
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        mysql.connection.commit()
        cursor.close()
        flash('User deleted successfully.')
        return redirect(url_for('manage_users'))
    return redirect(url_for('home'))

@app.route('/user_dashboard')
def user_dashboard():
    if 'username' in session and session.get('role') == 'user':
        return render_template('user_dashboard.html')
    return redirect(url_for('home'))

@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    message = request.form['message']
    sender = session['username']
    recipient = 'admin123'
    timestamp = get_wib_timestamp()
    cursor = get_db_connection()
    cursor.execute("INSERT INTO messages (sender, recipient, message, timestamp) VALUES (%s, %s, %s, %s)", 
                   (sender, recipient, message, timestamp))
    mysql.connection.commit()
    cursor.close()

    flash('Your message has been sent to Admin!', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/view_reports')
def view_reports():
    cursor = get_db_connection()
    cursor.execute("SELECT * FROM messages WHERE recipient = 'admin123' ORDER BY timestamp DESC")
    messages = cursor.fetchall()
    cursor.close()
    return render_template('view_reports.html', messages=messages)

@app.route('/pilih_game')
def pilih_game():
    if 'username' in session:
        return render_template('pilih_game.html')
    return redirect(url_for('home'))

@app.route('/play_game1')
def play_game1():
    return render_template('Game1/index.html')

@app.route('/play_game2')
def play_game2():
    return render_template('Game2/index.html')

@app.route('/play_game3')
def play_game3():
    return render_template('Game3/index.html')

@app.route('/play_game4')
def play_game4():
    return render_template('Game4/index.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    # Menjalankan dalam aplikasi context
    with app.app_context():
        # Buat tabel jika belum ada
        cursor = get_db_connection()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            username VARCHAR(255) UNIQUE,
                            email VARCHAR(255),
                            password VARCHAR(255)
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            sender VARCHAR(255),
                            recipient VARCHAR(255),
                            message TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                        )''')
        mysql.connection.commit()
        cursor.close()

    app.run(debug=True)
