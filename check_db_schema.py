import sqlite3

try:
    conn = sqlite3.connect('jobtracker.db')
    cur = conn.cursor()
    
    # Check if users table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone():
        print("Users table exists")
        cur.execute("PRAGMA table_info(users)")
        cols = cur.fetchall()
        print(f"Columns: {len(cols)}")
        for row in cols:
            print(f"  {row}")
    else:
        print("Users table does NOT exist")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
