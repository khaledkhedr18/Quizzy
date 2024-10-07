import mysql.connector
from flask import g


def connect_to_db():
    try:

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="gamedfashkh1",
            database="quizzy",
            port=3307,
            buffered=True
        )
        print('Successfully connected to database')
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None


def getDatabase():
    if 'quizzy' not in g:
        g.quizzy = connect_to_db()
    return g.quizzy
