import sys
from dotenv import load_dotenv

load_dotenv()

try:
    print("Testing FastAPI app import...")
    from main import app
    print("✓ FastAPI app imported successfully")
    
    print("\nTesting database initialization...")
    from backend.core.database import init_database
    success = init_database()
    if success:
        print("✓ Database initialized successfully")
    else:
        print("✗ Database initialization failed")
        sys.exit(1)
        
    print("\nChecking registered routes...")
    routes = []
    for route in app.routes:
        routes.append(str(route.path))
    print(f"✓ Found {len(routes)} routes")
    for route in sorted(routes)[:20]:  # Show first 20
        print(f"  - {route}")
    
    print("\n✓ All checks passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
