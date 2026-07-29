import sqlite3
import requests
import time

DB_PATH = 'market_prices.db'
BATCH_SIZE = 100  
FUZZWORK_URL = 'https://market.fuzzwork.co.uk/aggregates/'
REGION_ID = '10000002'  # Jita

def get_all_type_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT typeID FROM market_prices')
    rows = c.fetchall()
    conn.close()
    return [str(row[0]) for row in rows]

def get_fuzzwork_prices(type_ids):
    url = f"{FUZZWORK_URL}?station=60003760&types={','.join(type_ids)}"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()  # {typeID: {buy: {...}, ...}, ...}
    else:
        print(f"Error fetching from Fuzzwork: {resp.status_code}")
        return None

def refresh_all_prices():
    type_ids = get_all_type_ids()
    print(f"Refreshing {len(type_ids)} type_ids in batches of {BATCH_SIZE}...")
    consecutive_failures = 0
    for i in range(0, len(type_ids), BATCH_SIZE):
        batch = type_ids[i:i+BATCH_SIZE]
        print(f"Requesting Fuzzwork for batch {i//BATCH_SIZE+1}...")
        prices = get_fuzzwork_prices(batch)
        if prices is None:
            consecutive_failures += 1
            print(f"Batch {i//BATCH_SIZE+1}: Failed. Consecutive failures: {consecutive_failures}")
            if consecutive_failures >= 2:
                print("Two consecutive batches failed. Stopping script.")
                break
        else:
            consecutive_failures = 0
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for tid in batch:
                buy_price = float(prices.get(tid, {}).get('buy', {}).get('max', 0))
                sell_price = float(prices.get(tid, {}).get('sell', {}).get('min', 0))
                updated_at = time.strftime('%Y-%m-%dT%H:%M:%S')
                c.execute('UPDATE market_prices SET buy_price = ?, sell_price = ?, updated_at = ? WHERE typeID = ?', 
                         (buy_price, sell_price, updated_at, tid))
            conn.commit()
            conn.close()
        time.sleep(1)  # Be nice to Fuzzwork
    print("Done.")

if __name__ == '__main__':
    refresh_all_prices()
