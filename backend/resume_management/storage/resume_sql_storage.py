import sqlite3
import os

DB_PATH = os.path.join('data', 'datasets', 'resume.db')

def init_sqlite_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS resume_summary (
        resume_id TEXT PRIMARY KEY,
        characteristics TEXT,
        experience_summary TEXT,
        skills_overview TEXT
    )
    ''')
    conn.commit()
    conn.close()

def store_resume_summary(resume_id, characteristics, experience_summary, skills_overview):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO resume_summary 
    (resume_id, characteristics, experience_summary, skills_overview) 
    VALUES (?, ?, ?, ?)
    ''', (resume_id, characteristics, experience_summary, skills_overview))
    conn.commit()
    conn.close()
