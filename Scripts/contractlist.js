/**
 * Fetches and displays corporation contracts from the ESI.
 * It requires a valid EVE SSO token in localStorage.
 * It also validates contract contents against stored quotes.
 */
async function loadContracts() {
    const token = localStorage.getItem('token');
    const list = document.getElementById("contract-list");
    
    if (!list) {
        console.warn('[loadContracts] No #contract-list element found on page.');
        return;
    }

    if (!token) {
        list.innerHTML = "<p>Please log in to view contracts.</p>";
        return;
    }

    // Show loading state
    list.innerHTML = "<p>Loading contracts...</p>";

    try {
        // Step 1: Fetch current active contracts first
        const res = await fetch("/fetch_contracts/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ access_token: token, scope: "current" })
        });
        
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const data = await res.json();
        if (data.error) {
            list.innerHTML = `<p style="color: #f44336;">Error: ${data.error}</p>`;
            return;
        }
        
        const currentContracts = Array.isArray(data.contracts) ? data.contracts : [];
        const typeMap = {};

        async function resolveTypeNames(contractsList) {
            const unmapped = [];
            for (const c of contractsList) {
                if (Array.isArray(c.items)) {
                    for (const it of c.items) {
                        if (it.type_name && !it.type_name.startsWith('TypeID_')) {
                            typeMap[it.type_id] = it.type_name;
                        } else if (it.type_id && !typeMap[it.type_id]) {
                            unmapped.push(it.type_id);
                        }
                    }
                }
            }
            if (unmapped.length > 0) {
                try {
                    const sdeRes = await fetch('/api/sde/names', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ids: [...new Set(unmapped)] })
                    });
                    if (sdeRes.ok) {
                        const resolved = await sdeRes.json();
                        Object.assign(typeMap, resolved);
                    }
                } catch (e) { console.error("Error resolving type names:", e); }
            }
        }

        await resolveTypeNames(currentContracts);

        async function validateContract(contract) {
            const description = (contract && contract.title) ? contract.title : '';
            const quoteCodeMatch = description.match(/[A-F0-9]{6}/i);
            if (!quoteCodeMatch) return { valid: null, reason: 'No quote code found in title' };
            const quoteCode = quoteCodeMatch[0].toUpperCase();
            try {
                const quoteResponse = await fetch(`/api/quotes/${quoteCode}`);
                if (!quoteResponse.ok) return { valid: null, reason: 'Title doesn\'t match any quote.', quoteCode };
                const quoteData = await quoteResponse.json();
                if (quoteData.error) return { valid: null, reason: 'Title doesn\'t match any quote.', quoteCode };
                
                const originalContent = (quoteData && quoteData.content) ? String(quoteData.content).toLowerCase().trim() : '';
                const itemsArr = Array.isArray(contract.items) ? contract.items : [];
                const contractItems = itemsArr.map(item => {
                    const qty = (item && item.quantity) ? item.quantity : 1;
                    const itemName = typeMap[item && item.type_id] ? typeMap[item.type_id] : (item.type_name || `TypeID_${item && item.type_id}`);
                    return `${String(itemName).toLowerCase()} ${qty}`;
                });
                
                const originalLines = originalContent.split('\n').filter(line => line.trim());
                let matchedItems = 0;
                for (const originalLine of originalLines) {
                    const trimmedOriginal = originalLine.trim();
                    if (!trimmedOriginal) continue;
                    let itemName, quantity;
                    let m = trimmedOriginal.match(/^(.*?)(?:\s*)\((?:x)?\s*([\d,]+)\)\s*$/i);
                    if (m) {
                        itemName = m[1].trim().toLowerCase();
                        quantity = parseInt(m[2].replace(/,/g, '')) || 1;
                    } else if ((m = trimmedOriginal.match(/^(.*\S)\s+[xX]\s*([\d,]+)\s*$/))) {
                        itemName = m[1].trim().toLowerCase();
                        quantity = parseInt(m[2].replace(/,/g, '')) || 1;
                    } else if ((m = trimmedOriginal.match(/^(.*\S)\s+([\d,]+)\s*$/))) {
                        const before = m[1].trim().toLowerCase();
                        const full = trimmedOriginal.toLowerCase();
                        const fullExists = contractItems.some(cl => cl.startsWith(full + ' '));
                        if (fullExists) { itemName = full; quantity = 1; }
                        else { itemName = before; quantity = parseInt(m[2].replace(/,/g, '')) || 1; }
                    } else {
                        itemName = trimmedOriginal.toLowerCase();
                        quantity = 1;
                    }

                    const contractMatch = contractItems.find(contractLine => {
                        const contractItemMatch = contractLine.match(/^(.+?)\s+(\d+)$/);
                        if (contractItemMatch) {
                            const contractItemName = contractItemMatch[1].trim().toLowerCase();
                            const contractQuantity = parseInt(contractItemMatch[2]);
                            return contractItemName === itemName && contractQuantity === quantity;
                        }
                        return false;
                    });
                    if (contractMatch) matchedItems++;
                }
                const matchPercentage = originalLines.length > 0 ? (matchedItems / originalLines.length) : 0;
                const isValid = matchPercentage >= 0.8;
                return { 
                    valid: isValid, 
                    reason: isValid ? 'Items match quote' : `Only ${Math.round(matchPercentage * 100)}% of items match`,
                    quoteCode,
                    matchPercentage: Math.round(matchPercentage * 100)
                };
            } catch (error) {
                return { valid: false, reason: 'Network or server error', quoteCode };
            }
        }

        function renderCard(contract, idx) {
            const statusBadge = `<span style="padding:2px 8px; border-radius:4px; font-size:0.8em; font-weight:bold; background:${contract.is_current ? '#2e7d32' : '#424242'}; color:#fff;">${contract.status || 'unknown'}</span>`;
            return `
            <div class="contract" style="margin-bottom: 16px;">
                <div class="issuer-row" style="display:flex; justify-content:space-between; align-items:center;">
                    <p><strong>Issuer:</strong> ${contract.issuer_name || contract.issuer_id} ${statusBadge}</p>
                    <div class="show-items-container">
                        <span class="validation-indicator" id="validation-${idx}">⏳</span>
                        <button class="toggleItems" data-idx="${idx}">Show Items</button>
                    </div>
                </div>
                <p><strong>Price:</strong> ${contract.price.toLocaleString()} ISK</p>
                <p><strong>Title:</strong> ${contract.title || 'No title'}</p>
                <p class="contract-value" id="contract-value-${idx}"><em>Calculating value...</em></p>
                <p class="validation-status" id="validation-status-${idx}"><em>Validating quote...</em></p>
                <div class="itemCollapse" id="items-${idx}" style="display: none;">
                    <ul>
                        ${(contract.items || []).map(item => `<li>${typeMap[item.type_id] || item.type_name || item.type_id} (x${item.quantity})</li>`).join('')}
                    </ul>
                </div>
            </div>`;
        }

        async function processCardValues(contractsList, startIndex) {
            contractsList.forEach(async (contract, i) => {
                const idx = startIndex + i;
                if (typeof window.getContractValue === 'function') {
                    try {
                        const val = await window.getContractValue(contract.items || []);
                        const valueElem = document.getElementById(`contract-value-${idx}`);
                        if (valueElem) valueElem.textContent = `Estimated Value: ${val.toLocaleString()} ISK`;
                    } catch (e) {
                        const valueElem = document.getElementById(`contract-value-${idx}`);
                        if (valueElem) valueElem.textContent = 'Estimated Value: N/A';
                    }
                }
                const validation = await validateContract(contract);
                const indicatorElem = document.getElementById(`validation-${idx}`);
                const statusElem = document.getElementById(`validation-status-${idx}`);
                if (indicatorElem && statusElem) {
                    if (validation.valid === true) {
                        indicatorElem.textContent = '✅';
                        indicatorElem.className = 'validation-indicator validation-valid';
                        statusElem.textContent = `✅ Valid: ${validation.reason} (${validation.quoteCode})`;
                        statusElem.style.color = '#4CAF50';
                    } else if (validation.valid === false) {
                        indicatorElem.textContent = '❌';
                        indicatorElem.className = 'validation-indicator validation-invalid';
                        statusElem.textContent = `❌ Invalid: ${validation.reason}${validation.quoteCode ? ` (${validation.quoteCode})` : ''}`;
                        statusElem.style.color = '#f44336';
                    } else {
                        indicatorElem.textContent = '⚠️';
                        indicatorElem.className = 'validation-indicator validation-unknown';
                        statusElem.textContent = `⚠️ Warning: ${validation.reason}`;
                        statusElem.style.color = '#ff9800';
                    }
                }
            });
        }

        // Render Current Active Contracts section immediately
        let html = `<h2>Current Active Contracts (${currentContracts.length})</h2>`;
        if (currentContracts.length === 0) {
            html += `<p style="margin-bottom: 24px; color: #888;">No active contracts pending processing.</p>`;
        } else {
            html += currentContracts.map((c, i) => renderCard(c, i)).join('');
        }

        const totalHistoric = data.total_historic || 0;
        if (totalHistoric > 0) {
            html += `
            <div id="historic-section" style="margin-top: 36px;">
                <h2>Historic Contracts (${totalHistoric})</h2>
                <div id="historic-list-container"></div>
                <p id="historic-loader-status" style="color: #aaa; margin-top: 12px;">⏳ Loading historic contracts (5 at a time)...</p>
            </div>`;
        }

        list.innerHTML = html;
        await processCardValues(currentContracts, 0);

        // Re-attach toggle handlers for current cards
        document.querySelectorAll('.toggleItems').forEach(btn => {
            btn.addEventListener('click', function() {
                const idx = this.getAttribute('data-idx');
                const itemsDiv = document.getElementById(`items-${idx}`);
                if (itemsDiv) {
                    itemsDiv.style.display = itemsDiv.style.display === 'none' ? 'block' : 'none';
                    this.textContent = itemsDiv.style.display === 'none' ? 'Show Items' : 'Hide Items';
                }
            });
        });

        // Step 2: Fetch historic contracts in chunks of 5
        if (totalHistoric > 0) {
            let offset = 0;
            const limit = 5;
            let totalLoaded = currentContracts.length;

            const historicContainer = document.getElementById('historic-list-container');
            const statusLabel = document.getElementById('historic-loader-status');

            while (offset < totalHistoric) {
                try {
                    const hRes = await fetch("/fetch_contracts/", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ access_token: token, scope: "historic", offset, limit })
                    });
                    if (!hRes.ok) break;
                    const hData = await hRes.json();
                    const batch = Array.isArray(hData.contracts) ? hData.contracts : [];
                    if (batch.length === 0) break;

                    await resolveTypeNames(batch);

                    const batchHtml = batch.map((c, i) => renderCard(c, totalLoaded + i)).join('');
                    if (historicContainer) historicContainer.innerHTML += batchHtml;

                    await processCardValues(batch, totalLoaded);

                    // Re-attach button listeners for newly rendered batch
                    document.querySelectorAll('.toggleItems').forEach(btn => {
                        btn.onclick = function() {
                            const idx = this.getAttribute('data-idx');
                            const itemsDiv = document.getElementById(`items-${idx}`);
                            if (itemsDiv) {
                                itemsDiv.style.display = itemsDiv.style.display === 'none' ? 'block' : 'none';
                                this.textContent = itemsDiv.style.display === 'none' ? 'Show Items' : 'Hide Items';
                            }
                        };
                    });

                    totalLoaded += batch.length;
                    offset += limit;

                    if (statusLabel) {
                        statusLabel.textContent = `Loaded ${Math.min(offset, totalHistoric)} of ${totalHistoric} historic contracts...`;
                    }

                    if (!hData.has_more) break;
                    // Short 300ms pause between chunk requests
                    await new Promise(r => setTimeout(r, 300));
                } catch (err) {
                    console.error("Error fetching historic chunk:", err);
                    break;
                }
            }

            if (statusLabel) {
                statusLabel.textContent = `✓ All ${totalHistoric} historic contracts loaded.`;
                statusLabel.style.color = '#4CAF50';
            }
        }
        
        // Add event listeners to the "Show/Hide Items" buttons for each contract.
        document.querySelectorAll('.toggleItems').forEach(btn => {
            btn.addEventListener('click', function() {
                const idx = this.getAttribute('data-idx');
                const itemsDiv = document.getElementById(`items-${idx}`);
                if (itemsDiv.style.display === 'none') {
                    itemsDiv.style.display = 'block';
                    this.textContent = 'Hide Items';
                } else {
                    itemsDiv.style.display = 'none';
                    this.textContent = 'Show Items';
                }
            });
        });
        
    } catch (error) {
        console.error('Error loading contracts:', error);
        list.innerHTML = `<p style="color: #f44336;">Error loading contracts: ${error.message}</p>`;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', loadContracts);

// Add refresh button functionality
// Allows the user to manually reload the contract list.
document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('refresh-contracts');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshBtn.textContent = 'Refreshing...';
            refreshBtn.disabled = true;
            loadContracts().then(() => {
                refreshBtn.textContent = 'Refresh Contracts';
                refreshBtn.disabled = false;
            }).catch(() => {
                refreshBtn.textContent = 'Refresh Contracts';
                refreshBtn.disabled = false;
            });
        });
    }
});