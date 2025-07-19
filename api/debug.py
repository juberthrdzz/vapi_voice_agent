from fastapi import FastAPI  # Import FastAPI framework
import json  # Import JSON library
from pathlib import Path  # Import Path to handle file paths

# Create FastAPI application instance for debugging
app = FastAPI(title="Debug API")

@app.get("/")
async def debug_root():
    """
    Simple health check endpoint without any external dependencies.
    This helps verify if Vercel can run our Python code.
    """
    return {"message": "Debug API is working", "status": "ok"}

@app.get("/menu-test")
async def debug_menu():
    """
    Test menu loading without Redis dependencies.
    This verifies if file reading works on Vercel.
    """
    try:
        # Get the path to menu.json file (one level up from api folder)
        menu_path = Path(__file__).parent.parent / "menu.json"
        
        # Open and read the menu JSON file
        with open(menu_path, "r") as f:
            menu_data = json.load(f)  # Parse JSON
        
        return {"status": "success", "menu_categories": list(menu_data["categories"].keys())}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Export the FastAPI app instance for Vercel deployment
handler = app 