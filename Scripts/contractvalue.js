let typeMapPromise = null;
async function loadTypeMap() {
    if (!typeMapPromise) {
        typeMapPromise = fetch('jsons/type_ids.json').then(r => r.json());
    }
    return typeMapPromise;
}

let reprocessingMapPromise = null;
async function loadReprocessingMap() {
    if (!reprocessingMapPromise) {
        reprocessingMapPromise = fetch('jsons/reprocessing_map.json').then(r => r.json());
    }
    return reprocessingMapPromise;
}

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
    // 1. Parenthetical (x5) or (5)
    let m = raw.match(/^(.*?)(?:\s*)\((?:x)?\s*([\d,]+)\)\s*$/i);
    if (m) {
        return { name: m[1].trim(), quantity: parseInt(m[2].replace(/,/g, ''), 10) || 1 };
    }
    // 2. Explicit x notation: Item x5
    m = raw.match(/^(.*\S)\s+[xX]\s*([\d,]+)\s*$/);
    if (m) {
        return { name: m[1].trim(), quantity: parseInt(m[2].replace(/,/g, ''), 10) || 1 };
    }
    // 3. Trailing number ambiguous: decide if number is part of name
    m = raw.match(/^(.*\S)\s+([\d,]+)\s*$/);
    if (m) {
        const before = m[1].trim();
        const numPart = m[2];
        // Load type map to check full vs prefix name
        const sizeNumbers = new Set(['1','50','75','100','150','200','400','800','3200']);
        if (sizeNumbers.has(numPart.replace(/,/g,''))) {
            // Treat as part of name (e.g., Navy Cap Booster 400)
            return { name: raw, quantity: 1 };
        }
        return { name: before, quantity: parseInt(numPart.replace(/,/g,''),10) || 1 };
    }
    // 4. No quantity specified
    return { name: raw, quantity: 1 };
}

// Convert item name to type_id using typeMap
async function getTypeId(itemName) {
    const typeMapRaw = await loadTypeMap();
    // Create lowercase
    const typeMap = {};
    for (const [name, id] of Object.entries(typeMapRaw)) {
        typeMap[name.toLowerCase()] = id;
    }
    return typeMap[itemName.toLowerCase()] || null;
}

const priceCache = {};
async function getItemPrice(type_id) {
    if (priceCache[type_id] !== undefined) {
        return priceCache[type_id];
    }
    // Use backend API for market prices
    const url = `/api/market_prices/?type_ids=${type_id}`;
    try {
        const res = await fetch(url);
        if (!res.ok) {
            console.error(`[getItemPrice] HTTP error ${res.status} for type_id ${type_id}`);
            priceCache[type_id] = 0;
            return 0;
        }
        const data = await res.json();
        // data.prices = { type_id: { price, last_updated } }
        const price = data.prices && data.prices[type_id] && data.prices[type_id].price ? data.prices[type_id].price : 0;
        priceCache[type_id] = price;
        return price;
    } catch (e) {
        console.error(`[getItemPrice] Exception for type_id ${type_id}:`, e);
        priceCache[type_id] = 0;
        return 0;
    }
}

// Calculate reprocessed value for an item using same math as Reprocess & Market.js
async function getReprocessedValue(type_id, quantity) {
    const reprocessingMap = await loadReprocessingMap();
    const materials = reprocessingMap[type_id.toString()];
    
    if (!materials) {
        return null; // Item cannot be reprocessed
    }
    
    // Define ice items (same list as Reprocess & Market.js)
    const iceSet = new Set([
        "Blue Ice", "Compressed Blue Ice", "Clear Icicle", "Compressed Clear Icicle",
        "Dark Glitter", "Compressed Dark Glitter", "Enriched Clear Icicle", "Compressed Enriched Clear Icicle",
        "Gelidus", "Compressed Gelidus", "Glacial Mass", "Compressed Glacial Mass",
        "Glare Crust", "Compressed Glare Crust", "Krystallos", "Compressed Krystallos",
        "Pristine White Glaze", "Compressed Pristine White Glaze", "Smooth Glacial Mass", "Compressed Smooth Glacial Mass",
        "Thick Blue Ice", "Compressed Thick Blue Ice", "White Glaze", "Compressed White Glaze"
    ]);
    
    // Get item name to check if it's ice
    const typeMap = await loadTypeMap();
    const itemName = Object.keys(typeMap).find(name => typeMap[name] == type_id);
    const isIce = itemName && iceSet.has(itemName);
    
    let totalValue = 0;
    for (const [materialTypeId, baseQuantity] of Object.entries(materials)) {
        let materialQuantity;
        
        // Apply reprocessing math (same as Reprocess & Market.js)
        if (isIce) {
            materialQuantity = Math.floor((baseQuantity * quantity) * 0.9063);
        } else {
            materialQuantity = Math.floor(baseQuantity * (quantity / 100) * 0.9063);
        }
        
        // Use straight Jita buy price (no multipliers)
        const materialPrice = await getItemPrice(parseInt(materialTypeId));
        totalValue += materialPrice * materialQuantity;
    }
    
    return totalValue;
}

// Get the best value for an item (always reprocess if in reprocessables.json)
async function getBestItemValue(type_id, quantity) {
    const reprocessables = await loadReprocessables();
    const typeMap = await loadTypeMap();
    
    // Get item name to check if it's in reprocessables
    const itemName = Object.keys(typeMap).find(name => typeMap[name] == type_id);
    
    // Check if item is in reprocessables.json (case-insensitive)
    const isReprocessable = itemName && Object.keys(reprocessables).some(key => 
        key.toLowerCase() === itemName.toLowerCase()
    );
    
    if (isReprocessable) {
        // Always reprocess if item is in reprocessables.json
        const reprocessedValue = await getReprocessedValue(type_id, quantity);
        if (reprocessedValue !== null) {
            console.log(`[getBestItemValue] type_id ${type_id} (${itemName}): Always reprocessing - Value: ${reprocessedValue.toLocaleString()}`);
            return reprocessedValue;
        }
    }
    
    // If not reprocessable, use raw value
    const rawPrice = await getItemPrice(type_id);
    const rawValue = rawPrice * quantity;
    console.log(`[getBestItemValue] type_id ${type_id} (${itemName}): Using raw value (${rawValue.toLocaleString()})`);
    return rawValue;
}

// Calculate total value for a list of items (can be objects with type_id or strings to parse)
async function getContractValue(items) {
    let total = 0;
    for (const item of items) {
        let type_id, quantity;
        
        if (typeof item === 'string') {
            // Parse string format like "Compressed Plunder Mordunium (x1143658)"
            const parsed = parseItemString(item);
            type_id = await getTypeId(parsed.name);
            quantity = parsed.quantity;
            
            if (!type_id) {
                console.warn('[getContractValue] Could not find type_id for item:', parsed.name);
                continue;
            }
            } else if (item && (item.type_id !== undefined && item.type_id !== null)) {
                // Object with type_id property
                type_id = item.type_id;
                quantity = (item.quantity !== undefined && item.quantity !== null) ? item.quantity : 1;
        } else {
            console.warn('[getContractValue] Skipping invalid item:', item);
            continue;
        }
        
        const value = await getBestItemValue(type_id, quantity);
        console.log(`[getContractValue] item:`, item, 'type_id:', type_id, 'quantity:', quantity, 'best_value:', value);
        total += value;
    }
    console.log(`[getContractValue] total:`, total);
    return total;
}

// Parse multiple item strings from text input
function parseContractItems(textInput) {
    return textInput.trim().split('\n').filter(line => line.trim());
}

window.getContractValue = getContractValue;
window.parseContractItems = parseContractItems;
