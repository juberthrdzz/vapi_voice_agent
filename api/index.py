import json  # Import JSON library to parse menu file
import os  # Import OS library to access environment variables
from pathlib import Path  # Import Path to handle file paths
from typing import Dict, Any, Optional  # Import type hints for better code documentation

from fastapi import FastAPI, HTTPException  # Import FastAPI framework and HTTP exception handling
from pydantic import BaseModel  # Import Pydantic for data validation
from upstash_redis import Redis  # Import Upstash Redis client

# Create FastAPI application instance
app = FastAPI(title="Restaurant Voice Agent API")

# Initialize Redis client using environment variable for URL
# This connects to Upstash Redis database for caching
redis_client = Redis.from_env()

# Global variable to store menu data in memory for fast access
# This prevents reading the file on every request (improves performance)
MENU_CACHE: Optional[Dict[str, Any]] = None

def load_menu() -> Dict[str, Any]:
    """
    Load menu data from JSON file and cache it in memory.
    This function runs once when the server starts to minimize cold-start time.
    
    Returns:
        Dict containing the complete menu structure
    """
    global MENU_CACHE  # Access the global menu cache variable
    
    if MENU_CACHE is None:  # Only load if not already cached
        # Get the path to menu.json file (one level up from api folder)
        menu_path = Path(__file__).parent.parent / "menu.json"
        
        # Open and read the menu JSON file
        with open(menu_path, "r") as f:
            MENU_CACHE = json.load(f)  # Parse JSON and store in cache
    
    return MENU_CACHE  # Return the cached menu data

# Data models for API requests and responses using Pydantic
class OrderItem(BaseModel):
    """Model for individual items in an order"""
    item_id: str  # Unique identifier for menu item
    quantity: int  # Number of items ordered
    special_requests: Optional[str] = None  # Optional customization requests

class Order(BaseModel):
    """Model for complete customer order"""
    customer_phone: str  # Customer's phone number for order tracking
    items: list[OrderItem]  # List of items being ordered
    total_amount: float  # Total cost of the order

class VoiceQuery(BaseModel):
    """Model for voice assistant queries"""
    query: str  # The customer's spoken question or request
    session_id: str  # Unique session identifier for conversation tracking

@app.on_event("startup")
async def startup_event():
    """
    This function runs when the FastAPI server starts.
    It pre-loads the menu to ensure fast response times.
    """
    load_menu()  # Load menu into memory cache
    print("Menu loaded and cached successfully")  # Log successful loading

@app.get("/")
async def root():
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        Simple message confirming API status
    """
    return {"message": "Restaurant Voice Agent API is running"}

@app.get("/menu")
async def get_menu():
    """
    Get the complete restaurant menu.
    Uses cached data for fast response.
    
    Returns:
        Complete menu with all categories and items
    """
    menu = load_menu()  # Get menu from cache
    return menu

@app.get("/menu/{category}")
async def get_menu_category(category: str):
    """
    Get menu items for a specific category (appetizers, mains, desserts).
    
    Args:
        category: The menu category to retrieve
        
    Returns:
        List of items in the specified category
        
    Raises:
        HTTPException: If category doesn't exist
    """
    menu = load_menu()  # Get menu from cache
    
    # Check if the requested category exists in the menu
    if category not in menu["categories"]:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    
    # Return the items for the requested category
    return {"category": category, "items": menu["categories"][category]}

@app.post("/voice/query")
async def process_voice_query(voice_query: VoiceQuery):
    """
    Process a voice query from the customer.
    This would integrate with a voice AI service to understand customer intent.
    
    Args:
        voice_query: The customer's voice input and session info
        
    Returns:
        Processed response for the voice assistant
    """
    # Store the query in Redis for session tracking
    # This helps maintain conversation context across multiple requests
    await redis_client.set(
        f"session:{voice_query.session_id}:last_query",
        voice_query.query,
        ex=3600  # Expire after 1 hour
    )
    
    # Simple keyword-based query processing
    # In production, this would use advanced NLP/AI services
    query_lower = voice_query.query.lower()  # Convert to lowercase for matching
    
    if "menu" in query_lower:  # Customer asking about menu
        menu = load_menu()
        return {
            "response": "Here are our menu categories: " + 
                       ", ".join(menu["categories"].keys()),
            "action": "show_menu",
            "session_id": voice_query.session_id
        }
    elif any(word in query_lower for word in ["price", "cost", "how much"]):  # Price inquiry
        return {
            "response": "I can help you with pricing. What specific item are you interested in?",
            "action": "request_item_details",
            "session_id": voice_query.session_id
        }
    elif "order" in query_lower:  # Customer wants to place order
        return {
            "response": "I'd be happy to help you place an order. What would you like to start with?",
            "action": "start_order",
            "session_id": voice_query.session_id
        }
    else:  # Default response for unrecognized queries
        return {
            "response": "I'm here to help you with our menu and placing orders. How can I assist you today?",
            "action": "general_help",
            "session_id": voice_query.session_id
        }

@app.post("/orders")
async def create_order(order: Order):
    """
    Create a new customer order and store it in Redis.
    
    Args:
        order: Complete order details including items and customer info
        
    Returns:
        Order confirmation with unique order ID
    """
    # Generate unique order ID using timestamp and phone number
    import time
    order_id = f"order_{int(time.time())}_{order.customer_phone[-4:]}"
    
    # Store order in Redis for persistence and retrieval
    # Convert order to JSON string for storage
    await redis_client.set(
        f"order:{order_id}",
        order.json(),  # Serialize order data to JSON
        ex=86400  # Expire after 24 hours
    )
    
    # Return confirmation to customer
    return {
        "order_id": order_id,
        "status": "confirmed",
        "message": f"Order placed successfully! Your order ID is {order_id}",
        "estimated_time": "25-30 minutes"  # Estimated preparation time
    }

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """
    Retrieve order details by order ID.
    
    Args:
        order_id: Unique identifier for the order
        
    Returns:
        Complete order details
        
    Raises:
        HTTPException: If order not found
    """
    # Retrieve order from Redis
    order_data = await redis_client.get(f"order:{order_id}")
    
    # Check if order exists
    if not order_data:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Parse JSON data and return order details
    return {"order_id": order_id, "order_data": json.loads(order_data)}

# Export the FastAPI app instance for Vercel deployment
# Vercel automatically detects the 'app' variable 