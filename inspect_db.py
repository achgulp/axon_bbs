# Full path: axon_bbs/inspect_db.py
import sqlite3

conn = sqlite3.connect('data/axon_bbs.sqlite3')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())
