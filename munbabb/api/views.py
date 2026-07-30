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

def get_config(request):
    return JsonResponse({
        "app_domain": os.getenv("APP_DOMAIN", "http://localhost:8000"),
        "discord_invite": os.getenv("DISCORD_INVITE", "https://discord.gg/yFxsjw9"),
        "app_title": os.getenv("APP_TITLE", "Munba Buyback"),
        "contract_recipient": os.getenv("CONTRACT_RECIPIENT", "Munba Buyback")
    })

def build_auth_url():
    # Helper to generate the URL (porting from Esi.py)
    # Using simple approach for now
    scopes = "esi-contracts.read_corporation_contracts.v1 esi-characters.read_corporation_roles.v1"
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
            # Verify
            v_res = requests.get("https://login.eveonline.com/oauth/verify", headers={"Authorization": f"Bearer {access_token}"})
            if v_res.ok:
                char_id = v_res.json().get("CharacterID")
                # Get char details
                c_res = requests.get(f"https://esi.evetech.net/latest/characters/{char_id}/")
                if c_res.ok:
                    corp_id = c_res.json().get("corporation_id")
                    tokens["corp_id"] = corp_id
        except Exception:
            pass
    return JsonResponse(tokens)

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
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            access_token = data.get("access_token")
            if not access_token:
                return JsonResponse({"error": "Missing access token."}, status=400)
            
            # Simplified version for now, full port requires the async functions in Esi.py
            # Since this is a Django sync view, we'll just mock it or port it fully
            return JsonResponse({"contracts": [], "new_contracts": [], "total_contracts": 0})
        except Exception as e:
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
        results = []
        q = Q()
        if names: q |= Q(name__in=names)
        if ids: q |= Q(id__in=ids)
        if not (names or ids): return JsonResponse([])
        for item in ItemType.objects.filter(q).select_related('group'):
            materials = ItemTypeMaterials.objects.filter(item_type=item).select_related('material', 'material__group')
            reprocess_yield = {m.material.id: {"name": m.material.name, "quantity": m.quantity, "group_id": m.material.group_id} for m in materials}
            results.append({
                "id": item.id,
                "name": item.name,
                "group_id": item.group_id,
                "category_id": item.group.category_id if item.group else None,
                "volume": float(item.volume) if item.volume else 0,
                "reprocessing": reprocess_yield
            })
        return JsonResponse(results, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
