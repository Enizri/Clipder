import sys
import os
from dotenv import load_dotenv

load_dotenv()

try:
    print("Testing FastAPI app routes...")
    from main import app
    
    print("\nAll registered routes:")
    routes = []
    for route in app.routes:
        path = str(route.path)
        routes.append(path)
    
    # Show all routes sorted
    for route in sorted(routes):
        print(f"  {route}")
    
    # Check for ai-editor routes
    ai_routes = [r for r in routes if "ai-editor" in r or "ai_editor" in r]
    print(f"\n✓ Found {len(ai_routes)} AI Editor routes:")
    for route in ai_routes:
        print(f"  - {route}")
    
    if ai_routes:
        print("\n✓ AI Editor routes are registered!")
    else:
        print("\n✗ AI Editor routes NOT found - not registered in main.py")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
