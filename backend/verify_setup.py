#!/usr/bin/env python3
"""
Verification script to check if everything is set up correctly.
"""

import os
import sys
from pathlib import Path

def check_database():
    """Check if SQLite database exists and has tables."""
    print("📁 Checking database...")
    db_path = Path(__file__).parent / "green_points.db"
    if not db_path.exists():
        print("❌ Database not found. Run: python setup_sqlite.py")
        return False
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        conn.close()
        
        if len(tables) < 10:
            print(f"❌ Database has only {len(tables)} tables. Expected 12+ tables.")
            return False
        
        print(f"✅ Database OK ({len(tables)} tables)")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def check_dependencies():
    """Check if required packages are installed."""
    print("📦 Checking dependencies...")
    required = [
        'flask', 'flask_cors', 'fastapi', 'uvicorn',
        'streamlit', 'torch', 'transformers', 'PIL',
        'sqlite3', 'requests'
    ]
    
    missing = []
    for package in required:
        try:
            if package == 'PIL':
                __import__('PIL')
            elif package == 'sqlite3':
                __import__('sqlite3')
            elif package == 'flask_cors':
                __import__('flask_cors')
            else:
                __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed")
    return True

def check_files():
    """Check if required files exist."""
    print("📄 Checking files...")
    required_files = [
        'flask_app.py',
        'model_api.py',
        'streamlit_integrated.py',
        'greenpoints_app.py',
        'setup_sqlite.py',
        'schema_sqlite.sql',
        'green_points.db'
    ]
    
    backend_dir = Path(__file__).parent
    missing = []
    for file in required_files:
        if (backend_dir / file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - NOT FOUND")
            missing.append(file)
    
    if missing:
        print(f"\n❌ Missing files: {', '.join(missing)}")
        return False
    
    print("✅ All required files present")
    return True

def check_imports():
    """Check if files can be imported."""
    print("🔍 Checking imports...")
    try:
        import flask_app
        print("  ✅ flask_app.py")
    except Exception as e:
        print(f"  ❌ flask_app.py: {e}")
        return False
    
    try:
        import model_api
        print("  ✅ model_api.py")
    except Exception as e:
        print(f"  ❌ model_api.py: {e}")
        return False
    
    try:
        # This will show Streamlit warnings, but that's OK
        import streamlit_integrated
        print("  ✅ streamlit_integrated.py")
    except Exception as e:
        print(f"  ❌ streamlit_integrated.py: {e}")
        return False
    
    print("✅ All files import successfully")
    return True

def main():
    """Run all checks."""
    print("=" * 60)
    print("  Eco-Friendly Community - Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Files", check_files),
        ("Dependencies", check_dependencies),
        ("Database", check_database),
        ("Imports", check_imports),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{'=' * 60}")
        print(f"  {name}")
        print("=" * 60)
        result = check_func()
        results.append((name, result))
        print()
    
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All checks passed! Ready to run the application.")
        print("\nNext steps:")
        print("  1. Start all services: start_all_windows.bat")
        print("  2. Open frontend: http://localhost:3000")
        print("  3. Test upload: Click 'Take Photo' or 'Upload File'")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

