#!/usr/bin/env python3
"""
Pre-load AI models to cache them before starting services.
This reduces startup time on subsequent runs.
"""

import sys
import time

def main():
    print("=" * 70)
    print("  Pre-loading AI Models for Eco-Friendly Community")
    print("=" * 70)
    print()
    print("This will download and cache all AI models (~4GB total)")
    print("First run: 5-10 minutes (downloading)")
    print("Subsequent runs: 30-60 seconds (from cache)")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    print()
    print("=" * 70)
    print("  Starting Model Pre-loading...")
    print("=" * 70)
    print()
    
    start_time = time.time()
    
    try:
        # Import and load models
        print("Importing greenpoints_app...")
        import greenpoints_app
        print("✅ Imported")
        print()
        
        print("Loading AI models...")
        print("(This may take several minutes on first run)")
        print()
        
        # Load models
        models = greenpoints_app.get_models()
        
        elapsed = time.time() - start_time
        
        print()
        print("=" * 70)
        print("  ✅ Models Pre-loaded Successfully!")
        print("=" * 70)
        print(f"⏱️  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print()
        print("Models are now cached and will load faster on next startup.")
        print("You can now start the services with:")
        print("  python start_all.py")
        print("  or")
        print("  start_all_windows.bat")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("  ❌ Error Loading Models")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check internet connection (required for first download)")
        print("  2. Check disk space (need ~4GB for model cache)")
        print("  3. Check Python dependencies: pip install -r requirements.txt")
        print()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)

