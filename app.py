from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os
from werkzeug.utils import secure_filename
from datetime import date

app = Flask(__name__, template_folder='template')
app.secret_key = 'your_secret_key'

# MySQL configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'act1_database'
}
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

# Allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# Route: Home
@app.route('/')
def index():
    return redirect(url_for('login'))

# Route: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form['name']
            address = request.form['address']
            birthday = request.form['birthday']
            username = request.form['username']
            password = request.form['password']
            image_file = request.files['image']

            # Validate required fields
            if not all([name, address, birthday, username, password, image_file]):
                flash('All fields are required.', 'danger')
                return render_template('register.html')

            # Validate and save image
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                image_file.save(image_path)
                relative_image_path = f'static/uploads/{filename}'
            else:
                flash('Invalid image file.', 'danger')
                return render_template('register.html')

            # Connect to database
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Check for duplicate username
            cursor.execute('SELECT * FROM personal WHERE username=%s', (username,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Username already exists.', 'danger')
            else:
                # Insert user
                cursor.execute(
                    '''
                    INSERT INTO personal (image, name, birthday, address, username, password)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ''',
                    (relative_image_path, name, birthday, address, username, password)
                )
                conn.commit()
                flash('Registration successful! Please log in.', 'success')
                cursor.close()
                conn.close()
                return redirect(url_for('login'))

            cursor.close()
            conn.close()
        except mysql.connector.Error:
            flash('A database error occurred. Please try again.')
        except Exception:
            flash('An unexpected error occurred. Please try again.')
    return render_template('register.html')

# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']

            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT acc_id, image, name, birthday, address
                FROM personal
                WHERE username = %s AND password = %s
            ''', (username, password))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session['user'] = {
                    'id': user['acc_id'],
                    'image': user['image'],
                    'name': user['name'],
                    'birthday': user['birthday'],
                    'address': user['address']
                }
                return redirect(url_for('main'))
            else:
                flash('Invalid username or password.', 'danger')

        except mysql.connector.Error:
            flash('A database error occurred. Please try again.', 'danger')
        except Exception:
            flash('An unexpected error occurred. Please try again.', 'danger')

    return render_template('login.html')

# Route: Main Page (profile)
@app.route('/main', methods=['GET', 'POST'])
def main():
    if 'user' not in session:
        flash('Please log in first.')
        return redirect(url_for('login'))

    user = session['user']
    birthday = user['birthday']
    age = 'N/A'

    # Calculate age
    if birthday:
        today = date.today()
        if isinstance(birthday, str):
            birthday = date.fromisoformat(birthday)
        age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))

    # Build image URL safely
    filename = os.path.basename(user['image']) if user['image'] else None
    image_url = url_for('static', filename=f'uploads/{filename}') if filename else None

    return render_template(
        'profile.html',
        name=user['name'],
        address=user['address'],
        age=age,
        image=image_url
    )
    


# Route: Logout
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True, port=81)
