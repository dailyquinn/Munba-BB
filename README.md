# Munba Buyback

Munba Buyback is a web application for running an EVE Online corporation buyback program. It combines an interactive front-end for player quotes and contract management with a Django + AllianceAuth + ESI back-end running inside Docker.

NOTE: This application is still under development. At this point, it is "functional" but not "complete", consider this a Beta release. Features like automatic SSL support and security features are planned for future releases.

## Features

- **Quote Generator** (`index.html` + `Scripts/Reprocess & Market.js`)
  - Accepts pasted item lists and evaluates reprocessable items (ore, ice, PI, etc.).
  - Resolves item names and group definitions using the EVE Static Data Export (SDE).
  - Calculates line-item totals and overall contract payout based on customizable multipliers.
  - Dynamically displays current default buyback rates, contracting corporation name, page title, and location options configured via environment variables.
  - Generates unique quote codes for contract verification.

- **Admin Dashboard** (`contracts.html`)
  - Requires EVE SSO login (restricted to members of the configured `ADMIN_CORP_ID`).
  - **Outstanding Contracts**: Displays corporation contracts via ESI, validating contents against generated quotes.
  - **Multiplier Editor**: Interactive GUI for managing item/group multipliers and setting the global default rate (`jsons/multipliers.json`).
  - **Active Modifiers List**: Displays human-readable SDE names alongside raw JSON keys (`group:18` or `16633`).

- **Django Back-end** (`munbabb/`)
  - `/api/config` – Provides dynamic application settings (app title, Discord invite, ESI-resolved corp recipient, location tables).
  - `/api/sde/search` & `/api/sde/names` – EVE SDE item/group name resolution.
  - `/api/save-multipliers` – Updates multiplier settings in `jsons/multipliers.json`.
  - `/login` & `/callback` – EVE SSO OAuth authentication flow.

## Project Structure

```
Munba-BB/
├── munbabb/                    # Django application root
│   ├── api/                   # API views, models, and URL routing
│   ├── munbabb/               # Project configuration (settings, WSGI, Celery)
│   └── manage.py              # Django management utility
├── Scripts/                   # Front-end JavaScript modules
│   ├── Reprocess & Market.js  # Primary quote calculation logic
│   ├── admin-tabs.js          # Admin dashboard & multiplier editor logic
│   ├── contractlist.js        # ESI contract renderer
│   ├── contractvalue.js       # Contract valuation logic
│   └── Dropdown warnings.js   # UI location & fee warning handler
├── jsons/                     # JSON configuration files
│   ├── multipliers.json       # Active item/group/default multipliers
│   └── reprocessables.json    # Reprocessing maps and item definitions
├── Media/                     # Branding assets
│   ├── logo.png               # Corporation / app logo
│   └── background.png         # Main page background image
├── data/                      # Persistent database directory (SQLite DB mounted via volume)
├── index.html                 # Main buyback quote tool
├── contracts.html             # Admin dashboard & settings manager
├── Dockerfile                 # Container build definition
├── docker-compose.example.yml # Template for Docker configuration
└── requirements.txt           # Python package requirements
```

## Setup & Deployment

### 1. Register EVE Application (CCP Developers Portal)

When creating your application on [developers.eveonline.com](https://developers.eveonline.com), ensure you add the following **ESI scope**:

- `esi-contracts.read_corporation_contracts.v1` – Required to fetch and read active corporation contracts and items.

*(Note: Character corporation membership is verified via the public ESI character endpoint, so no additional role scopes are required).*

Set the Callback URL on the portal to match your `EVE_REDIRECT_URI` (e.g. `http://localhost:8000/callback` or `https://your-domain.com/callback`).

### 2. Configure Docker Compose

Copy the example Docker Compose file to create your active configuration:

```bash
cp docker-compose.example.yml docker-compose.yml
```

Edit `docker-compose.yml` and configure your environment variables:

| Variable | Description |
|---|---|
| `EVE_CLIENT_ID` | ESI Application Client ID from CCP Developers portal |
| `EVE_CLIENT_SECRET` | ESI Application Secret Key |
| `EVE_REDIRECT_URI` | OAuth callback URL (e.g. `http://localhost:8000/callback` or `https://your-domain.com/callback`) |
| `ADMIN_CORP_ID` | EVE Corporation ID authorized for admin dashboard access (automatically resolves corp name via ESI) |
| `APP_DOMAIN` | Base domain/URL of the deployment |
| `DISCORD_INVITE` | Discord server invite link |
| `APP_TITLE` | Application title displayed in header and browser tab (defaults to `Unknown Buyback`) |
| `CONTRACT_RECIPIENT` | Fallback contract recipient string if `ADMIN_CORP_ID` is not set |
| `LOCATIONS` | JSON array of drop-off locations with system name, structure type, and optional hauling fee |

#### Location Configuration Example

```yaml
- LOCATIONS=[{"system":"UALX-3","structure":"Keepstar","fee":0},{"system":"Tenerifis","structure":"L/XL Structure","fee":50000000}]
```

*Note: If `structure` is not applicable, you can set `"structure": ""`, `"structure": null`, or omit the `"structure"` key entirely. Do NOT leave a trailing colon without a value (`"structure":`) as that is invalid JSON syntax.*

### 2. Build & Run Container

Start the service using Docker Compose:

```bash
docker compose up -d --build
```

On initial startup, the container automatically applies database migrations and loads the EVE Static Data Export (SDE).

### 3. Accessing the Application

- **Quote Tool**: `http://localhost:8000/` or `http://localhost:8000/index.html`
- **Admin Dashboard**: `http://localhost:8000/contracts.html` (requires EVE SSO login with an account in `ADMIN_CORP_ID`)

## Customization & Administration

- **Default Buyback Rate**: Set in the Admin Dashboard under **Edit Multipliers** > **Default Modifier**, or directly via `"_default"` in `jsons/multipliers.json`.
- **Item & Group Multipliers**: Managed interactively in the Admin Dashboard, or by editing `jsons/multipliers.json` (`"34": 0.88` for items, `"group:18": 0.90` for item groups).
- **Logos & Styling**: Replace images in `Media/logo.png` and `Media/background.png`.

## Notes & Licensing

- This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](file:///d:/OneDrive/Documents/Repo%20Clones/Munba-BB/LICENSE) file for details.
- All EVE Online assets are property of Fenris Creations.
- Front-end appraisal integration uses Fuzzwork's public market API.
- GDS-BB provided for modification courtesy of Voidlegacy
- Initial commit made from my last locally saved commit of RCI Buyback
- Contributions and tips (ISK/Plex only, to Quinn Munba) are welcome!
