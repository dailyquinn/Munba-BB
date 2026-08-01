from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
import time
import os
import random
import requests
from django.conf import settings

from .models import Quote, MarketPrice

# ESI config
EVE_CLIENT_ID = os.getenv("EVE_CLIENT_ID")
EVE_CLIENT_SECRET = os.getenv("EVE_CLIENT_SECRET")
EVE_REDIRECT_URI = os.getenv("EVE_REDIRECT_URI", "http://localhost:8000/callback")
ADMIN_CORP_ID = int(os.getenv("ADMIN_CORP_ID", "0") or 0)

contracts_cache = {
    'timestamp': 0,
    'contracts': []
}

corp_name_cache = {"id": None, "name": None, "timestamp": 0}

def get_admin_corp_name():
    if not ADMIN_CORP_ID:
        return os.getenv("CONTRACT_RECIPIENT", "Munba Buyback")
    now = time.time()
    if corp_name_cache["id"] == ADMIN_CORP_ID and corp_name_cache["name"] and (now - corp_name_cache["timestamp"] < 86400):
        return corp_name_cache["name"]
    try:
        res = requests.get(f"https://esi.evetech.net/latest/corporations/{ADMIN_CORP_ID}/", timeout=5)
        if res.ok:
            name = res.json().get("name")
            if name:
                corp_name_cache["id"] = ADMIN_CORP_ID
                corp_name_cache["name"] = name
                corp_name_cache["timestamp"] = now
                return name
    except Exception as e:
        pass
    return os.getenv("CONTRACT_RECIPIENT", "Munba Buyback")

def get_locations():
    locations_raw = os.getenv("LOCATIONS")
    if locations_raw:
        try:
            parsed = json.loads(locations_raw)
            if isinstance(parsed, list):
                result = []
                for item in parsed:
                    if isinstance(item, dict):
                        sys_name = item.get("system")
                        struct_name = item.get("structure")
                        
                        sys_str = str(sys_name).strip() if sys_name and sys_name != 0 else ""
                        struct_str = str(struct_name).strip() if struct_name and struct_name != 0 else ""
                        
                        fee = item.get("fee", 0)
                        try:
                            fee = float(fee) if fee is not None else 0
                        except (ValueError, TypeError):
                            fee = 0
                            
                        result.append({
                            "system": sys_str,
                            "structure": struct_str,
                            "fee": fee
                        })
                if result:
                    return result
        except Exception:
            pass

    return [
        {"system": "UALX-3", "structure": "Keepstar", "fee": 0},
        {"system": "ABE-M2", "structure": "Fortizar", "fee": 0},
        {"system": "Tenerifis", "structure": "L/XL Structure", "fee": 50000000}
    ]

def get_config(request):
    app_domain = (os.getenv("APP_DOMAIN") or "http://localhost:8000").strip()
    if app_domain and not (app_domain.startswith("http://") or app_domain.startswith("https://") or app_domain.startswith("//")):
        scheme = "http://" if ("localhost" in app_domain or "127.0.0.1" in app_domain) else "https://"
        app_domain = f"{scheme}{app_domain}"
    return JsonResponse({
        "app_domain": app_domain,
        "discord_invite": os.getenv("DISCORD_INVITE", "https://discord.gg/yFxsjw9"),
        "app_title": os.getenv("APP_TITLE", "Unknown Buyback"),
        "contract_recipient": get_admin_corp_name(),
        "locations": get_locations()
    })

def build_auth_url():
    scopes = "esi-contracts.read_corporation_contracts.v1"
    url = f"https://login.eveonline.com/v2/oauth/authorize/?response_type=code&redirect_uri={EVE_REDIRECT_URI}&client_id={EVE_CLIENT_ID}&scope={scopes}&state=login"
    return url

def login(request):
    return HttpResponseRedirect(build_auth_url())

def callback(request):
    code = request.GET.get('code')
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
                window.location.href = '/contracts.html';
            } else {
                window.location.href = '/index.html';
            }
        } else {
            document.body.innerHTML = '<p>Login failed.</p>';
        }
    });
</script>
</body></html>
'''
    html = html.replace("__ADMIN_CORP_ID__", str(ADMIN_CORP_ID))
    return HttpResponse(html)

@csrf_exempt
def api_callback_token(request):
    code = request.GET.get('code')
    # Simplified token exchange
    import base64
    if not EVE_CLIENT_ID or not EVE_CLIENT_SECRET:
        return JsonResponse({"error": "ESI credentials not set"}, status=500)
    auth = base64.b64encode(f"{EVE_CLIENT_ID}:{EVE_CLIENT_SECRET}".encode()).decode()
    res = requests.post(
        "https://login.eveonline.com/v2/oauth/token",
        data={"grant_type": "authorization_code", "code": code},
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"}
    )
    if not res.ok:
        return JsonResponse(res.json(), status=res.status_code)
    tokens = res.json()
    
    # Try to verify token and get corp ID
    access_token = tokens.get("access_token")
    if access_token:
        try:
            import base64
            import json
            parts = access_token.split(".")
            if len(parts) >= 2:
                payload = parts[1]
                payload += '=' * (-len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                data = json.loads(decoded)
                sub = data.get('sub', '')
                if sub.startswith('CHARACTER:EVE:'):
                    char_id = sub.split(':')[-1]
                    c_res = requests.get(f"https://esi.evetech.net/latest/characters/{char_id}/")
                    if c_res.ok:
                        corp_id = c_res.json().get("corporation_id")
                        tokens["corp_id"] = corp_id
        except Exception:
            pass
    return JsonResponse(tokens)

@csrf_exempt
def get_market_prices(request):
    raw_ids = []
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            if isinstance(body, dict):
                ids = body.get("type_ids", [])
                if isinstance(ids, list):
                    raw_ids = [int(i) for i in ids if str(i).isdigit()]
                elif isinstance(ids, str):
                    raw_ids = [int(i.strip()) for i in ids.split(',') if i.strip().isdigit()]
            elif isinstance(body, list):
                raw_ids = [int(i) for i in body if str(i).isdigit()]
        except Exception:
            pass
    
    if not raw_ids:
        type_ids_str = request.GET.get('type_ids', '')
        if type_ids_str:
            try:
                raw_ids = list({int(i.strip()) for i in type_ids_str.split(',') if i.strip().isdigit()})
            except Exception:
                pass

    if not raw_ids:
        return JsonResponse({"prices": {}})

    prices = {}
    now = time.time()
    now_str = str(int(now))
    
    # 1. Query cached prices from MarketPrice table
    try:
        cached_qs = MarketPrice.objects.filter(typeID__in=raw_ids)
        cached_map = {p.typeID: p for p in cached_qs}
    except Exception:
        cached_map = {}
    
    missing_ids = []
    for tid in raw_ids:
        if tid in cached_map:
            p_obj = cached_map[tid]
            try:
                age = now - float(p_obj.updated_at)
            except Exception:
                age = 999999
            if age < 3600:
                prices[str(tid)] = {
                    "price": p_obj.buy_price,
                    "buy": p_obj.buy_price,
                    "sell": p_obj.sell_price
                }
                continue
        missing_ids.append(tid)

    # 2. Fetch missing/stale prices from Fuzzwork Market API in 100-item chunks
    if missing_ids:
        for i in range(0, len(missing_ids), 100):
            chunk = missing_ids[i:i+100]
            chunk_str = ",".join(map(str, chunk))
            try:
                url = f"https://market.fuzzwork.co.uk/aggregates/?station=60003760&types={chunk_str}"
                res = requests.get(url, timeout=5)
                if res.ok:
                    data = res.json()
                    for tid_str, p_data in data.items():
                        try:
                            tid = int(tid_str)
                            buy_max = float(p_data.get('buy', {}).get('max', 0) or 0)
                            sell_min = float(p_data.get('sell', {}).get('min', 0) or 0)
                            
                            prices[str(tid)] = {
                                "price": buy_max,
                                "buy": buy_max,
                                "sell": sell_min
                            }
                            MarketPrice.objects.update_or_create(
                                typeID=tid,
                                defaults={
                                    "buy_price": buy_max,
                                    "sell_price": sell_min,
                                    "updated_at": now_str
                                }
                            )
                        except Exception:
                            pass
            except Exception as e:
                print("Fuzzwork fetch error:", e)

    return JsonResponse({"prices": prices})

def user_notifications_count(request, user_id=None):
    return JsonResponse({"count": 0})

@csrf_exempt
def add_quote(request):
    if request.method == "POST":
        content = request.body.decode('utf-8')
        if content.startswith('"') and content.endswith('"'):
            content = json.loads(content)
        code = f'{random.randint(0, 0xFFFFFF):06X}'
        Quote.objects.update_or_create(code=code, defaults={"content": content, "created_at": int(time.time())})
        return JsonResponse({"code": code, "content": content, "created_at": int(time.time())})

def get_quote(request, code):
    try:
        q = Quote.objects.get(code=code)
        return JsonResponse({"code": q.code, "content": q.content, "created_at": q.created_at})
    except Quote.DoesNotExist:
        return JsonResponse({"error": "Quote not found"})

@csrf_exempt
def fetch_contracts(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        access_token = data.get("access_token")
        if not access_token:
            return JsonResponse({"error": "Missing access token."}, status=400)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "Munba-Buyback/1.0"
        }

        # 1. Resolve character and corporation ID from ESI token
        verify_res = requests.get("https://login.eveonline.com/oauth/verify", headers=headers, timeout=10)
        if not verify_res.ok:
            verify_res = requests.get("https://esi.evetech.net/verify/", headers=headers, timeout=10)
        
        if not verify_res.ok:
            return JsonResponse({"error": f"Failed to verify SSO token with ESI (HTTP {verify_res.status_code})"}, status=401)
        
        verify_data = verify_res.json()
        char_id = verify_data.get("CharacterID") or verify_data.get("character_id")
        if not char_id:
            return JsonResponse({"error": "Could not determine Character ID from token."}, status=400)

        # Get character affiliation (Corporation ID)
        affil_res = requests.post(
            "https://esi.evetech.net/latest/characters/affiliation/?datasource=tranquility",
            json=[char_id],
            timeout=10
        )
        if not affil_res.ok or not affil_res.json():
            return JsonResponse({"error": "Could not determine character corporation affiliation."}, status=400)
        
        corp_id = affil_res.json()[0].get("corporation_id")
        if not corp_id:
            return JsonResponse({"error": "Character has no corporation ID."}, status=400)

        # 2. Fetch corporation contracts from ESI
        contracts_url = f"https://esi.evetech.net/latest/corporations/{corp_id}/contracts/?datasource=tranquility"
        contracts_res = requests.get(contracts_url, headers=headers, timeout=15)
        
        if not contracts_res.ok:
            return JsonResponse({"error": f"ESI error fetching contracts: {contracts_res.text}"}, status=contracts_res.status_code)
        
        raw_contracts = contracts_res.json()
        if not isinstance(raw_contracts, list):
            return JsonResponse({"contracts": [], "new_contracts": [], "total_contracts": 0})

        # Filter active item_exchange contracts
        active_contracts = [
            c for c in raw_contracts
            if c.get("type") == "item_exchange" and c.get("status") in ["outstanding", "in_progress", "finished"]
        ]

        # 3. Collect issuer IDs and resolve issuer character names via ESI universe/names
        issuer_ids = list({c["issuer_id"] for c in active_contracts if "issuer_id" in c})
        issuer_names = {}
        if issuer_ids:
            try:
                names_res = requests.post(
                    "https://esi.evetech.net/latest/universe/names/?datasource=tranquility",
                    json=issuer_ids,
                    timeout=10
                )
                if names_res.ok:
                    for entry in names_res.json():
                        issuer_names[entry.get("id")] = entry.get("name")
            except Exception as e:
                print("Failed to fetch issuer names:", e)

        # 4. Fetch items for each contract
        results = []
        for contract in active_contracts:
            cid = contract.get("contract_id")
            items = []
            try:
                items_url = f"https://esi.evetech.net/latest/corporations/{corp_id}/contracts/{cid}/items/?datasource=tranquility"
                items_res = requests.get(items_url, headers=headers, timeout=10)
                if items_res.ok and isinstance(items_res.json(), list):
                    items = [
                        {
                            "type_id": item.get("type_id"),
                            "quantity": item.get("quantity", 1)
                        }
                        for item in items_res.json()
                        if item.get("is_included", True)
                    ]
            except Exception as e:
                print(f"Failed to fetch items for contract {cid}:", e)

            results.append({
                "contract_id": cid,
                "issuer_id": contract.get("issuer_id"),
                "issuer_name": issuer_names.get(contract.get("issuer_id"), f"Character {contract.get('issuer_id')}"),
                "price": float(contract.get("price", 0) or 0),
                "title": contract.get("title", ""),
                "status": contract.get("status", ""),
                "date_issued": contract.get("date_issued", ""),
                "items": items
            })

        return JsonResponse({
            "contracts": results,
            "new_contracts": results,
            "total_contracts": len(results)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def save_multipliers(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # Find root dir
            project_root = settings.BASE_DIR.parent
            file_path = os.path.join(project_root, 'jsons', 'multipliers.json')
            backup_path = file_path + '.backup'
            import shutil
            if os.path.exists(file_path):
                shutil.copy2(file_path, backup_path)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return JsonResponse({"success": True, "message": "Multipliers saved successfully"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

from eve_sde.models import ItemType, ItemGroup, ItemTypeMaterials

def sde_search(request):
    q = request.GET.get('q', '').strip().lower()
    if len(q) < 2: return JsonResponse([])
    matches = []
    groups = ItemGroup.objects.filter(name__icontains=q)[:10]
    for g in groups: matches.append({"name": g.name, "id": g.id, "type": "group"})
    items = ItemType.objects.filter(name__icontains=q)[:15]
    for i in items: matches.append({"name": i.name, "id": i.id, "type": "item"})
    return JsonResponse(matches, safe=False)

@csrf_exempt
def sde_names(request):
    try:
        data = json.loads(request.body)
        ids = data.get("ids", [])
        group_ids = data.get("group_ids", [])
        id_to_name = {}
        if ids:
            for item in ItemType.objects.filter(id__in=ids):
                id_to_name[item.id] = item.name
        if group_ids:
            for grp in ItemGroup.objects.filter(id__in=group_ids):
                id_to_name[f"group:{grp.id}"] = grp.name
        return JsonResponse(id_to_name)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def sde_resolve_items(request):
    try:
        data = json.loads(request.body)
        names = data.get("names", [])
        ids = data.get("ids", [])
        if not (names or ids):
            return JsonResponse([], safe=False)
        
        # Batch items to prevent SQLite parameter limits (max 500 per batch)
        items = []
        if names:
            clean_names = list({str(n).strip() for n in names if n})
            for i in range(0, len(clean_names), 500):
                chunk = clean_names[i:i+500]
                items.extend(ItemType.objects.filter(name__in=chunk).select_related('group'))
        
        if ids:
            clean_ids = list({int(i) for i in ids if i})
            for i in range(0, len(clean_ids), 500):
                chunk = clean_ids[i:i+500]
                items.extend(ItemType.objects.filter(id__in=chunk).select_related('group'))

        # Deduplicate items by ID
        unique_items = list({item.id: item for item in items}.values())
        item_ids = [item.id for item in unique_items]
        
        # Bulk-fetch all reprocessing materials in batch queries to eliminate N+1 overhead
        materials_by_item = {}
        if item_ids:
            for i in range(0, len(item_ids), 500):
                chunk = item_ids[i:i+500]
                m_qs = ItemTypeMaterials.objects.filter(item_type_id__in=chunk).select_related('material_item_type', 'material_item_type__group')
                for m in m_qs:
                    materials_by_item.setdefault(m.item_type_id, []).append(m)

        results = []
        for item in unique_items:
            m_list = materials_by_item.get(item.id, [])
            reprocess_yield = {
                m.material_item_type.id: {
                    "name": m.material_item_type.name,
                    "quantity": m.quantity,
                    "group_id": m.material_item_type.group_id
                }
                for m in m_list
            }
            results.append({
                "id": item.id,
                "name": item.name,
                "group_id": item.group_id,
                "category_id": item.group.category_id if item.group else None,
                "volume": float(item.volume) if item.volume else 0,
                "portion_size": item.portion_size or 1,
                "reprocessing": reprocess_yield
            })
        return JsonResponse(results, safe=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
