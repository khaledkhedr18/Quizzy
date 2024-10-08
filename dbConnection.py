import mysql.connector
from flask import g
from mysql.connector import Error, OperationalError


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
    except Error as err:
        print(f"Error connecting to the database: {err}")
        return None


def getDatabase():
    if 'quizzy' not in g:
        g.quizzy = connect_to_db()
    elif g.quizzy.is_connected() == False:
        print("Reconnecting to database")
        g.quizzy = connect_to_db()
    return g.quizzy


def close_db_connection():
    db = g.pop('quizzy', None)
    if db is not None:
        db.close()
        print("Database connection closed")
