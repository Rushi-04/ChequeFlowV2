import sqlite3
import os

def init_db():
    # Define absolute path for the database in the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "cheques.db")
    print(f"DEBUG: Initializing database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Update/Create Cheques Table with approval columns
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cheques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cheque_number TEXT UNIQUE,
        date TEXT,
        ssn TEXT,
        payee_name TEXT,
        payee_address TEXT,
        amount REAL,
        amount_words TEXT,
        claim_number TEXT,
        status TEXT,
        payment_mode TEXT,
        bkcode TEXT,
        employer_name TEXT,
        employer_street TEXT,
        employer_city_state_zip TEXT,
        bank_info TEXT,
        routing_number TEXT,
        micr_account_tail TEXT,
        bank_routing_fraction TEXT,
        void_days INTEGER DEFAULT 90,
        signature_path TEXT
    )
    ''')
    
    columns_to_add = [
        ("bank_routing_fraction", "TEXT"),
        ("approved_signature_id", "INTEGER"),
        ("approved_by_name", "TEXT"),
        ("approved_signature_path", "TEXT"),
        ("is_approved", "INTEGER DEFAULT 0"),
        ("approved_at", "TEXT")
    ]
    
    cursor.execute("PRAGMA table_info(cheques)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"Adding column {col_name} to cheques table...")
            cursor.execute(f"ALTER TABLE cheques ADD COLUMN {col_name} {col_type}")

    # 2. Create Signatures Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS signatures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        signature_path TEXT NOT NULL
    )
    ''')
    
    # 3. Seed Signatures if empty
    cursor.execute("SELECT COUNT(*) FROM signatures")
    if cursor.fetchone()[0] == 0:
        print("Seeding demo signatures...")
        # Note: Paths should be relative to the project root or absolute.
        # Here we use paths relative to where the app runs.
        demo_signatures = [
            ("John Doe", "assets/signatures/white-sig.jpg"),
            ("Jane Smith", "assets/signatures/white-sig.jpg"),
            ("Michael Brown", "assets/signatures/white-sig.jpg"),
            ("Emily Davis", "assets/signatures/white-sig.jpg"),
            ("Chris Wilson", "assets/signatures/white-sig.jpg"),
            ("Sarah Miller", "assets/signatures/white-sig.jpg"),
            ("David Taylor", "assets/signatures/white-sig.jpg"),
            ("Lisa Anderson", "assets/signatures/white-sig.jpg"),
            ("James Thomas", "assets/signatures/white-sig.jpg"),
            ("Michelle Jackson", "assets/signatures/white-sig.jpg")
        ]
        cursor.executemany("INSERT INTO signatures (name, signature_path) VALUES (?, ?)", demo_signatures)

    conn.commit()
    conn.close()
    print("Database initialization and migration complete.")

if __name__ == "__main__":
    init_db()
