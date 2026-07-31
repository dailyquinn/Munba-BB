let reprocessablesPromise = null;
async function loadReprocessables() {
    if (!reprocessablesPromise) {
        reprocessablesPromise = fetch('jsons/reprocessables.json').then(r => r.json());
    }
    return reprocessablesPromise;
}

function parseItemString(itemString) {
    const raw = itemString.trim();
    if (!raw) return { name: '', quantity: 0 };
    let m = raw.match(/^(.*?)(?:\s*)\((?:x)?\s*([\d,]+)\)\s*$/i);
    if (m) {
        return { name: m[1].trim(), quantity: parseInt(m[2].replace(/,/g, ''), 10) || 1 };
    }
    m = raw.match(/^(.*\S)\s+[xX]\s*([\d,]+)\s*$/);
    if (m) {
        return { name: m[1].trim(), quantity: parseInt(m[2].replace(/,/g, ''), 10) || 1 };
    }
    m = raw.match(/^(.*\S)\s+([\d,]+)\s*$/);
    if (m) {
        const before = m[1].trim();
        const numPart = m[2];
        const sizeNumbers = new Set(['1','50','75','100','150','200','400','800','3200']);
        if (sizeNumbers.has(numPart.replace(/,/g,''))) {
            return { name: raw, quantity: 1 };
        }
        return { name: before, quantity: parseInt(numPart.replace(/,/g,''),10) || 1 };
    }
    return { name: raw, quantity: 1 };
}

const priceCache = {};

async function getContractValue(items) {
    let total = 0;
    
    const parsedStrings = [];
    const directItems = [];
    
    // Parse inputs
    for (const item of items) {
        if (typeof item === 'string') {
            const parsed = parseItemString(item);
            parsedStrings.push(parsed);
        } else if (item && item.type_id !== undefined) {
            directItems.push({ type_id: item.type_id, quantity: item.quantity || 1 });
        }
    }
    
    // Resolve names and ids via API
    const namesToResolve = [...new Set(parsedStrings.map(p => p.name))];
    const idsToResolve = [...new Set(directItems.map(p => p.type_id))];
    
    let resolvedMap = {};
    if (namesToResolve.length > 0 || idsToResolve.length > 0) {
        try {
            const resolveRes = await fetch('/api/sde/resolve_items', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ names: namesToResolve, ids: idsToResolve })
            });
            const resolvedItems = await resolveRes.json();
            for (const item of resolvedItems) {
                resolvedMap[item.name.toLowerCase()] = item;
                resolvedMap[item.id] = item;
            }
        } catch (e) { console.error("Error resolving items:", e); }
    }
    
    const reprocessables = await loadReprocessables();
    
    // Collect all unique IDs that need pricing
    const allIdsToPrice = Object.values(resolvedMap).map(i => i.id);
    for (const item of Object.values(resolvedMap)) {
        if (item.reprocessing) {
            for (const matId of Object.keys(item.reprocessing)) {
                allIdsToPrice.push(parseInt(matId));
            }
        }
    }
    
    // Prefetch all prices
    const uniqueIds = [...new Set(allIdsToPrice)];
    if (uniqueIds.length > 0) {
        try {
            const res = await fetch('/api/market_prices/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type_ids: uniqueIds })
            });
            if (res.ok) {
                const data = await res.json();
                for (const type_id in data.prices) {
                    priceCache[type_id] = data.prices[type_id].price;
                }
            }
        } catch(e) { console.error("Price fetch failed:", e); }
    }
    
    const iceSet = new Set([
        "Blue Ice", "Compressed Blue Ice", "Clear Icicle", "Compressed Clear Icicle",
        "Dark Glitter", "Compressed Dark Glitter", "Enriched Clear Icicle", "Compressed Enriched Clear Icicle",
        "Gelidus", "Compressed Gelidus", "Glacial Mass", "Compressed Glacial Mass",
        "Glare Crust", "Compressed Glare Crust", "Krystallos", "Compressed Krystallos",
        "Pristine White Glaze", "Compressed Pristine White Glaze", "Smooth Glacial Mass", "Compressed Smooth Glacial Mass",
        "Thick Blue Ice", "Compressed Thick Blue Ice", "White Glaze", "Compressed White Glaze"
    ]);
    
    // Compute total
    for (const item of items) {
        let name, type_id, quantity, resolved;
        if (typeof item === 'string') {
            const p = parseItemString(item);
            name = p.name;
            quantity = p.quantity;
            resolved = resolvedMap[name.toLowerCase()];
        } else {
            type_id = item.type_id;
            quantity = item.quantity || 1;
            resolved = resolvedMap[type_id];
        }
        
        if (!resolved) {
            console.warn('[getContractValue] Skipping unresolvable item:', item);
            continue;
        }
        
        const isReprocessable = Object.keys(reprocessables).some(key => key.toLowerCase() === resolved.name.toLowerCase());
        
        if (isReprocessable && Object.keys(resolved.reprocessing).length > 0) {
            const isIce = iceSet.has(resolved.name);
            let reprocessValue = 0;
            for (const [matId, matData] of Object.entries(resolved.reprocessing)) {
                let matQty;
                if (isIce) {
                    matQty = Math.floor((matData.quantity * quantity) * 0.9063);
                } else {
                    matQty = Math.floor(matData.quantity * (quantity / 100) * 0.9063);
                }
                const matPrice = priceCache[matId] || 0;
                reprocessValue += matPrice * matQty;
            }
            console.log(`[getContractValue] ${resolved.name}: Always reprocessing - Value: ${reprocessValue.toLocaleString()}`);
            total += reprocessValue;
        } else {
            const rawValue = (priceCache[resolved.id] || 0) * quantity;
            console.log(`[getContractValue] ${resolved.name}: Using raw value (${rawValue.toLocaleString()})`);
            total += rawValue;
        }
    }
    
    console.log(`[getContractValue] total:`, total);
    return total;
}

function parseContractItems(textInput) {
    return textInput.trim().split('\n').filter(line => line.trim());
}

window.getContractValue = getContractValue;
window.parseContractItems = parseContractItems;
