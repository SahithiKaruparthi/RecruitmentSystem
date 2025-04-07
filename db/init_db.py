import sqlite3
import os
from pathlib import Path

def init_db():
    """Initialize the SQLite database with necessary tables"""
    db_path = Path('db/memory.sqlite')
    
    # Create db directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table for authentication
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create job_descriptions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS job_descriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT UNIQUE NOT NULL,
        job_title TEXT NOT NULL,
        company TEXT NOT NULL,
        description TEXT NOT NULL,
        skills TEXT NOT NULL, -- JSON array as string
        experience_required TEXT NOT NULL,
        qualification TEXT NOT NULL,
        vector_id TEXT, -- Reference to vector store
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    ''')
    
    # Create resumes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_id TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        experience TEXT NOT NULL, -- JSON as string
        skills TEXT NOT NULL, -- JSON array as string
        education TEXT NOT NULL, -- JSON as string
        file_path TEXT NOT NULL,
        vector_id TEXT, -- Reference to vector store
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Create rankings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rankings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        match_score FLOAT NOT NULL,
        rank INTEGER,
        shortlisted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resume_id) REFERENCES resumes(resume_id),
        FOREIGN KEY (job_id) REFERENCES job_descriptions(job_id),
        UNIQUE(resume_id, job_id)
    )
    ''')
    
    # Create interviews table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        interview_date TIMESTAMP,
        status TEXT CHECK (status IN ('scheduled', 'completed', 'cancelled', 'pending')),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resume_id) REFERENCES resumes(resume_id),
        FOREIGN KEY (job_id) REFERENCES job_descriptions(job_id)
    )
    ''')
    
    # Commit and close connection
    conn.commit()
    conn.close()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()