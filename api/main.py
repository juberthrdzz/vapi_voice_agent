import json  # Import JSON library to parse menu file
import os  # Import OS library to access environment variables
import logging  # Import logging for error tracking
import requests  # Import requests for HTTP calls to external services
from pathlib import Path  # Import Path to handle file paths
from typing import Dict, Any, Optional  # Import type hints for better code documentation

from fastapi import FastAPI, HTTPException  # Import FastAPI framework and HTTP exception handling
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware for cross-origin requests
from pydantic import BaseModel  # Import Pydantic for data validation
from upstash_redis import Redis  # Import Upstash Redis client

# Conditionally import Firestore if credentials are available
# This allows the app to run without Firebase configuration
try:
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        from google.cloud import firestore  # Import Firestore client for order storage
        firestore_client = firestore.Client()  # Initialize Firestore client
    else:
        firestore_client = None  # No Firestore if no credentials
except ImportError:
    firestore_client = None  # Firestore not available

# Configure logging for error tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application instance
app = FastAPI(title="Restaurant Voice Agent API")

# Add CORS middleware to allow requests from VAPI and other frontends
# This is essential for voice assistant integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin (VAPI, web browsers, etc.)
    allow_credentials=True,  # Allow cookies and authorization headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers in requests
)

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

class CartItem(BaseModel):
    """Model for items in the shopping cart"""
    item_id: str  # ID of the menu item being added to cart
    quantity: int = 1  # Number of this item to add (default 1)
    special_requests: Optional[str] = None  # Special requests for this specific item

class CartRequest(BaseModel):
    """Model for adding items to cart"""
    session_id: str  # Unique session identifier for the cart
    item_id: str  # Menu item to add to cart
    quantity: int = 1  # Number of items to add
    special_requests: Optional[str] = None  # Optional special instructions

class RemovePayload(BaseModel):
    """Model for removing items from cart via POST"""
    session_id: str  # Unique session identifier for the cart
    item_id: str  # Menu item to remove from cart

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

@app.get("/redis-test")
async def redis_test():
    """
    Test Redis connection.
    
    Returns:
        Redis connection status
    """
    try:
        # Test basic Redis operation
        test_key = "test_connection"
        redis_client.set(test_key, "working", ex=10)
        result = redis_client.get(test_key)
        
        return {
            "redis_status": "connected",
            "test_result": result,
            "message": "Redis is working correctly"
        }
    except Exception as e:
        return {
            "redis_status": "error",
            "error": str(e),
            "message": "Redis connection failed"
        }

@app.get("/menu")
async def get_menu():
    """
    Get the complete restaurant menu.
    Uses cached data for fast response.
    
    Returns:
        Complete menu with all categories and items
    """
    print("🍽️  API CALL: getFullMenu executed")  # Debug log
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
    print(f"📋 API CALL: getMenuCategory - category: {category}")  # Debug log
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
    redis_client.set(
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
    order_data = redis_client.get(f"order:{order_id}")
    
    # Check if order exists
    if not order_data:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Parse JSON data and return order details
    return {"order_id": order_id, "order_data": json.loads(order_data)}

# ============= CART ENDPOINTS =============
# These endpoints manage shopping cart functionality to avoid LLM memory issues

@app.post("/cart/add")
async def add_to_cart(cart_request: CartRequest):
    """
    Add an item to the shopping cart.
    This prevents the LLM from having to remember all items until checkout.
    
    Args:
        cart_request: Contains session_id, item_id, quantity, and special_requests
        
    Returns:
        Success message with updated cart summary
    """
    print(f"🛒 API CALL: addToCart - session: {cart_request.session_id}, item: {cart_request.item_id}, qty: {cart_request.quantity}")  # Debug log
    # Validate that the menu item exists
    menu = load_menu()
    
    # Find the item in the menu
    item_found = False
    item_details = None
    
    for category_name, category_items in menu["categories"].items():
        for item in category_items:
            if item["id"] == cart_request.item_id:
                item_found = True
                item_details = item
                break
        if item_found:
            break
    
    if not item_found:
        raise HTTPException(status_code=404, detail=f"Menu item {cart_request.item_id} not found")
    
    # Get current cart from Redis
    cart_key = f"cart:{cart_request.session_id}"
    cart_data = redis_client.get(cart_key)
    
    if cart_data:
        # Parse existing cart
        cart_items = json.loads(cart_data)
    else:
        # Create new cart
        cart_items = []
    
    # Check if item already exists in cart
    item_exists = False
    for i, existing_item in enumerate(cart_items):
        if existing_item["item_id"] == cart_request.item_id:
            # Update quantity of existing item
            cart_items[i]["quantity"] += cart_request.quantity
            item_exists = True
            break
    
    if not item_exists:
        # Add new item to cart
        cart_items.append({
            "item_id": cart_request.item_id,
            "name": item_details["name"],
            "price": item_details["price"],
            "quantity": cart_request.quantity,
            "special_requests": cart_request.special_requests
        })
    
    # Save updated cart to Redis (expire after 1 hour)
    redis_client.set(cart_key, json.dumps(cart_items), ex=3600)
    
    # Calculate cart summary
    total_items = sum(item["quantity"] for item in cart_items)
    total_amount = sum(item["price"] * item["quantity"] for item in cart_items)
    
    return {
        "message": f"Added {cart_request.quantity}x {item_details['name']} to cart",
        "cart_summary": {
            "total_items": total_items,
            "total_amount": round(total_amount, 2),
            "items_in_cart": len(cart_items)
        }
    }

@app.get("/cart/{session_id}")
async def get_cart(session_id: str):
    """
    Retrieve current cart contents for a session.
    
    Args:
        session_id: Unique identifier for the cart session
        
    Returns:
        Cart contents with items and totals
    """
    print(f"👀 API CALL: getCart - session: {session_id}")  # Debug log
    # Get cart from Redis
    cart_key = f"cart:{session_id}"
    cart_data = redis_client.get(cart_key)
    
    if not cart_data:
        return {
            "session_id": session_id,
            "items": [],
            "total_items": 0,
            "total_amount": 0.0
        }
    
    # Parse cart data
    cart_items = json.loads(cart_data)
    
    # Calculate totals
    total_items = sum(item["quantity"] for item in cart_items)
    total_amount = sum(item["price"] * item["quantity"] for item in cart_items)
    
    return {
        "session_id": session_id,
        "items": cart_items,
        "total_items": total_items,
        "total_amount": round(total_amount, 2)
    }

@app.delete("/cart/{session_id}/item/{item_id}")
async def remove_from_cart(session_id: str, item_id: str):
    """
    Remove a specific item from the cart.
    
    Args:
        session_id: Unique identifier for the cart session
        item_id: ID of the menu item to remove
        
    Returns:
        Success message with updated cart summary
    """
    # Get cart from Redis
    cart_key = f"cart:{session_id}"
    cart_data = redis_client.get(cart_key)
    
    if not cart_data:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Parse cart data
    cart_items = json.loads(cart_data)
    
    # Find and remove the item
    cart_items = [item for item in cart_items if item["item_id"] != item_id]
    
    # Update cart in Redis
    if cart_items:
        redis_client.set(cart_key, json.dumps(cart_items), ex=3600)
    else:
        # Delete empty cart
        redis_client.delete(cart_key)
    
    # Calculate new totals
    total_items = sum(item["quantity"] for item in cart_items)
    total_amount = sum(item["price"] * item["quantity"] for item in cart_items)
    
    return {
        "message": f"Removed item {item_id} from cart",
        "cart_summary": {
            "total_items": total_items,
            "total_amount": round(total_amount, 2),
            "items_in_cart": len(cart_items)
        }
    }

@app.post("/cart/{session_id}/checkout")
async def checkout_cart(session_id: str, customer_info: dict):
    """
    Convert cart to order and process checkout.
    
    Args:
        session_id: Unique identifier for the cart session
        customer_info: Must contain customer_name and customer_phone
        
    Returns:
        Order confirmation with order ID
    """
    print(f"💳 API CALL: checkoutCart - session: {session_id}, customer: {customer_info.get('customer_name', 'Unknown')}")  # Debug log
    # Get cart from Redis
    cart_key = f"cart:{session_id}"
    cart_data = redis_client.get(cart_key)
    
    if not cart_data:
        raise HTTPException(status_code=404, detail="Cart is empty or not found")
    
    # Parse cart data
    cart_items = json.loads(cart_data)
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Validate customer info
    if "customer_name" not in customer_info or "customer_phone" not in customer_info:
        raise HTTPException(status_code=400, detail="Customer name and phone are required")
    
    # Convert cart items to order format
    order_items = []
    total_amount = 0
    
    for cart_item in cart_items:
        order_items.append({
            "item_id": cart_item["item_id"],
            "quantity": cart_item["quantity"],
            "special_requests": cart_item.get("special_requests")
        })
        total_amount += cart_item["price"] * cart_item["quantity"]
    
    # Create order
    order = Order(
        customer_phone=customer_info["customer_phone"],
        items=[OrderItem(**item) for item in order_items],
        total_amount=round(total_amount, 2)
    )
    
    # Generate order ID
    import time
    order_id = f"order_{int(time.time())}_{order.customer_phone[-4:]}"
    
    # Add customer name to order data
    order_data = order.dict()
    order_data["customer_name"] = customer_info["customer_name"]
    order_data["special_instructions"] = customer_info.get("special_instructions", "")
    
    # Store order in Redis
    redis_client.set(
        f"order:{order_id}",
        json.dumps(order_data),
        ex=86400  # Expire after 24 hours
    )
    
    # Clear the cart after successful checkout
    redis_client.delete(cart_key)
    
    # ============= SEND ORDER TO FIREBASE =============
    # After successful checkout, send order data to external Firebase server
    
    # Get metadata from Redis hash storage
    metadata = get_cart_metadata(session_id)
    
    # Load menu for item name lookup
    menu = load_menu()
    
    # Build human-readable platillos string using menu lookup
    platillos_string = build_platillos_string(cart_items, menu)
    
    # Construct payload with Spanish keys as required
    order_payload = {
        # Required fields (marked with ✳ in requirements)
        "nombre_cliente": metadata.get("nombre_cliente", customer_info.get("customer_name", "")),
        "telefono": metadata.get("telefono", customer_info.get("customer_phone", "")),
        "tipo_de_pedido": metadata.get("tipo_de_pedido", ""),  # pickup|delivery
        "platillos": platillos_string,  # Human-readable string like "2 Empanadas carne, 1 Papas"
        "precio_total": round(total_amount, 2),  # Numeric total price
        # Optional fields
        "metodo_pago": metadata.get("metodo_pago", ""),
        "notas": metadata.get("notas", ""),
        "direccion_cliente": metadata.get("direccion_cliente", ""),
    }
    
    # Send order to Firebase server (async, non-blocking)
    # Errors are logged but don't affect the customer response
    await send_order_to_firebase(order_payload)
    
    # Return confirmation (unchanged response to maintain API compatibility)
    return {
        "order_id": order_id,
        "status": "confirmed",
        "message": f"Order placed successfully! Your order ID is {order_id}",
        "total_amount": round(total_amount, 2),
        "estimated_time": "25-30 minutes"
    }

@app.post("/cart/remove")
async def remove_item(payload: RemovePayload):
    """
    Remove one item from the user's cart (POST variant for Vapi).
    
    Args:
        payload: Contains session_id and item_id to remove
        
    Returns:
        Success confirmation
    """
    print(f"🗑️  API CALL: removeFromCart - session: {payload.session_id}, item: {payload.item_id}")  # Debug log
    # Get cart from Redis
    cart_key = f"cart:{payload.session_id}"
    cart_data = redis_client.get(cart_key)
    
    if not cart_data:
        return {"ok": True, "message": "Cart was already empty"}
    
    # Parse cart data
    cart_items = json.loads(cart_data)
    
    # Remove the specified item
    cart_items = [item for item in cart_items if item["item_id"] != payload.item_id]
    
    # Update cart in Redis
    if cart_items:
        redis_client.set(cart_key, json.dumps(cart_items), ex=3600)
    else:
        # Delete empty cart
        redis_client.delete(cart_key)
    
    return {"ok": True}

# ============= ORDER SUBMISSION HELPERS =============

def get_cart_metadata(session_id: str) -> Dict[str, str]:
    """
    Retrieve cart metadata from Redis hash storage.
    
    Args:
        session_id: Unique session identifier for the cart
        
    Returns:
        Dictionary with metadata fields (empty strings for missing values)
    """
    try:
        # Get metadata hash from Redis using the pattern meta:{session_id}
        meta_key = f"meta:{session_id}"
        meta_data = redis_client.hgetall(meta_key)  # Get all hash fields
        
        # Convert bytes to strings and provide defaults for missing fields
        return {
            "nombre_cliente": meta_data.get("nombre_cliente", "").decode() if meta_data.get("nombre_cliente") else "",
            "telefono": meta_data.get("telefono", "").decode() if meta_data.get("telefono") else "",
            "tipo_de_pedido": meta_data.get("tipo_de_pedido", "").decode() if meta_data.get("tipo_de_pedido") else "",
            "metodo_pago": meta_data.get("metodo_pago", "").decode() if meta_data.get("metodo_pago") else "",
            "notas": meta_data.get("notas", "").decode() if meta_data.get("notas") else "",
            "direccion_cliente": meta_data.get("direccion_cliente", "").decode() if meta_data.get("direccion_cliente") else "",
        }
    except Exception as e:
        logger.warning(f"Error getting metadata for session {session_id}: {e}")
        # Return empty strings for all fields if metadata retrieval fails
        return {
            "nombre_cliente": "",
            "telefono": "",
            "tipo_de_pedido": "",
            "metodo_pago": "",
            "notas": "",
            "direccion_cliente": "",
        }

def build_platillos_string(cart_items: list, menu: Dict[str, Any]) -> str:
    """
    Build a human-readable string of ordered items using menu lookup.
    
    Args:
        cart_items: List of items in the cart
        menu: Menu data for name lookup
        
    Returns:
        String like "2 Empanadas carne, 1 Papas"
    """
    # Create a lookup dictionary for fast item name retrieval
    item_lookup = {}
    for category_name, category_items in menu["categories"].items():
        for item in category_items:
            item_lookup[item["id"]] = item["name"]  # Map item_id to name
    
    # Build list of "quantity itemName" strings
    platillo_parts = []
    for cart_item in cart_items:
        item_id = cart_item["item_id"]
        quantity = cart_item["quantity"]
        
        # Get item name from lookup or use item_id as fallback
        item_name = item_lookup.get(item_id, item_id)
        platillo_parts.append(f"{quantity} {item_name}")
    
    # Join all items with comma and space
    return ", ".join(platillo_parts)

async def send_order_to_firebase(order_payload: Dict[str, Any]) -> bool:
    """
    Send order to external Firebase server.
    
    Args:
        order_payload: Complete order data with Spanish keys
        
    Returns:
        True if successful, False if failed (logged but not raised)
    """
    try:
        # Get restaurant ID from environment variable or use default
        restaurant_id = os.getenv("RESTAURANT_ID", "todoEmpanadas1")
        order_payload["id_restaurante"] = restaurant_id
        
        # Send POST request to Firebase server with 3 second timeout
        response = requests.post(
            "https://vapi-firebase-server.fly.dev/create-order",
            json=order_payload,
            timeout=3  # 3 second timeout as specified
        )
        
        # Log successful submission
        logger.info(f"Order sent to Firebase - Status: {response.status_code}")
        return True
        
    except requests.exceptions.Timeout:
        # Log timeout but don't raise exception
        logger.warning("Firebase order submission timed out after 3 seconds")
        return False
    except Exception as e:
        # Log any other errors but don't raise exception
        logger.error(f"Error sending order to Firebase: {e}")
        return False

# Export the FastAPI app instance for Vercel deployment
# Vercel will automatically use the 'app' instance 