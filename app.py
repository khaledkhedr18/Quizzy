from flask import Flask, render_template, url_for, request, g, redirect, session
from dbConnection import connect_to_db, getDatabase
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


@app.teardown_appcontext
def close_connection(exception):
    """
    Closes the database connection and handles any exceptions that occur during teardown.

    Called by Flask automatically when the application context is torn down.
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
    if exception is not None:
        print(f"Exception occurred at teardown: {exception}")


def get_current_user():
    """
    Returns the user object associated with the current session, or None if no user is logged in.

    :return: The user object associated with the current session, or None if no user is logged in
    :rtype: tuple or None
    """
    user_result = None
    if 'user' in session:
        user = session['user']
        db = getDatabase()
        if db is None:
            return None
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE name = %s", (user,))
        user_result = cursor.fetchone()
    cursor.close()
    db.close()
    return user_result


@app.route("/")
def index():
    """
    Displays the homepage for Quizzy.
    """
    return render_template("home.html")


@app.route("/login")
def login():
    """
    Displays the login page for Quizzy.
    """
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Handles a GET/POST request to the /register route.

    If the request is a POST, the function takes the username and password
    from the form data, hashes the password, and creates a new user in the
    database. If the request is a GET, the function renders the registration
    page.

    :return: The rendered registration page on a GET, a redirect to the
             homepage on a POST
    :rtype: str
    """
    if request.method == "POST":
        db = getDatabase()
        if db is None:
            return "Error connecting to the database", 500
        name = request.form.get("name")
        password = request.form.get("password")
        hashed_password = generate_password_hash(
            password, method='pbkdf2:sha256')
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (name, password, teacher, admin) VALUES (%s, %s, %s, %s)",
            (name, hashed_password, False, False))
        db.commit()
        cursor.close()
        db.close()
        session['user'] = name
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    """
    Logs out the user from Quizzy and redirects them to the homepage.
    """
    return render_template("home.html")


if __name__ == "__main__":
    app.run(debug=True)
