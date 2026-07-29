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
        const res = await fetch("/fetch_contracts/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ access_token: token })
        });
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        
        const data = await res.json();
        
        if (data.error) {
            list.innerHTML = `<p style="color: #f44336;">Error: ${data.error}</p>`;
            return;
        }
        
        const contracts = Array.isArray(data.contracts) ? data.contracts : [];

        if (!contracts.length) {
            list.innerHTML = "<p>No contracts found.</p>";
            return;
        }
        
        // Fetch the mapping of type IDs to item names.
        const typeMapRaw = await fetch('jsons/type_ids.json').then(r => r.json());
        // Invert the map to be ID -> Name for easy lookup.
        const typeMap = {};
        for (const [name, id] of Object.entries(typeMapRaw)) {
            typeMap[id] = name;
        }

        /**
         * Validates a single contract by comparing its contents to a quote code found in its title.
         * @param {object} contract - The contract object from the ESI.
         * @param {number} contractIndex - The index of the contract in the list, used for targeting DOM elements.
         * @returns {Promise<object>} A promise that resolves to a validation result object.
         *                          { valid: boolean|null, reason: string, quoteCode?: string, matchPercentage?: number }
         *                          `valid` is null if no quote code is found.
         */
        async function validateContract(contract, contractIndex) {
            const description = (contract && contract.title) ? contract.title : '';
            
            // Look for quote code in the title
            const quoteCodeMatch = description.match(/[A-F0-9]{6}/i);
            if (!quoteCodeMatch) {
                return { valid: null, reason: 'No quote code found in title' };
            }
            
            const quoteCode = quoteCodeMatch[0].toUpperCase();
            
            try {
                // Fetch the original quote content
                const quoteResponse = await fetch(`/api/quotes/${quoteCode}`);
                
                if (!quoteResponse.ok) {
                    return { valid: null, reason: 'Title doesn\'t match any quote.', quoteCode: quoteCode };
                }
                
                const quoteData = await quoteResponse.json();
            
                if (quoteData.error) {
                    return { valid: null, reason: 'Title doesn\'t match any quote.', quoteCode: quoteCode };
                }
                
                // Parse the original quote content and contract items for comparison
                const originalContent = (quoteData && quoteData.content) ? String(quoteData.content).toLowerCase().trim() : '';
                const itemsArr = Array.isArray(contract.items) ? contract.items : [];
                const contractItems = itemsArr.map(item => {
                    const qty = (item && item.quantity) ? item.quantity : 1;
                    const itemName = typeMap[item && item.type_id] ? typeMap[item.type_id] : `TypeID_${item && item.type_id}`;
                    return `${String(itemName).toLowerCase()} ${qty}`;
                });
                
                // Create a comparable string from contract items
                // This normalizes the contract's contents for comparison with the quote.
                const contractContent = contractItems.join('\n');
                
                const originalLines = originalContent.split('\n').filter(line => line.trim());
                const contractLines = contractItems;
                
                // Check if most items from the quote are present in the contract
                let matchedItems = 0;
                for (const originalLine of originalLines) {
                    const trimmedOriginal = originalLine.trim();
                    if (!trimmedOriginal) continue;
                    let itemName;
                    let quantity;
                    // Attempt to parse various quantity formats from the original quote text (e.g., "Item Name x5", "Item Name (5)", "Item Name 5").
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
                        // If full line matches a contract item (name with number) treat as quantity 1
                        const fullExists = contractLines.some(cl => cl.startsWith(full + ' '));
                        if (fullExists) {
                            itemName = full;
                            quantity = 1;
                        } else {
                            itemName = before;
                            quantity = parseInt(m[2].replace(/,/g, '')) || 1;
                        }
                    } else {
                        // No quantity specified: assume 1
                        itemName = trimmedOriginal.toLowerCase();
                        quantity = 1;
                    }

                    // Find a matching item and quantity in the contract.
                    const contractMatch = contractLines.find(contractLine => {
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
                
                // A contract is considered valid if at least 80% of the items from the quote are present in the contract.
                const matchPercentage = originalLines.length > 0 ? (matchedItems / originalLines.length) : 0;
                const isValid = matchPercentage >= 0.8;
                
                return { 
                    valid: isValid, 
                    reason: isValid ? 'Items match quote' : `Only ${Math.round(matchPercentage * 100)}% of items match`,
                    quoteCode: quoteCode,
                    matchPercentage: Math.round(matchPercentage * 100)
                };
                
            } catch (error) {
                console.error('Error validating contract:', error);
                return { valid: false, reason: 'Network or server error', quoteCode: quoteCode };
            }
        }

        // Initial render of the contract list with placeholders for calculated values and validation status.
        list.innerHTML = contracts.map((contract, idx) => `
            <div class="contract">
                <div class="issuer-row">
                    <p><strong>Issuer:</strong> ${contract.issuer_name || contract.issuer_id}</p>
                    <div class="show-items-container">
                        <span class="validation-indicator" id="validation-${idx}">⏳</span>
                        <button class="toggleItems" data-idx="${idx}">Show Items</button>
                    </div>
                </div>
                <p><strong>Price:</strong> ${contract.price.toLocaleString()}</p>
                <p><strong>Title:</strong> ${contract.title || 'No title'}</p>
                <p class="contract-value" id="contract-value-${idx}"><em>Calculating value...</em></p>
                <p class="validation-status" id="validation-status-${idx}"><em>Validating quote...</em></p>
                <div class="itemCollapse" id="items-${idx}" style="display: none;">
                    <ul>
                        ${contract.items.map(item => `<li>${typeMap[item.type_id] || item.type_id} (x${item.quantity})</li>`).join('')}
                    </ul>
                </div>
            </div>
        `).join('');
        
        // Validate each contract and calculate values
        contracts.forEach(async (contract, idx) => {
            // Asynchronously calculate the estimated market value of the contract's items.
            if (typeof window.getContractValue === 'function') {
                try {
                    await window.getContractValue(contract.items || [] ).then(value => {
                        const valueElem = document.getElementById(`contract-value-${idx}`);
                        if (valueElem) valueElem.textContent = `Estimated Value: ${value.toLocaleString()} ISK`;
                    });
                } catch (e) {
                    console.error('[loadContracts] getContractValue error for idx', idx, e);
                }
            } else {
                const valueElem = document.getElementById(`contract-value-${idx}`);
                if (valueElem) valueElem.textContent = 'Estimated Value: N/A';
            }
            
            // Asynchronously validate the contract against its quote code.
            const validation = await validateContract(contract, idx);
            const indicatorElem = document.getElementById(`validation-${idx}`);
            const statusElem = document.getElementById(`validation-status-${idx}`);
            
            if (indicatorElem && statusElem) {
                if (validation.valid === true) {
                    // Code found and contents match = Green
                    indicatorElem.textContent = '✅';
                    indicatorElem.className = 'validation-indicator validation-valid';
                    statusElem.textContent = `✅ Valid: ${validation.reason} (${validation.quoteCode})`;
                    statusElem.style.color = '#4CAF50';
                } else if (validation.valid === false) {
                    // Code found but contents don't match = Red
                    indicatorElem.textContent = '❌';
                    indicatorElem.className = 'validation-indicator validation-invalid';
                    statusElem.textContent = `❌ Invalid: ${validation.reason}${validation.quoteCode ? ` (${validation.quoteCode})` : ''}`;
                    statusElem.style.color = '#f44336';
                } else {
                    // validation.valid === null (no quote code found in title) = Yellow
                    indicatorElem.textContent = '⚠️';
                    indicatorElem.className = 'validation-indicator validation-unknown';
                    statusElem.textContent = `⚠️ Warning: ${validation.reason}`;
                    statusElem.style.color = '#ff9800';
                }
            }
        });
        
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