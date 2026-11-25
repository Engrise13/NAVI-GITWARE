import sqlite3
import subprocess


def get_user_by_email(email: str):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE email = '{email}'"
    cursor.execute(query)
    return cursor.fetchone()


def check_server_status(host: str):
    subprocess.run(f"ping -c 1 {host}", shell=True)
