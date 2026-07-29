# RCI Buyback

Munba Buyback (derived from GDS-BB and RCI Buyback) is a web application for running an EVE Online corporation buyback program. It combines a static front-end for player interaction with a FastAPI back-end that pulls market prices, estimates contract values, and fetches outstanding contracts via EVE's ESI interface.

## Features

- **Quote generator** (`index.html` + `Scripts/Reprocess & Market.js`)
  - Accepts pasted item lists, reprocesses ore/ice using `jsons/reprocessing_map.json`.
  - Queries Fuzzwork market prices and applies multipliers from `jsons/multipliers.json`.
  - Returns per-item pricing, reprocessed material values, and total payout.
  - Generates a unique quote code for contract validation.

- **Admin Dashboard** (`contracts.html`)
  - Requires EVE SSO login (restricted to admin corp).
  - **Outstanding Contracts**: Displays corporation contracts via `Scripts/contractlist.js`.
    - Validates contract contents against generated quotes using the quote code in the description.
    - Estimates contract market value using `Scripts/contractvalue.js`.
  - **Multiplier Editor**: GUI for editing `jsons/multipliers.json` via `Scripts/admin-tabs.js`.

- **FastAPI back-end** (`Scripts/main.py`)
  - `/api/market_prices/` – caches Jita buy prices in `market_prices.db`.
  - `/api/quotes/` – stores and retrieves quote details for validation.
  - `/login` & `/callback` – EVE SSO entry points.
  - `/fetch_contracts/` – retrieves corp contracts and items via ESI.
  - Serves static files from the repository root.

- **Price cache maintenance**
  - Background hourly refresh thread.
  - `Scripts/export_typeids_to_db.py` seeds the SQLite database with EVE type IDs.
  - `Scripts/force_refresh_prices.py` refreshes prices on demand.

## Project layout

```
GDS-BB/
├── Scripts/
│   ├── main.py                # FastAPI application
│   ├── Esi.py                 # OAuth/ESI helpers
│   ├── contractvalue.js       # Contract valuation logic
│   ├── Reprocess & Market.js  # Quote calculator
│   ├── contractlist.js        # Contract list renderer
│   ├── admin-tabs.js          # Admin UI logic
│   ├── Dropdown warnings.js   # UI helpers
│   └── ... (DB utilities)
├── jsons/                     # Type IDs, reprocessing maps, multipliers
├── index.html                 # Buyback quote page
├── contracts.html             # Outstanding contracts UI
├── market_prices.db           # SQLite price cache
├── invTypes2.csv              # Source for Type IDs (required for setup)
├── requirements.txt           # Python dependencies
└── Media/                     # Logos & background images
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Environment variables** (used in `Scripts/Esi.py`)
   ```bash
   EVE_CLIENT_ID=<your_application_id>
   EVE_CLIENT_SECRET=<your_secret>
   EVE_REDIRECT_URI=http://localhost:8000/callback
   ADMIN_CORP_ID=CorpID_of_the_BB
   ```
3. **Prepare market database**
   ```bash
   python Scripts/export_typeids_to_db.py    # populate type IDs
   python Scripts/force_refresh_prices.py    # optional initial price load
   ```

## Running the app

```bash
uvicorn Scripts.main:app --host 0.0.0.0 --port 8000 --reload
```
Visit `http://localhost:8000/index.html` for the quote tool.
The “Outstanding Contracts” link triggers the EVE SSO flow and renders `contracts.html`.

## Customization

- Adjust buyback multipliers in `jsons/multipliers.json` (type ID → multiplier).
- Add or remove reprocessable items via `jsons/reprocessables.json`.
- Update reprocessing yields in `jsons/reprocessing_map.json`.

## Additional scripts

- `Scripts/force_refresh_prices.py` – refreshes cached prices for all type IDs.
- `Scripts/export_typeids_to_db.py` – imports type IDs from `invTypes2.csv` into the SQLite DB.

## Notes

- All EVE Online assets belong to CCP Games; project is for educational/fan use.
- Front-end uses Fuzzwork's public market API—please respect rate limits.
- GDS-BB provided for modification courtesy of Voidlegacy
- Initial commit made from my last locally saved commit of RCI Buyback
- Contributions are welcome!
