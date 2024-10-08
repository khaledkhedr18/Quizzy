from flask import Flask, render_template, url_for, request
from flask import g, redirect, session, flash
from dbConnection import connect_to_db, getDatabase, close_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import OperationalError
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


@app.teardown_appcontext
def close_connection(exception):
    """
    Closes the database connection and handles any exceptions
    that occur during teardown.

    Called by Flask automatically when the application context is torn down.
    """
    close_db_connection()


def get_current_user():
    """
    Returns the user object associated with the current session,
    or None if no user is logged in.

    :return: The user object associated with the current session,
    or None if no user is logged in

    :rtype: tuple or None
    """
    user_result = None
    if 'user' in session:
        db = getDatabase()
        cursor = db.cursor()
        user = session['user']
        if db is None:
            return None
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
    currentUser = get_current_user()
    return render_template("home.html", user=currentUser)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Displays the login page for Quizzy.
    """
    pageError = None
    currentUser = get_current_user()
    db = None
    cursor = None

    if request.method == "POST":
        try:
            db = getDatabase()  # Recreate the connection for each request
            cursor = db.cursor()

            name = request.form.get("name")
            password = request.form.get("password")

            if not name or name == "":
                pageError = "Please, Enter your username!"
                return render_template("login.html", error=pageError, user=currentUser)

            if not password or len(password) < 8:
                pageError = "Incorrect password, please try again!"
                return render_template("login.html", error=pageError, user=currentUser)

            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE name = %s", (name,))
            userAccount = cursor.fetchone()

            # Verify user credentials
            if userAccount and check_password_hash(userAccount[2], password):
                session['user'] = userAccount[1]
                return render_template("home.html", success="Login Successful!", user=currentUser)

            else:
                pageError = "Invalid username or password!"
                return render_template("login.html", error=pageError, user=currentUser)

        except OperationalError as e:
            pageError = "Database connection issue. Please try again later."
            return render_template("login.html", error=pageError, user=currentUser)

        finally:
            if cursor is not None:
                cursor.close()
            if db is not None:
                db.close()
    return render_template("login.html", user=currentUser, error=pageError)


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Handles the registration of users.

    Displays the registration form if the request is a GET request.
    If the request is a POST request, it attempts to register the user
    with the given username and password. If the username already exists,
    or if the password is not more than 8 characters long, it displays
    the registration form again with an appropriate error message.

    If the registration is successful, it sets the user's session and
    redirects them to the homepage with a success message.

    :return: The rendered registration form or the homepage with a success message
    :rtype: str
    """
    pageError = None
    currentUser = get_current_user()

    if request.method == "POST":
        db = getDatabase()
        cursor = db.cursor()

        if db is None:
            return "Error connecting to the database", 500
        name = request.form.get("name")

        if not name or name == "":
            pageError = "Please enter a username"
            return render_template("register.html", error=pageError, user=currentUser)
        cursor.execute(
            "SELECT * FROM users WHERE name = %s", (name,))

        existing_user = cursor.fetchone()

        if existing_user:
            pageError = "The username already exists"
            return render_template("register.html", error=pageError, user=currentUser)

        password = request.form.get("password")

        if not request.form.get("password") or len(password) < 8:
            pageError = "Please enter a password that is more than 8 characters long!"
            return render_template("register.html", error=pageError, user=currentUser)

        hashed_password = generate_password_hash(
            password, method='pbkdf2:sha256')
        cursor.execute(
            "INSERT INTO users (name, password, teacher, admin) VALUES (%s, %s, %s, %s)",
            (name, hashed_password, False, False))
        db.commit()
        cursor.close()
        db.close()
        session['user'] = name
        return render_template("home.html", success="Successfully registered", user=currentUser)

    return render_template("register.html", user=currentUser)


@app.route("/logout")
def logout():
    """
    Logs out the user from Quizzy and redirects them to the homepage.
    """
    session.pop('user', None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)
