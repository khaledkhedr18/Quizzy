import mysql.connector
from flask import g
from mysql.connector import Error, OperationalError


def connect_to_db():
    """
    Establishes a connection to the Quizzy database.

    :return: A connection to the database, or None if an error occurred
    :rtype: mysql.connector.connection.MySQLConnection or None
    """
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
    """
    Gets the database connection.
    If the connection has not been established before (i.e. this is the first request),
    it connects to the database.
    If the connection has been established but is not currently connected (i.e. the
    connection has been closed), it reconnects to the database.
    If the connection has been established and is currently connected, it returns the
    existing connection.
    :return: The database connection
    :rtype: mysql.connector.connection.MySQLConnection
    """
    if 'quizzy' not in g:
        g.quizzy = connect_to_db()
    elif g.quizzy.is_connected() == False:
        print("Reconnecting to database")
        g.quizzy = connect_to_db()
    return g.quizzy


def close_db_connection():
    """
    Closes the database connection and removes it from the app context.

    If the connection is not currently connected, it does nothing.
    :return: None
    """
    db = g.pop('quizzy', None)
    if db is not None:
        db.close()
        print("Database connection closed")
