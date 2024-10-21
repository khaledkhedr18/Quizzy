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
    Gets the current user object from the database based on the session user.

    If the user is not logged in, it returns None.
    If the user is logged in, it checks if the user object exists in the database.
    If the user object exists in the database, it updates the session user and
    returns the user object.
    If the user object does not exist in the database, it removes the user from
    the session and returns None.

    :return: The user object if the user is logged in, None otherwise
    :rtype: tuple
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


@app.route("/about")
def about():
    """
    Displays the homepage for Quizzy.

    Displays the links to the login, register and logout pages.
    If a user is logged in, displays the user's name on the page.

    :return: The rendered homepage
    :rtype: str
    """
    currentUser = get_current_user()
    return render_template("about.html", user=currentUser)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles user login.

    Verifies the user credentials and logs the user in if valid.
    If the user is already logged in, it redirects the user to the homepage.
    If the user is not logged in, it renders the login page and handles the form submission.
    If the form submission is invalid, it renders the login page with an error message.
    If the user credentials are invalid, it renders the login page with an error message.
    If the user is logged in, it renders the homepage with a success message.

    :return: The rendered login or homepage
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
    Handles the registration of new users.

    This function renders the registration page if the request is a GET request.
    If the request is a POST request, it validates the user input, checks if the username already exists,
    and inserts the new user into the database if the input is valid.

    :return: The rendered registration page or homepage
    :rtype: str
    """
    pageError = None
    currentUser = get_current_user()
    if request.method == "POST":
        db = getDatabase()
        if db is None:
            return "Error connecting to the database", 500
        cursor = db.cursor()

        name = request.form.get("name")
        if not name or name.strip() == "":
            pageError = "Please enter a username"
            return render_template("register.html", error=pageError, user=currentUser)

        cursor.execute("SELECT * FROM users WHERE name = %s", (name,))
        existing_user = cursor.fetchone()
        if existing_user:
            pageError = "The username already exists"
            return render_template("register.html", error=pageError, user=currentUser)

        password = request.form.get("password")
        if not password or len(password) < 8:
            pageError = "Please enter a password that is more than 8 characters long!"
            return render_template("register.html", error=pageError, user=currentUser)

        hashed_password = generate_password_hash(
            password, method='pbkdf2:sha256')
        cursor.execute("INSERT INTO users (name, password, teacher, admin) VALUES (%s, %s, %s, %s)",
                       (name, hashed_password, False, False))
        db.commit()
        cursor.close()
        db.close()

        # session['user'] = name
        currentUser = get_current_user()
        return render_template("home.html", success="Successfully registered", user=currentUser)

    return render_template("register.html", user=currentUser)


@app.route('/allusers', methods=["GET", "POST"])
def all_users():
    """
    Handles user registration.

    Verifies the user credentials and registers the user if valid.
    If the user is already logged in, it renders the homepage with a success message.
    If the user is not logged in, it renders the login page.
    If the user credentials are invalid, it renders the login page with an error message.

    :return: The rendered login or homepage
    :rtype: str
    """
    currentUser = get_current_user()
    if currentUser:
        db = getDatabase()
        cursor = db.cursor()
        cursor.execute('select * from users')
        allUsers = cursor.fetchall()
        return render_template('users.html', user=currentUser, users=allUsers)
    else:
        return redirect(url_for('login'))


@app.route('/promote/<int:id>', methods=["GET", "POST"])
def promote(id):
    """
    Promote a user to a teacher.

    :param id: The id of the user to be promoted
    :return: Redirect to the all users page if the request is a GET request and the user is logged in
    :rtype: str
    """
    user = get_current_user()

    if request.method == "GET" and user:
        db = getDatabase()
        cursor = db.cursor()
        cursor.execute("update users set teacher = true where id = %s", (id,))
        db.commit()
        cursor.close()
        db.close()
        return redirect(url_for('all_users'))
    else:
        return redirect(url_for('login'))


@app.route('/askquestions', methods=["GET", "POST"])
def askquestions():
    """
    Handles asking a question.

    This function renders the ask question page if the request is a GET request and the user is logged in.
    If the request is a POST request, it validates the user input, checks if the teacher exists,
    and inserts the new question into the database if the input is valid.

    :return: The rendered ask question page or homepage
    :rtype: str
    """
    success = None
    currentUser = get_current_user()
    if currentUser:
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
    else:
        return redirect(url_for('login'))


@app.route('/answer/<question_id>', methods=["GET", "POST"])
def answer(question_id):
    """
    Handles answering a question.

    Renders the answer page if the request is a GET request and the user is logged in.
    If the request is a POST request, it validates the user input, updates the question
    in the database if the input is valid, and redirects the user to the unanswered questions page.
    If the user is not logged in, it redirects the user to the login page.

    :param question_id: The id of the question to be answered
    :return: The rendered answer page or login page
    :rtype: str
    """
    success = None
    error = None
    user = get_current_user()
    if user:
        db = getDatabase()
        cursor = db.cursor()
        if request.method == "POST":
            answer = request.form.get("answer")
            if answer:
                cursor.execute("update questions set answer_text = %s where id = %s",
                               (answer, question_id))
                db.commit()
                success = "Answered successfully"
                return redirect(url_for('unansweredquestions', success=success))
            else:
                error = "Unexpected error, Please try again!"
                return redirect(url_for('unansweredquestions', error=error))

        cursor.execute(
            "select * from questions where id = %s", (question_id,))
        fetched_question = cursor.fetchone()
        return render_template('answer.html', user=user, question=fetched_question)
    else:
        return redirect(url_for('login'))


@app.route('/unansweredquestions', methods=["GET", "POST"])
def unansweredquestions():
    """
    Handles viewing unanswered questions.

    Renders the unanswered questions page if the request is a GET request and the user is logged in.
    If the user is not logged in, it redirects the user to the login page.

    :return: The rendered unanswered questions page or login page
    :rtype: str
    """
    currentUser = get_current_user()
    if currentUser:
        db = getDatabase()
        cursor = db.cursor()
        if cursor is None or currentUser is None:
            error = "Error connecting to the database"
            return render_template('home.html', error=error, user=currentUser), 500
        else:
            cursor.execute(
                'select * from questions where answer_text is null and teacher_id = %s', (currentUser[0],))
            allQuestions = cursor.fetchall()
            return render_template('unansweredquestions.html', user=currentUser, allQuestions=allQuestions)
    else:
        return redirect(url_for('login'))


@app.route('/answeredquestions', methods=["GET", "POST"])
def answeredquestions():
    """
    Handles viewing answered questions.

    Renders the answered questions page if the request is a GET request and the user is logged in.
    If the user is not logged in, it redirects the user to the login page.

    :return: The rendered answered questions page or login page
    :rtype: str
    """
    currentUser = get_current_user()
    if currentUser:
        db = getDatabase()
        cursor = db.cursor()
        if cursor is None or currentUser is None:
            error = "Error connecting to the database"
            return render_template('home.html', error=error, user=currentUser), 500
        else:
            cursor.execute(
                'select * from questions where answer_text is not null and asked_by_id = %s', (currentUser[0],))
            allQuestions = cursor.fetchall()
            return render_template('answeredquestions.html', user=currentUser, allQuestions=allQuestions)
    else:
        return redirect(url_for('login'))


@app.route('/teacheransweredquestions', methods=["GET", "POST"])
def teacheransweredquestions():
    """
    Handles viewing answered questions of the teacher.

    Renders the answered questions page if the request is a GET request and the user is logged in.
    If the user is not logged in, it redirects the user to the login page.

    :return: The rendered answered questions page or login page
    :rtype: str
    """
    currentUser = get_current_user()
    if currentUser:
        db = getDatabase()
        cursor = db.cursor()
        if cursor is None or currentUser is None:
            error = "Error connecting to the database"
            return render_template('home.html', error=error, user=currentUser), 500
        else:
            cursor.execute(
                'select * from questions where answer_text is not null and teacher_id = %s', (currentUser[0],))
            allQuestions = cursor.fetchall()
            return render_template('teacheransweredquestions.html', user=currentUser, allQuestions=allQuestions)
    else:
        return redirect(url_for('login'))


@app.route('/pendingquestions', methods=["GET", "POST"])
def pendingquestions():
    """
    Handles viewing pending questions.

    Renders the pending questions page if the request is a GET request and the user is logged in.
    If the user is not logged in, it redirects the user to the login page.

    :return: The rendered pending questions page or login page
    :rtype: str
    """
    currentUser = get_current_user()
    if currentUser:
        db = getDatabase()
        cursor = db.cursor()
        if cursor is None or currentUser is None:
            error = "Error connecting to the database"
            return render_template('home.html', error=error, user=currentUser), 500
        else:
            cursor.execute(
                'select * from questions where answer_text is null and asked_by_id = %s', (currentUser[0],))
            allQuestions = cursor.fetchall()
            return render_template('pendingquestions.html', user=currentUser, allQuestions=allQuestions)
    else:
        return redirect(url_for('login'))


@app.route('/userprofile/<int:id>', methods=["GET"])
def user_profile(id):
    """
    Handles viewing a user's profile.

    Renders the user's profile page if the request is a GET request and the user is logged in.
    If the user is not logged in, it redirects the user to the login page.
    If the user is not found, it returns a 404 error.

    :param id: The id of the user whose profile to view
    :return: The rendered profile page or login page
    :rtype: str
    """
    currentUser = get_current_user()
    if currentUser:  # Fetch the current logged-in user
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
    else:
        return redirect(url_for('login'))


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
