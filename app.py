from flask import Flask, render_template, url_for, request
from flask import g, redirect, session
from dbConnection import connect_to_db, getDatabase, close_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import OperationalError
import os
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)


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
        if db is None:
            return None
        cursor = db.cursor()
        user = session['user']
        cursor.execute("SELECT * FROM users WHERE name = %s", (user,))
        user_result = cursor.fetchone()
        if user_result:
            session['user'] = user_result[1]
            cursor.close()
            db.close()
            return user_result
        cursor.close()
        db.close()
    return None


@app.route("/")
def index():
    """
    Displays the homepage for Quizzy.

    Displays the links to the login, register and logout pages.
    If a user is logged in, displays the user's name on the page.

    :return: The rendered homepage
    :rtype: str
    """
    currentUser = get_current_user()
    return render_template("home.html", user=currentUser)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles user login.

    If the request is a GET request, it displays the login page.
    If the request is a POST request, it attempts to log in the user
    with the given username and password. If the username or password
    is invalid, it displays the login page again with an appropriate
    error message.

    If the login is successful, it sets the user's session and redirects
    them to the homepage with a success message.

    :return: The rendered login page or the homepage with a success message
    :rtype: str
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
            remember_me = request.form.get("remember_me")

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

                # check if keep me logged in is checked
                if remember_me:
                    session.permanent = True
                else:
                    session.permanent = False

                currentUser = get_current_user()
                return render_template("home.html", success="Login Successful!", user=currentUser)

            else:
                pageError = "Invalid username or password!"
                return render_template("login.html", error=pageError, user=currentUser)

        except OperationalError as e:
            pageError = "Database connection issue. Please try again later."
            return render_template("login.html", user=currentUser, error=pageError)

        finally:
            if cursor is not None:
                cursor.close()
            if db is not None:
                db.close()
    return render_template("login.html", user=currentUser, error=pageError)


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Handles the registration of a new user.

    If the request method is POST, it first checks if the username already exists,
    and if the password is not empty and more than 8 characters long.
    If these conditions are met, it inserts the username and hashed password in the database,
    logs the user in and redirects them to the home page.
    If not, it renders the registration page with an error message.

    If the request method is GET, it simply renders the registration page.

    :return: The rendered page
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
        currentUser = get_current_user()
        return render_template("home.html", success="Successfully registered", user=currentUser)

    return render_template("register.html", user=currentUser)


@app.route('/allusers', methods=["GET", "POST"])
def all_users():
    currentUser = get_current_user()
    db = getDatabase()
    cursor = db.cursor()
    cursor.execute('select * from users')
    allUsers = cursor.fetchall()
    return render_template('users.html', user=currentUser, users=allUsers)


@app.route('/promote/<int:id>', methods=["GET", "POST"])
def promote(id):
    user = get_current_user()

    if request.method == "GET":
        db = getDatabase()
        cursor = db.cursor()
        cursor.execute("update users set teacher = true where id = %s", (id,))
        db.commit()
        cursor.close()
        db.close()
        return redirect(url_for('all_users'))

    return render_template('users.html', user=user)


@app.route('/askquestions', methods=["GET", "POST"])
def askquestions():
    success = None
    currentUser = get_current_user()
    db = getDatabase()
    cursor = db.cursor()
    if request.method == "POST":
        question = request.form.get("question")
        teacher = request.form.get("teacher")
        cursor.execute(
            "select * from users where id = %s", (teacher,))
        teacher_result = cursor.fetchone()
        if teacher_result and currentUser:
            cursor.execute(
                "insert into questions (question_text, asked_by_id, teacher_id, teacher_name, asked_by_name) values (%s, %s, %s, %s, %s)", (question, currentUser[0], teacher, teacher_result[1], currentUser[1] if currentUser else None))
            db.commit()
            success = "Question asked successfully"
        else:
            error = "Please, login to ask a question"
            success = "Invalid teacher"
            return render_template('home.html', error=error, user=currentUser)

    cursor.execute('select * from users')
    allUsers = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('askquestions.html', user=currentUser, users=allUsers, success=success)


@app.route('/answerquestions', methods=["GET", "POST"])
def answerquestions():
    currentUser = get_current_user()
    db = getDatabase()
    cursor = db.cursor()
    cursor.execute('select * from users where teacher = 0')
    allUsers = cursor.fetchall()

    return render_template('answerquestions.html', user=currentUser, users=allUsers)


@app.route('/userprofile/<int:id>', methods=["GET"])
def user_profile(id):
    currentUser = get_current_user()  # Fetch the current logged-in user
    db = getDatabase()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (id,))
    userInfo = cursor.fetchone()  # Fetch the target user info
    cursor.close()
    db.close()

    if userInfo:
        # Pass currentUser as 'user' and userInfo as 'user_info' to the template
        return render_template('user_profile.html', user=currentUser, user_info=userInfo)
    else:
        return "User not found", 404


@app.route("/logout")
def logout():
    """
    Logs out the current user.

    Removes the user from the session and redirects to the homepage.

    :return: The rendered homepage
    :rtype: str
    """
    session.pop('user', None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)
