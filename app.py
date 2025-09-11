%%writefile app.py
# ------------------------------ app.py ------------------------------
# Streamlit front-end with 5 tabs:
# 1) Nearby Stores (map + filters)          2) Product Compare
# 3) Shopping List Optimizer                4) Alerts (demo)
# 5) Chatbot (Gemini + tools)

import streamlit as st
import pandas as pd

# Import UI functions and chatbot from agent.py
from agent import (
    ui_search_stores, ui_compare_prices, ui_shopping_list,
    ui_get_directions, run_agent, subscribe_alert, simulate_restock
)

# Basic page settings
st.set_page_config(page_title="FindMyStore", layout="wide")
st.title("🏬 FindMyStore — Demo")

# Sidebar filters — applied to multiple tabs
with st.sidebar:
    st.header("Search Filters")
    city = st.text_input("City", value="Hyderabad")
    category = st.selectbox("Category", ["", "grocery", "pharmacy", "electronics", "clothing", "bakery", "restaurant"])
    radius = st.slider("Radius (km)", 1, 20, 6)
    open_now = st.checkbox("Open now", value=False)
    st.caption("Tip: Leave category blank for a broad search.")

# Tabs for features
tabs = st.tabs(["🗺️ Nearby Stores", "🔍 Product Compare", "🛒 Shopping List", "🔔 Alerts (Demo)", "🤖 Chatbot"])

# -------------------- Tab 1: Nearby Stores --------------------
with tabs[0]:
    st.subheader("Nearby Store Finder + Maps Integration")
    if st.button("Find Stores", type="primary"):
        results = ui_search_stores(city, category or None, radius, open_now)
        if not results:
            st.warning("No stores found. Try a different category or radius.")
        else:
            st.success(f"Found {len(results)} store(s).")
            # Map: expects DataFrame with lat/lon columns
            df_map = pd.DataFrame([{"lat": r["lat"], "lon": r["lng"]} for r in results if r.get("lat") and r.get("lng")])
            if not df_map.empty:
                st.map(df_map, size=100)

            # Render cards with main details
            for s in results:
                with st.container():
                    left, right = st.columns([0.7, 0.3])
                    with left:
                        badge = "✅ Verified" if s.get("verified") else "⚪ Unverified"
                        stars = "⭐" * int(round(s.get("rating", 4.0)))
                        st.markdown(f"**{s['name']}**  \n{badge} · {stars}")
                        st.write(f"Category: {s.get('category','—')}  |  City: {s.get('city','—')}")
                        if s.get("address"):
                            st.write(f"Address: {s['address']}")
                        if s.get("hours"):
                            st.write(f"Hours: {s['hours']}")
                    with right:
                        link = f"https://www.google.com/maps?q={s['lat']},{s['lng']}"
                        st.link_button("📍 View on Map", link)

# -------------------- Tab 2: Product Compare --------------------
with tabs[1]:
    st.subheader("Product Availability + Price Comparison")
    col1, col2 = st.columns([0.6,0.4])
    with col1:
        product = st.text_input("Product name", value="XYZ Shampoo")
        if st.button("Compare Prices"):
            df = ui_compare_prices(product, city, category or None, radius)
            if df.empty:
                st.warning("No data.")
            else:
                # Highlight the cheapest available option
                cheapest = df[df["qty"] > 0].sort_values(by="price", ascending=True).head(1)
                if not cheapest.empty:
                    c = cheapest.iloc[0]
                    st.success(f"Cheapest: **{c['store']}** — ₹{int(c['price'])} (qty {int(c['qty'])})")
                st.dataframe(df, use_container_width=True)
    with col2:
        st.info("Tip: pick a Category in the sidebar to narrow the store set used for comparison.")

# -------------------- Tab 3: Shopping List --------------------
with tabs[2]:
    st.subheader("Smart Shopping List + Budget Mode")
    items = st.text_area("Enter items (comma-separated)", value="Rice 10kg, XYZ Shampoo, Milk Lotion")
    if st.button("Optimize Shopping List"):
        res = ui_shopping_list(items, city, category or None, radius)
        if "message" in res:
            st.warning(res["message"])
        else:
            if res["plan"]:
                for p in res["plan"]:
                    with st.container():
                        st.markdown(f"**Store #{p['store_id']}** — Subtotal: ₹{int(p['subtotal'])}")
                        lines = [f"- {k}: ₹{int(v)}" for k, v in p["items"].items()]
                        st.markdown("\n".join(lines))
                st.success(f"Total estimated cost: ₹{int(res['total_cost'])}")
            if res["not_found"]:
                st.error(f"Not found: {', '.join(res['not_found'])}")
            if res["covered_all"]:
                st.caption("✅ All items covered")

# -------------------- Tab 4: Alerts (Demo) --------------------
with tabs[3]:
    st.subheader("Real-Time Stock & Deal Alerts (Demo)")
    a1, a2 = st.columns(2)
    with a1:
        sub_prod = st.text_input("Subscribe for product", value="XYZ Shampoo")
        sub_city = st.text_input("City for alerts", value=city)
        if st.button("Subscribe"):
            st.success(subscribe_alert(sub_prod, sub_city)["message"])
    with a2:
        sim_prod = st.text_input("Simulate restock for product", value="XYZ Shampoo")
        sim_store = st.number_input("Store ID to restock", value=1, min_value=1, step=1)
        if st.button("Simulate Restock"):
            st.success(simulate_restock(sim_prod, int(sim_store))["message"])
    st.caption("Note: Alerts are in-memory for demo. Use Firestore for persistence.")

# -------------------- Tab 5: Chatbot --------------------
with tabs[4]:
    st.subheader("Voice + AI Chatbot Assistant")
    st.caption("Examples:\n- Where can I get a laptop bag under ₹1000 near me?\n- Find an open pharmacy in Hyderabad within 4 km.\n- Optimize this list: rice 10kg, xyz shampoo, milk lotion")
    query = st.text_input("Your message")
    if st.button("Ask 🤖"):
        if query.strip():
            with st.spinner("Thinking..."):
                st.success(run_agent(query))
        else:
            st.warning("Type something first 🙂")
