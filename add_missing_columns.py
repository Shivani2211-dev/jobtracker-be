import sqlite3

conn = sqlite3.connect('jobtracker.db')
cur = conn.cursor()

try:
    # Add missing columns to users table
    cur.execute("ALTER TABLE users ADD COLUMN resume_filename VARCHAR(255)")
    print("Added resume_filename")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("resume_filename already exists")
    else:
        print(f"Error adding resume_filename: {e}")

try:
    cur.execute("ALTER TABLE users ADD COLUMN resume_summary TEXT")
    print("Added resume_summary")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("resume_summary already exists")
    else:
        print(f"Error adding resume_summary: {e}")

try:
    cur.execute("ALTER TABLE users ADD COLUMN resume_skills TEXT")
    print("Added resume_skills")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("resume_skills already exists")
    else:
        print(f"Error adding resume_skills: {e}")

conn.commit()
conn.close()
print("\nDatabase schema updated successfully!")
