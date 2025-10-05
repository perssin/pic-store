import os
import sqlite3
import webbrowser
from datetime import datetime
from flask import Flask, request, send_from_directory, redirect, url_for, session, render_template_string

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me"   # used for session encryption

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
DB_FILE = 'images.db'
PASSWORD = "3498"      # <--- change this to your own password
PORT = 5000
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# --- Initialize Database ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS images (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            filename TEXT NOT NULL,
                            filepath TEXT NOT NULL,
                            uploaded_at TEXT NOT NULL
                        )''')
init_db()


# --- HTML Template (includes login + gallery) ---
HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Secure Picture Storage</title>
<style>
body {
  font-family: 'Segoe UI', Arial, sans-serif;
  background: linear-gradient(135deg,#b2dfdb,#e1bee7);
  margin:0; padding:0; text-align:center;
}
.container {
  max-width:900px; margin:50px auto; background:white;
  border-radius:12px; padding:30px; box-shadow:0 0 15px rgba(0,0,0,0.1);
}
h1 { color:#4a148c; margin-bottom:20px; }
input[type="file"], input[type="password"] {
  padding:10px; border:1px solid #ccc; border-radius:6px;
}
button {
  background-color:#7e57c2; color:white; border:none;
  padding:10px 20px; border-radius:6px; margin-left:10px;
  cursor:pointer; transition:background 0.3s;
}
button:hover { background-color:#5e35b1; }
.gallery {
  display:flex; flex-wrap:wrap; justify-content:center; gap:15px;
}
.image-card {
  background:#f9f9f9; border-radius:10px; padding:10px;
  box-shadow:0 0 8px rgba(0,0,0,0.1); width:200px; text-align:center;
}
.image-card img { width:100%; border-radius:10px; }
a {
  display:inline-block; margin-top:8px; text-decoration:none;
  background:#4a148c; color:white; padding:6px 12px;
  border-radius:5px; transition:background 0.3s;
}
a:hover { background:#7b1fa2; }
.logout { background:#c62828; }
.logout:hover { background:#b71c1c; }
</style>
</head>
<body>
  <div class="container">
    {% if not session.get('logged_in') %}
      <h1>🔐 Secure Image Access</h1>
      <form method="POST" action="{{ url_for('login') }}">
        <input type="password" name="password" placeholder="Enter Password" required>
        <button type="submit">Login</button>
      </form>
    {% else %}
      <h1>📸 Secure Picture Manager</h1>
      <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*" required>
        <button type="submit">Upload</button>
        <a href="{{ url_for('logout') }}" class="logout">Logout</a>
      </form>

      <h2>Stored Pictures</h2>
      <div class="gallery">
        {% for id, filename, uploaded_at in images %}
          <div class="image-card">
            <img src="{{ url_for('uploaded_file', filename=filename) }}" alt="{{ filename }}">
            <p>{{ filename }}</p>
            <small>Uploaded: {{ uploaded_at }}</small><br>
            <a href="{{ url_for('download_file', image_id=id) }}">⬇️ Download</a>
            <a href="{{ url_for('delete_file', image_id=id) }}" class="logout">🗑️ Delete</a>
          </div>
        {% else %}
          <p>No pictures uploaded yet.</p>
        {% endfor %}
      </div>
    {% endif %}
  </div>
</body>
</html>
'''


# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if not session.get('logged_in'):
        return render_template_string(HTML)
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO images (filename, filepath, uploaded_at) VALUES (?, ?, ?)",
                             (filename, filepath, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
            return redirect(url_for('upload_file'))
    with sqlite3.connect(DB_FILE) as conn:
        images = conn.execute("SELECT id, filename, uploaded_at FROM images ORDER BY id DESC").fetchall()
    return render_template_string(HTML, images=images)


@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password') == PASSWORD:
        session['logged_in'] = True
    return redirect(url_for('upload_file'))


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('upload_file'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if not session.get('logged_in'):
        return redirect(url_for('upload_file'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/download/<int:image_id>')
def download_file(image_id):
    if not session.get('logged_in'):
        return redirect(url_for('upload_file'))
    with sqlite3.connect(DB_FILE) as conn:
        image = conn.execute("SELECT filename FROM images WHERE id = ?", (image_id,)).fetchone()
    if image:
        return send_from_directory(app.config['UPLOAD_FOLDER'], image[0], as_attachment=True)
    return "File not found", 404


@app.route('/delete/<int:image_id>')
def delete_file(image_id):
    if not session.get('logged_in'):
        return redirect(url_for('upload_file'))
    with sqlite3.connect(DB_FILE) as conn:
        image = conn.execute("SELECT filename, filepath FROM images WHERE id = ?", (image_id,)).fetchone()
        if image:
            try:
                os.remove(image[1])
            except FileNotFoundError:
                pass
            conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
            conn.commit()
    return redirect(url_for('upload_file'))


# --- Auto-open in browser on run ---
def open_browser():
    webbrowser.open(f"http://127.0.0.1:{PORT}")

if __name__ == '__main__':
    import threading
    threading.Timer(1.0, open_browser).start()  # open browser after 1 second
    app.run(debug=True, port=PORT)
