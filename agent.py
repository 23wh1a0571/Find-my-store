from getpass import getpass
import textwrap, os


GEMINI_KEY = getpass("Enter your GOOGLE_API_KEY (Gemini): ")
MAPS_KEY  = getpass("Enter your MAPS_API_KEY (Google Maps) [press Enter to skip]: ")


env_text = textwrap.dedent(f"""
GOOGLE_API_KEY={GEMINI_KEY}
MAPS_API_KEY={MAPS_KEY}
""").strip()


with open(".env", "w") as f:
    f.write(env_text)

print("✅ .env written (keys NOT shown).")


%%writefile agent.py
# ------------------------------ agent.py ------------------------------
# This file implements ALL 6 requested features for FindMyStore:
# 1) Nearby Store Finder + Maps/filters
# 2) Product Availability + Price Comparison
# 3) Smart Shopping List + Budget Mode
# 4) Real-Time Stock & Deal Alerts (demo)
# 5) Voice + AI Chatbot (Gemini) that can call tools
# 6) Community Reviews & Verified Stores (from rating or simulated)

import os, json, random
from typing import List, Dict, Any, Tuple

# Load API keys from .env
from dotenv import load_dotenv
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")   # Gemini key
MAPS_API_KEY   = os.getenv("MAPS_API_KEY", "")     # Google Maps key (optional for demo)

# LangChain + Gemini LLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, Tool, AgentType

# Utilities for geo + data
import pandas as pd
from geopy.distance import geodesic

# Google Maps client (if key provided)
try:
    import googlemaps
    gmaps = googlemaps.Client(key=MAPS_API_KEY) if MAPS_API_KEY else None
except Exception:
    gmaps = None

# --------- Category mapping (Dialogflow-friendly naming -> Places types) ----------
CATEGORY_TO_TYPE = {
    "grocery": "grocery_or_supermarket",
    "pharmacy": "pharmacy",
    "electronics": "electronics_store",
    "clothing": "clothing_store",
    "bakery": "bakery",
    "restaurant": "restaurant",
}

# ---------------- Fallback (simulated) store data if Maps API not used ----------------
stores_fallback = [
    {"id": 1, "name": "SmartMart Jubilee Hills", "city": "Hyderabad", "category": "grocery",
     "hours": "9am-9pm", "lat": 17.433, "lng": 78.403, "rating": 4.5, "verified": True},
    {"id": 2, "name": "MediCare Pharmacy Banjara", "city": "Hyderabad", "category": "pharmacy",
     "hours": "24/7", "lat": 17.412, "lng": 78.448, "rating": 4.3, "verified": True},
    {"id": 3, "name": "ElectroHub Secunderabad", "city": "Hyderabad", "category": "electronics",
     "hours": "10am-8pm", "lat": 17.444, "lng": 78.501, "rating": 4.1, "verified": False},
    {"id": 4, "name": "StyleStreet Hitech City", "city": "Hyderabad", "category": "clothing",
     "hours": "11am-9pm", "lat": 17.452, "lng": 78.381, "rating": 4.6, "verified": True},
]

# -------------- Inventory with price (qty + ₹ price). Keys are store IDs ---------------
inventory: Dict[int, Dict[str, Dict[str, float]]] = {
    1: {"XYZ Shampoo": {"qty": 12, "price": 150}, "Milk Lotion": {"qty": 0, "price": 199}, "Rice 10kg": {"qty": 8, "price": 489}},
    2: {"XYZ Shampoo": {"qty":  4, "price": 155}, "Milk Lotion": {"qty": 7, "price": 189}},
    3: {"Laptop Bag":  {"qty":  6, "price": 899}, "USB Cable":   {"qty": 15, "price": 149}},
    4: {"T-Shirt":     {"qty": 10, "price": 399}},
}

# Dynamic inventory for live-fetched stores (created on demand)
dynamic_inventory: Dict[int, Dict[str, Dict[str, float]]] = {}

# Cache of the most recently fetched stores (for compare & shopping list)
_last_store_cache: List[Dict[str, Any]] = []

# --------------------------- Helpers: geo + links --------------------------------
def geocode_city(city: str) -> Tuple[float, float]:
    """Geocode city name -> (lat, lng). Falls back to Hyderabad center if Maps disabled."""
    if gmaps:
        ge = gmaps.geocode(city)
        if ge and ge[0]["geometry"]["location"]:
            loc = ge[0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
    return (17.3850, 78.4867)  # Hyderabad fallback

def maps_place_link(lat: float, lng: float, place_id: str = None) -> str:
    """Return a Google Maps link to a place or lat/lng."""
    if place_id:
        return f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={place_id}"
    return f"https://www.google.com/maps?q={lat},{lng}"

def maps_directions_link(dest_lat: float, dest_lng: float, place_id: str = None, origin: str = None) -> str:
    """Return a Google Maps directions URL."""
    base = "https://www.google.com/maps/dir/?api=1"
    parts = [base, f"destination={dest_lat},{dest_lng}"]
    if place_id:
        parts.append(f"destination_place_id={place_id}")
    if origin:
        parts.append(f"origin={origin}")
    parts.append("travelmode=driving")
    return "&".join(parts)

# --------------------- Fetch stores (Maps API or fallback) -----------------------
def fetch_stores(city: str, category: str = None, radius_km: float = 6.0, open_now: bool = False) -> List[Dict[str, Any]]:
    """Fetch stores by city/category + open status. Uses Google Maps if available, else simulated."""
    global _last_store_cache
    results: List[Dict[str, Any]] = []

    if gmaps:
        lat, lng = geocode_city(city)
        ptype = CATEGORY_TO_TYPE.get(category or "", "store")  # "store" is broad fallback
        places = gmaps.places_nearby(
            location=(lat, lng),
            radius=int(radius_km * 1000),
            type=ptype if ptype != "store" else None,  # None for broad search
            open_now=open_now if ptype != "store" else None,
        )
        pid = 1
        for p in places.get("results", []):
            loc = p.get("geometry", {}).get("location", {})
            rating = float(p.get("rating", 4.2))
            urt = int(p.get("user_ratings_total", 20))
            results.append({
                "id": pid,                                  # Local sequential ID for our UI
                "place_id": p.get("place_id"),
                "name": p.get("name"),
                "city": city,
                "category": category or "general",
                "hours": "—",
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
                "address": p.get("vicinity", ""),
                "rating": rating,
                "verified": True if (rating >= 4.3 and urt >= 30) else False,  # Simple rule
            })
            pid += 1
    else:
        # Simulated fallback results
        results = [s for s in stores_fallback if s["city"].lower() == city.lower()]
        if category:
            results = [s for s in results if s["category"] == category]

    _last_store_cache = results[:]  # cache for later use
    return results

# ------------------------- Inventory helpers ------------------------------------
def ensure_dynamic_inventory(store_id: int, product: str):
    """Give a live-fetched store a made-up stock+price so the demo feels real."""
    di = dynamic_inventory.setdefault(store_id, {})
    if product not in di:
        di[product] = {"qty": random.randint(0, 12),
                       "price": random.choice([79, 99, 129, 149, 179, 199, 249, 299, 349, 399, 899, 999])}

def get_inventory(store_id: int) -> Dict[str, Dict[str, float]]:
    """Return inventory dict (fallback + dynamic)."""
    if store_id in inventory:
        return inventory[store_id]
    return dynamic_inventory.setdefault(store_id, {})

def check_stock(store_id: int, product: str) -> Dict[str, Any]:
    """Return {'qty', 'price'} for a product in a store."""
    inv = get_inventory(store_id)
    if product not in inv:
        ensure_dynamic_inventory(store_id, product)
        inv = get_inventory(store_id)
    data = inv.get(product, {"qty": 0, "price": None})
    return {"store_id": store_id, "product": product, "qty": int(data["qty"]), "price": data["price"]}

def find_cheapest(product: str, max_price: float = None) -> Dict[str, Any]:
    """Search cached stores for cheapest available product (with optional max price)."""
    search_space = _last_store_cache[:] or stores_fallback[:]
    best = None
    for s in search_space:
        info = check_stock(s["id"], product)
        if info["qty"] > 0 and info["price"] is not None:
            if max_price is not None and info["price"] > max_price:
                continue
            if best is None or info["price"] < best["price"]:
                best = {**info, "store": s}
    return best or {"message": f"No available '{product}' found within criteria."}

def shopping_list_optimize(products: List[str]) -> Dict[str, Any]:
    """Greedy set-cover style plan to buy a list of items at minimum total cost across stores."""
    needed = set([p.strip() for p in products if p.strip()])
    if not needed:
        return {"message": "No items in shopping list."}

    search_space = _last_store_cache[:] or stores_fallback[:]
    offerings = {}
    for s in search_space:
        sid = s["id"]
        o = {}
        for item in needed:
            info = check_stock(sid, item)
            if info["qty"] > 0 and info["price"] is not None:
                o[item] = info["price"]
        if o:
            offerings[sid] = o

    chosen = []
    remaining = set(needed)
    total_cost = 0.0

    while remaining:
        best_sid, best_cover, best_score = None, set(), float("inf")
        for sid, offer in offerings.items():
            cover = remaining.intersection(offer.keys())
            if cover:
                cost = sum(offer[i] for i in cover)
                score = cost / len(cover)  # lower is better
                if score < best_score:
                    best_sid, best_cover, best_score = sid, cover, score

        if not best_sid:
            break  # cannot cover all items

        chosen.append({
            "store_id": best_sid,
            "items": {i: offerings[best_sid][i] for i in best_cover},
            "subtotal": sum(offerings[best_sid][i] for i in best_cover),
        })
        total_cost += chosen[-1]["subtotal"]
        remaining -= best_cover
        offerings.pop(best_sid, None)

    return {
        "covered_all": len(remaining) == 0,
        "plan": chosen,
        "not_found": list(remaining),
        "total_cost": round(total_cost, 2),
    }

# ---------------------- Alerts (demo: in-memory) ----------------------
_subscriptions: List[Dict[str, Any]] = []  # e.g., {"product": "XYZ Shampoo", "city": "Hyderabad"}

def subscribe_alert(product: str, city: str):
    """Remember what the user wants to be alerted for (demo only)."""
    _subscriptions.append({"product": product.strip(), "city": city.strip()})
    return {"message": f"Subscribed to '{product}' alerts in {city} (demo)."}

def simulate_restock(product: str, store_id: int, qty: int = 10):
    """Pretend the store restocked; update inventory and 'notify' subscribers (demo)."""
    inv = get_inventory(store_id)
    if product not in inv:
        inv[product] = {"qty": qty, "price": random.choice([99, 129, 149, 199, 249, 299])}
    else:
        inv[product]["qty"] = max(0, inv[product]["qty"]) + qty
    hits = [s for s in _subscriptions if s["product"].lower() == product.lower()]
    return {"message": f"Restocked '{product}' at store {store_id}. Alerts notified: {len(hits)} (demo)."}

# -------------------- Public helpers for Streamlit UI -----------------
def ui_search_stores(city: str, category: str = None, radius_km: float = 6.0, open_now: bool = False):
    """UI wrapper for fetching stores."""
    return fetch_stores(city, category, radius_km, open_now)

def ui_compare_prices(product: str, city: str = None, category: str = None, radius_km: float = 6.0):
    """UI wrapper that returns a DataFrame of availability+price across stores."""
    if city:
        fetch_stores(city, category, radius_km)  # refresh cache
    rows = []
    for s in _last_store_cache or stores_fallback:
        info = check_stock(s["id"], product)
        rows.append({
            "store_id": s["id"],
            "store": s.get("name"),
            "city": s.get("city"),
            "category": s.get("category"),
            "verified": s.get("verified", False),
            "rating": s.get("rating"),
            "qty": info["qty"],
            "price": info["price"],
            "map": maps_place_link(s.get("lat"), s.get("lng"), s.get("place_id")),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["qty","price"], ascending=[False, True])
    return df

def ui_shopping_list(products_csv: str, city: str = None, category: str = None, radius_km: float = 6.0):
    """UI wrapper for shopping list optimization."""
    if city:
        fetch_stores(city, category, radius_km)
    items = [x.strip() for x in products_csv.split(",") if x.strip()]
    return shopping_list_optimize(items)

def ui_get_directions(store_id: int, origin: str = None) -> str:
    """Return a directions link for the chosen store."""
    s = next((x for x in (_last_store_cache or stores_fallback) if x["id"] == store_id), None)
    if not s:
        return "Store not found."
    return maps_directions_link(s["lat"], s["lng"], s.get("place_id"), origin)

# ------------------------ LangChain Agent (Gemini) --------------------
llm = ChatGoogleGenerativeAI(
    model="models/gemini-1.5-pro-latest",  # Gemini 1.5 Pro
    temperature=0.3,
    google_api_key=GOOGLE_API_KEY,
)

# Tool: find stores (input: "city|category|radius_km|open_now")
def _tool_find_stores(q: str) -> str:
    parts = [p.strip() or None for p in q.split("|")]
    city = parts[0] if len(parts) > 0 else "Hyderabad"
    category = parts[1] if len(parts) > 1 else None
    radius = float(parts[2]) if len(parts) > 2 and parts[2] else 6.0
    open_now = (parts[3].lower() == "true") if len(parts) > 3 and parts[3] else False
    out = fetch_stores(city, category, radius, open_now)
    return json.dumps(out, ensure_ascii=False)

# Tool: check inventory (input: "store_id|product")
def _tool_check_inventory(q: str) -> str:
    sid, product = q.split("|", 1)
    out = check_stock(int(sid), product.strip())
    return json.dumps(out, ensure_ascii=False)

# Tool: find cheapest (input: "product|max_price(optional)")
def _tool_find_cheapest(q: str) -> str:
    parts = [p.strip() for p in q.split("|")]
    product = parts[0]
    max_price = float(parts[1]) if len(parts) > 1 and parts[1] else None
    out = find_cheapest(product, max_price)
    return json.dumps(out, ensure_ascii=False)

# Tool: optimize shopping list (input: "item1,item2,...")
def _tool_shopping_list(q: str) -> str:
    items = [x.strip() for x in q.split(",") if x.strip()]
    return json.dumps(shopping_list_optimize(items), ensure_ascii=False)

# Tool: directions link (input: "store_id|origin(optional)")
def _tool_get_directions(q: str) -> str:
    parts = [p.strip() for p in q.split("|")]
    sid = int(parts[0])
    origin = parts[1] if len(parts) > 1 and parts[1] else None
    return ui_get_directions(sid, origin)

# Tool: subscribe alerts (input: "product|city")
def _tool_subscribe_alert(q: str) -> str:
    product, city = q.split("|", 1)
    return json.dumps(subscribe_alert(product, city), ensure_ascii=False)

# Register tools with the agent
tools = [
    Tool(name="FindStoreTool",       func=_tool_find_stores,
         description="Find stores by city/category. Input: 'city|category|radius_km|open_now' (open_now true/false)."),
    Tool(name="CheckInventoryTool",  func=_tool_check_inventory,
         description="Check product stock/price in a store. Input: 'store_id|product'."),
    Tool(name="FindCheapestTool",    func=_tool_find_cheapest,
         description="Find the cheapest store for a product. Input: 'product|max_price(optional)'."),
    Tool(name="ShoppingListTool",    func=_tool_shopping_list,
         description="Optimize shopping list across stores. Input: 'item1,item2,...'."),
    Tool(name="GetDirectionsTool",   func=_tool_get_directions,
         description="Get Google Maps directions link. Input: 'store_id|origin(optional)'."),
    Tool(name="SubscribeAlertTool",  func=_tool_subscribe_alert,
         description="Subscribe to restock alerts (demo). Input: 'product|city'."),
]

# Use Conversational agent so it remembers context in a session
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=False,
)
# Keep chat history inside Python memory so context works
chat_history: list[tuple[str, str]] = []

def run_agent(query: str) -> str:
    global chat_history
    try:
        response = agent.invoke({
            "input": query,
            "chat_history": chat_history
        })
        if isinstance(response, dict):
            answer = response.get("output", response.get("output_text", str(response)))
        else:
            answer = str(response)
        # store turn in memory
        chat_history.append(("user", query))
        chat_history.append(("assistant", answer))
        return answer
    except Exception as e:
        return f"Agent error: {e}"
