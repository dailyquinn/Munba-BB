import sqlite3
import requests
import time
from datetime import datetime
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import os
import threading

# Use environment variable for database path (Docker compatibility)
DB_PATH = os.getenv('DATABASE_PATH', 'market_prices.db')

# Resolve project root (one level above this Scripts/ folder)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


# --- Market Price DB Setup ---
def init_market_db():
    """
    Initializes the SQLite database for market prices.
    - Creates the `market_prices` table if it doesn't exist.
    - Attempts to set the journal mode to WAL (Write-Ahead Logging) for better concurrency.
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        try:
            conn.execute('PRAGMA journal_mode=WAL')
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not enable WAL mode: {e}")
        
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS market_prices (
            typeID INTEGER PRIMARY KEY,
            buy_price REAL,
            sell_price REAL,
            updated_at TEXT
        )''')
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except sqlite3.OperationalError as e:
        print(f"Database initialization error: {e}")
init_market_db()

# --- Market Price Updater ---
def update_market_prices(type_ids):
    """
    Fetches market prices from Fuzzwork's API and updates the local database.
    - Processes type IDs in batches to be considerate to the API.
    - Uses a new database connection for each batch to minimize lock contention.
    - Stores the max buy price and min sell price for Jita 4-4.

    Args:
        type_ids (list): A list of integer type IDs to update.
    """
    # Jita 4-4: 60003760
    BATCH_SIZE = 100
    all_prices = {}
    now = datetime.now().isoformat()
    
    for i in range(0, len(type_ids), BATCH_SIZE):
        batch = type_ids[i:i+BATCH_SIZE]
        url = f"https://market.fuzzwork.co.uk/aggregates/?station=60003760&types={','.join(str(tid) for tid in batch)}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            
            # Use a separate connection for each batch to avoid lock issues
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            conn.execute('PRAGMA journal_mode=WAL')  # Use WAL mode for better concurrency
            c = conn.cursor()
            
            for tid in batch:
                buy_price = data.get(str(tid), {}).get('buy', {}).get('max', 0)
                sell_price = data.get(str(tid), {}).get('sell', {}).get('min', 0)
                c.execute('REPLACE INTO market_prices (typeID, buy_price, sell_price, updated_at) VALUES (?, ?, ?, ?)', 
                         (tid, buy_price, sell_price, now))
                all_prices[int(tid)] = buy_price
            
            conn.commit()
            conn.close()
            time.sleep(1)  # Be nice to Fuzzwork
            
        except Exception as e:
            print(f"Error updating batch {i//BATCH_SIZE+1}: {e}")
            continue
    
    return all_prices

# --- Market Price Fetcher ---
def get_prices_from_db(type_ids):
    """
    Retrieves market prices for a list of type IDs from the local SQLite database.

    Args:
        type_ids (list): A list of integer type IDs to fetch.

    Returns:
        dict: A dictionary mapping each type ID to its price and last update timestamp.
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL')
        c = conn.cursor()
        result = {}
        for tid in type_ids:
            c.execute('SELECT typeID, buy_price, sell_price, updated_at FROM market_prices WHERE typeID = ?', (tid,))
            row = c.fetchone()
            if row:
                result[tid] = {'price': row[1], 'last_updated': row[3]}  # row[1] = buy_price, row[3] = updated_at
            else:
                result[tid] = {'price': None, 'last_updated': None}
        conn.close()
        return result
    except sqlite3.OperationalError as e:
        print(f"Database error in get_prices_from_db: {e}")
        return {tid: {'price': None, 'last_updated': None} for tid in type_ids}

# In-memory cache for contracts to reduce ESI calls.
stored_contracts = []
contracts_cache = {
    'timestamp': 0,
    'contracts': []
}

# --- Background Tasks ---

def get_all_cached_type_ids():
    """
    Retrieves all unique typeIDs currently stored in the market prices database.
    Used by the hourly refresh task to know which items to update.
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL')
        c = conn.cursor()
        c.execute('SELECT typeID FROM market_prices')
        rows = c.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except sqlite3.OperationalError as e:
        print(f"Database error in get_all_cached_type_ids: {e}")
        return []

def hourly_market_refresh():
    """
    A background thread that automatically refreshes all cached market prices
    at the top of every hour. This keeps the price data reasonably fresh without
    needing manual intervention.
    """
    import datetime
    while True:
        try:
            # Calculate seconds until next hour
            now = datetime.datetime.now()
            next_hour = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
            seconds_until_next_hour = (next_hour - now).total_seconds()
            
            print(f"[Market Refresh] Next refresh in {seconds_until_next_hour/60:.1f} minutes at {next_hour.strftime('%H:%M')}")
            time.sleep(seconds_until_next_hour)
            
            # Now refresh at the top of the hour
            type_ids = get_all_cached_type_ids()
            if type_ids:
                print(f"[Market Refresh] Refreshing {len(type_ids)} type_ids at {datetime.datetime.now().strftime('%H:%M:%S')}...")
                update_market_prices(type_ids)
                print(f"[Market Refresh] Refresh completed at {datetime.datetime.now().strftime('%H:%M:%S')}")
            else:
                print("[Market Refresh] No type_ids cached yet, skipping refresh.")
        except Exception as e:
            print(f"[Market Refresh] Error during refresh: {e}")
            time.sleep(300)  # Wait 5 minutes before trying again

def cleanup_old_quotes():
    """
    Scans the database and removes quote entries that are older than 7 days.
    This prevents the quotes table from growing indefinitely.
    """
    try:
        # Calculate timestamp for 7 days ago
        seven_days_ago = int(time.time()) - (7 * 24 * 60 * 60)
        
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL')
        c = conn.cursor()
        
        # Count quotes to be deleted (for logging)
        c.execute('SELECT COUNT(*) FROM quotes WHERE created_at < ?', (seven_days_ago,))
        count_to_delete = c.fetchone()[0]
        
        # Delete old quotes
        c.execute('DELETE FROM quotes WHERE created_at < ?', (seven_days_ago,))
        conn.commit()
        conn.close()
        
        if count_to_delete > 0:
            print(f"[Quote Cleanup] Deleted {count_to_delete} quotes older than 7 days")
        else:
            print("[Quote Cleanup] No old quotes to delete")
            
    except sqlite3.OperationalError as e:
        print(f"[Quote Cleanup] Database error during cleanup: {e}")
    except Exception as e:
        print(f"[Quote Cleanup] Error during quote cleanup: {e}")

def daily_quote_cleanup():
    """
    A background thread that schedules the `cleanup_old_quotes` function
    to run once every day at midnight UTC.
    """
    import datetime
    while True:
        try:
            # Calculate seconds until next midnight UTC
            now = datetime.datetime.utcnow()
            next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
            seconds_until_midnight = (next_midnight - now).total_seconds()
            
            print(f"[Quote Cleanup] Next cleanup in {seconds_until_midnight/3600:.1f} hours at {next_midnight.strftime('%Y-%m-%d %H:%M UTC')}")
            time.sleep(seconds_until_midnight)
            
            # Run cleanup at midnight UTC
            print(f"[Quote Cleanup] Starting daily cleanup at {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            cleanup_old_quotes()
            print(f"[Quote Cleanup] Daily cleanup completed at {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
        except Exception as e:
            print(f"[Quote Cleanup] Error in daily cleanup scheduler: {e}")
            time.sleep(3600)  # Wait 1 hour before trying again

# Start background thread for hourly refresh
refresh_thread = threading.Thread(target=hourly_market_refresh, daemon=True)
refresh_thread.start()

# Start background thread for daily quote cleanup
cleanup_thread = threading.Thread(target=daily_quote_cleanup, daemon=True)
cleanup_thread.start()

# --- FastAPI Application Setup ---

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Legacy in-memory contract store.
contracts = []

class Contract(BaseModel):
    issuer: str
    location: str
    items: str

@app.post("/api/contracts/")
def contracted(contract: Contract):
    contracts.append(contract)
    print("New contract:", contract)
    return {"Message": "Contract stored."}


@app.get("/api/market_prices/")
async def get_market_prices(type_ids: str, refresh: bool = False):
    """
    API endpoint to get market prices.
    - If `refresh=True`, it forces a fetch from Fuzzwork's API for the given IDs.
    - Otherwise, it serves prices from the local DB cache.
    - If any requested items are missing from the cache, it fetches and stores them
      before returning the result.
    """
    type_id_list = [int(tid) for tid in type_ids.split(",") if tid.strip().isdigit()]
    if refresh:
        prices = update_market_prices(type_id_list)
        db_prices = get_prices_from_db(type_id_list)
        # Merge price and last_updated
        merged = {tid: {"price": prices[tid], "last_updated": db_prices[tid]["last_updated"]} for tid in type_id_list}
        return {"prices": merged}
    else:
        db_prices = get_prices_from_db(type_id_list)
        # If any are missing, fetch and update
        missing = [tid for tid, v in db_prices.items() if v["price"] is None]
        if missing:
            update_market_prices(missing)
            db_prices = get_prices_from_db(type_id_list)
        return {"prices": db_prices}

@app.get("/api/contracts/", response_model=List[Contract])
def list_contracts():
    return contracts

@app.get("/api/config")
def get_config():
    """Provides client-side configuration variables from environment settings."""
    return {
        "app_domain": os.getenv("APP_DOMAIN", "http://localhost:8000"),
        "discord_invite": os.getenv("DISCORD_INVITE", "https://discord.gg/yFxsjw9")
    }

# --- ESI Authentication Endpoints ---

from fastapi.responses import RedirectResponse, JSONResponse
from .Esi import build_auth_url, exchange_code_for_token

@app.get("/login")
def login():
    """Redirects the user to the EVE SSO login page."""
    return RedirectResponse(url=build_auth_url())

@app.get("/callback")
async def callback(code: str):
        # Admin corp gating: set ADMIN_CORP_ID in environment to the corp ID allowed to access contracts
        admin_corp_id = int(os.getenv("ADMIN_CORP_ID", "0") or 0)
        html = '''
<!DOCTYPE html>
<html><body>
<script>
const ADMIN_CORP_ID = __ADMIN_CORP_ID__;
fetch('/api/callback_token?code=' + encodeURIComponent(new URLSearchParams(window.location.search).get('code')))
    .then(res => res.json())
    .then(data => {
        if (data.access_token) {
            localStorage.setItem('token', data.access_token);
            const cid = Number(data.corp_id || 0);
            if (ADMIN_CORP_ID && cid === ADMIN_CORP_ID) {
                window.location.href = 'contracts.html';
            } else {
                window.location.href = 'index.html';
            }
        } else {
            document.body.innerHTML = '<p>Login failed.</p>';
        }
    });
</script>
</body></html>
'''
        html = html.replace("__ADMIN_CORP_ID__", str(admin_corp_id))
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)

@app.get("/api/callback_token")
async def api_callback_token(code: str):
    """
    API-level callback to exchange the authorization code for a token.
    It also fetches the character's corporation ID to assist with frontend
    routing and authorization decisions.
    """
    tokens = await exchange_code_for_token(code)
    # Include corp_id to support front-end routing decisions
    try:
        access_token = tokens.get("access_token")
        corp_id = None
        if access_token:
            identity = await verify_token(access_token)
            char_id = identity.get("CharacterID")
            if char_id:
                details = await get_character_details(char_id)
                corp_id = details.get("corporation_id")
        out = dict(tokens)
        if corp_id is not None:
            out["corp_id"] = corp_id
        return out
    except Exception:
        # Fallback to tokens only
        return tokens

# --- Contract & Quote API Endpoints ---

from .Esi import verify_token, get_character_details, get_contracts_and_items, Toon

import time

@app.post("/fetch_contracts/")
async def fetch_contracts(token_data: dict):
    """
    Fetches corporation contracts using a provided access token.
    - Implements a 20-minute cache (`cache_lifetime`) to avoid excessive ESI calls.
    - Verifies the token, gets character and corporation details.
    - Fetches contracts and their items from ESI.
    """
    access_token = token_data.get("access_token")
    if not access_token:
        return {"error": "Missing access token."}

    identity = await verify_token(access_token)
    char_id = identity["CharacterID"]

    details = await get_character_details(char_id)
    print(details)
    corp_id = details["corporation_id"]

    now = time.time()
    cache_lifetime = 1200  # 20 minutes
    if now - contracts_cache['timestamp'] < cache_lifetime and contracts_cache['contracts']:
        contracts = contracts_cache['contracts']
        print("Serving contracts from cache.")
    else:
        contracts = await get_contracts_and_items(access_token, corp_id)
        # Add issuer names to contracts
        for contract in contracts:
            if "issuer_name" not in contract:
                try:
                    contract["issuer_name"] = await Toon(contract["issuer_id"])
                except:
                    contract["issuer_name"] = "Unknown"
        contracts_cache['contracts'] = contracts
        contracts_cache['timestamp'] = now
        print("Fetched contracts from ESI and updated cache.")

    # Update stored contracts (optional, legacy logic)
    new_contracts = []
    existing_ids = {c["contract_id"] for c in stored_contracts}
    for contract in contracts:
        if contract["contract_id"] not in existing_ids:
            stored_contracts.append(contract)
            new_contracts.append(contract)
        else:
            for i, stored_contract in enumerate(stored_contracts):
                if stored_contract["contract_id"] == contract["contract_id"]:
                    stored_contracts[i] = contract
                    break

    return {
        "character": identity["CharacterName"],
        "corporation_id": corp_id,
        "contracts": contracts,
        "new_contracts": new_contracts,
        "total_contracts": len(contracts)
    }

import random
import time

def generate_hex():
    return f'{random.randint(0, 0xFFFFFF):06X}'

def check_quote():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    c = conn.cursor()   
    c.execute('''CREATE TABLE IF NOT EXISTS quotes (
        code TEXT PRIMARY KEY,
        content TEXT,
        created_at INTEGER
    )''')
    conn.commit()
    conn.close()
check_quote()

@app.post("/api/quotes/")
async def add_quote(content: str = Body(...)):
    """Stores the raw text of a new quote and returns a unique 6-character hex code."""
    code = generate_hex()
    created_at = int(time.time())
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO quotes (code, content, created_at) VALUES (?, ?, ?)', (code, content, created_at))
        conn.commit()
        conn.close()
        return {"code": code, "content": content, "created_at": created_at}
    except sqlite3.OperationalError as e:
        print(f"Database error in add_quote: {e}")
        return {"error": "Database error"}

@app.get("/api/quotes/{code}")
async def get_quote(code: str):
    """Retrieves a quote's content from the database using its unique code."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL')
        c = conn.cursor()
        c.execute('SELECT code, content, created_at FROM quotes WHERE code = ?', (code,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return {"code": row[0], "content": row[1], "created_at": row[2]}
        else:
            return {"error": "Quote not found"}
    except sqlite3.OperationalError as e:
        print(f"Database error in get_quote: {e}")
        return {"error": "Database error"}

@app.post("/api/quotes/cleanup")
async def manual_quote_cleanup():
    """An admin endpoint to manually trigger the cleanup of old quotes."""
    try:
        cleanup_old_quotes()
        return {"success": True, "message": "Quote cleanup completed successfully"}
    except Exception as e:
        print(f"Manual quote cleanup error: {e}")
        return {"success": False, "error": str(e)}

# --- Admin API Endpoints ---

@app.post("/api/save-multipliers")
async def save_multipliers(multipliers_data: dict):
    """
    Saves the provided dictionary of multipliers to `jsons/multipliers.json`.
    - Creates a backup of the existing file before writing the new data.
    - Resolves the file path relative to the project root for reliability.
    """
    try:
        import json
        # Resolve path relative to the project root (one level above this Scripts/ folder)
        script_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        multipliers_path = os.path.join(project_root, 'jsons', 'multipliers.json')
        
        # Backup current file first
        backup_path = multipliers_path + '.backup'
        if os.path.exists(multipliers_path):
            import shutil
            shutil.copy2(multipliers_path, backup_path)
        
        # Write new data
        with open(multipliers_path, 'w') as f:
            json.dump(multipliers_data, f, indent=2)
        
        return {"success": True, "message": "Multipliers saved successfully"}
    except Exception as e:
        print(f"Error saving multipliers: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to save multipliers: {str(e)}"})

# --- Static File Serving ---
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory=PROJECT_ROOT, html=True), name="static")


# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)