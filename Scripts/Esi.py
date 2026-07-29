import httpx
import asyncio
from dotenv import load_dotenv
import os
import uuid

# --- Configuration ---
load_dotenv()
client_id = os.getenv("EVE_CLIENT_ID")
client_secret = os.getenv("EVE_CLIENT_SECRET")
redirect_uri = os.getenv("EVE_REDIRECT_URI")
scopes = "esi-contracts.read_corporation_contracts.v1"

# Debug print to confirm that environment variables are loaded on startup.
print(f"[DEBUG] Client ID: {client_id[:10] if client_id else 'None'}...")
print(f"[DEBUG] Redirect URI: {redirect_uri}")
print(f"[DEBUG] Client Secret: {'SET' if client_secret else 'None'}")


"""
This module handles all interactions with the EVE Online ESI (EVE Swagger Interface),
including OAuth2 authentication and data fetching.
"""

# --- EVE SSO Authentication ---

def build_auth_url():
    """Constructs the EVE SSO URL for user authentication."""
    state = str(uuid.uuid4())
    return (
        "https://login.eveonline.com/v2/oauth/authorize"
        f"?response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&client_id={client_id}"
        f"&scope={scopes}"
        f"&state={state}"
    )

async def exchange_code_for_token(code: str):
    """
    Exchanges an authorization code for an access token and refresh token.

    Args:
        code: The authorization code returned from the EVE SSO callback.
    """
    token_url = "https://login.eveonline.com/v2/oauth/token"
    auth = httpx.BasicAuth(client_id, client_secret)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data= {"grant_type": "authorization_code", "code": code},
            auth=auth,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        return response.json()

# --- ESI Data Fetching ---

async def verify_token(token:str):
    """
    Verifies an access token and returns the character's identity information.
    Since /oauth/verify is deprecated, this decodes the JWT locally.

    Args:
        token: The EVE SSO access token (JWT).
    """
    import base64
    import json
    
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    
    payload = parts[1]
    payload += '=' * (-len(payload) % 4)
    decoded_payload = base64.urlsafe_b64decode(payload)
    jwt_data = json.loads(decoded_payload)
    
    sub = jwt_data.get("sub", "")
    char_id = None
    if sub.startswith("CHARACTER:EVE:"):
        char_id = int(sub.split(":")[2])
    elif ":" in sub:
        char_id = int(sub.split(":")[-1])
        
    return {
        "CharacterID": char_id,
        "CharacterName": jwt_data.get("name")
    }


async def get_character_details(character_id: int):
    """
    Fetches public details for a given character ID.

    Args:
        character_id: The EVE character ID.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://esi.evetech.net/latest/characters/{character_id}/")
        r.raise_for_status()
        return r.json()

async def Toon(charID:int):
    """
    Fetches the name of a character for a given character ID.

    Args:
        charID: The EVE character ID.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://esi.evetech.net/latest/characters/{charID}/")
        r.raise_for_status()
        return r.json()["name"]
    
async def get_contracts_and_items(token: str, corp_id: int):
    """
    Fetches all outstanding corporation contracts and their associated items.
    Includes a retry mechanism with exponential backoff for fetching items to handle ESI flakiness.

    Args:
        token: A valid EVE SSO access token for a character in the corporation.
        corp_id: The EVE corporation ID.
    """
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[DEBUG] Fetching contracts for corp_id: {corp_id}")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Fetch contracts list
            r = await client.get(
                f"https://esi.evetech.net/latest/corporations/{corp_id}/contracts/",
                headers=headers,
            )
            print(f"[DEBUG] Contracts response status: {r.status_code}")
            r.raise_for_status()
            # Filter for contracts that are currently outstanding.
            contracts = [c for c in r.json() if c.get("status") == "outstanding"]
            print(f"[DEBUG] Found {len(contracts)} outstanding contracts")
        except Exception as e:
            print(f"[ERROR] Failed to fetch contracts: {e}")
            raise

        # Fetch items for each contract individually, with retries for transient errors.
        for c in contracts:
            item_url = (
                f"https://esi.evetech.net/latest/corporations/{corp_id}/contracts/{c['contract_id']}/items/"
            )
            attempts = 0
            backoff = 0.5
            while True:
                attempts += 1
                try:
                    resp = await client.get(item_url, headers=headers)
                    # Retry on common transient ESI error codes.
                    if resp.status_code in {429, 500, 502, 503, 504, 520, 522, 523, 524}:
                        raise httpx.HTTPStatusError(
                            f"Transient HTTP {resp.status_code}", request=resp.request, response=resp
                        )
                    resp.raise_for_status()
                    c["items"] = resp.json()
                    print(f"[DEBUG] Successfully fetched {len(c['items'])} items for contract {c['contract_id']}")
                    break
                except httpx.HTTPStatusError as e:
                    print(f"[ERROR] HTTP error for contract {c['contract_id']}: {e}")
                    if attempts < 3: # Retry up to 3 times with increasing delay.
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    # After 3 failed attempts, give up, record the error, and proceed to the next contract.
                    c["items"] = []
                    c["items_error"] = {
                        "status": getattr(e.response, "status_code", None),
                        "detail": str(e),
                    }
                    break
                except Exception as e:
                    print(f"[ERROR] General error for contract {c['contract_id']}: {e}")
                    if attempts < 3:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    c["items"] = []
                    c["items_error"] = {"status": None, "detail": str(e)}
                    break

        print(f"[DEBUG] Returning {len(contracts)} contracts")
        return contracts