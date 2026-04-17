#!/usr/bin/env python3
"""
Setup SQLite database for Eco-Friendly Community.
Creates the database and all tables.
"""

import sqlite3
import os
from pathlib import Path

def setup_database(db_path="green_points.db"):
    """Create SQLite database and tables."""
    db_dir = Path(__file__).parent
    db_file = db_dir / db_path
    
    print(f"Setting up SQLite database: {db_file}")
    
    # Read schema
    schema_file = db_dir / "schema_sqlite.sql"
    if not schema_file.exists():
        print(f"Error: Schema file not found: {schema_file}")
        return False
    
    with open(schema_file, 'r') as f:
        schema = f.read()
    
    # Connect and create tables
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        # Execute schema
        cursor.executescript(schema)
        conn.commit()
        print("✅ Database created successfully!")
        
        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n✅ Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        return True
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "green_points.db"
    success = setup_database(db_path)
    sys.exit(0 if success else 1)

