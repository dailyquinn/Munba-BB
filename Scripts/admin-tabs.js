document.addEventListener('DOMContentLoaded', () => {
    // #region Element References
    // Get all necessary DOM elements for the admin page functionality.
    // This includes tabs, content areas, buttons, and input fields.
    const contractsTab = document.getElementById('contracts-tab');
    const multipliersTab = document.getElementById('multipliers-tab');
    const contractsContent = document.getElementById('contracts-content');
    const multipliersContent = document.getElementById('multipliers-content');
    const multipliersText = document.getElementById('multipliers-text');
    const saveBtn = document.getElementById('save-multipliers');
    const reloadBtn = document.getElementById('reload-multipliers');
    const downloadBtn = document.getElementById('download-multipliers');
    const statusSpan = document.getElementById('multipliers-status');
    const refreshBtn = document.getElementById('refresh-contracts');
    const readableListBody = document.getElementById('readable-list-body');

    // New Element References
    const searchInput = document.getElementById('search-input');
    const suggestionsBox = document.getElementById('suggestions');
    const modifierInput = document.getElementById('modifier-input');
    const addModifierBtn = document.getElementById('add-modifier-btn');
    const defaultModifierInput = document.getElementById('default-modifier-input');
    const saveDefaultBtn = document.getElementById('save-default-modifier-btn');

    // #endregion

    // #region State Variables
    // These maps store item and group data loaded from JSON files to facilitate searching and display.
    let itemMap = {};           // Maps item name (lowercase) -> item ID
    let groupMap = {};          // Maps group ID -> group name
    let idToNameMap = {};       // Maps item ID -> item name (for readable list)
    let groupIdToNameMap = {};  // Alias for groupMap, used for clarity in readable list rendering.
    let selectedEntry = null; // Stores { id, type: 'item'|'group', name }
    // #endregion

    // #region Tab Switching Logic
    if (contractsTab) {
        contractsTab.addEventListener('click', () => {
            contractsTab.classList.add('active');
            if (multipliersTab) multipliersTab.classList.remove('active');
            if (contractsContent) contractsContent.classList.add('active');
            if (multipliersContent) multipliersContent.classList.remove('active');
            if (refreshBtn) refreshBtn.style.display = 'inline-block';
        });
    }

    if (multipliersTab) {
        multipliersTab.addEventListener('click', () => {
            multipliersTab.classList.add('active');
            if (contractsTab) contractsTab.classList.remove('active');
            if (multipliersContent) multipliersContent.classList.add('active');
            if (contractsContent) contractsContent.classList.remove('active');
            if (refreshBtn) refreshBtn.style.display = 'none';
            
            // Load data when switching to tab
            loadMultipliers();
            loadItemData(); 
        });
    }
    // #endregion

    async function loadItemData() {
        if (!multipliersText.value) return;
        try {
            const data = JSON.parse(multipliersText.value);
            const ids = [];
            const group_ids = [];
            for (let key in data) {
                if (key.startsWith('group:')) {
                    group_ids.push(parseInt(key.split(':')[1]));
                } else {
                    ids.push(parseInt(key));
                }
            }
            if (ids.length === 0 && group_ids.length === 0) {
                renderReadableList();
                return;
            }
            
            const response = await fetch('/api/sde/names', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ ids, group_ids })
            });
            if (response.ok) {
                const nameData = await response.json();
                for (let key in nameData) {
                    if (key.startsWith('group:')) {
                        groupIdToNameMap[key.split(':')[1]] = nameData[key];
                    } else {
                        idToNameMap[key] = nameData[key];
                    }
                }
            }
            renderReadableList();
        } catch (e) {
            console.error('Error loading readable names:', e);
            renderReadableList();
        }
    }

    // #region Autocomplete Search Logic
    // Attaches an event listener to the search input field to provide autocomplete suggestions.
    if (searchInput) {
        searchInput.addEventListener('input', async (e) => {
            const query = e.target.value.toLowerCase();
            suggestionsBox.innerHTML = '';
            suggestionsBox.style.display = 'none';
            selectedEntry = null;

            if (query.length < 2) return; // Only start searching after 2 characters

            try {
                const response = await fetch(`/api/sde/search?q=${encodeURIComponent(query)}`);
                if (!response.ok) return;
                const matches = await response.json();

                // Display matches in the suggestions box
                if (matches.length > 0) {
                    suggestionsBox.style.display = 'block';
                    matches.forEach(match => {
                        const div = document.createElement('div');
                        div.className = 'suggestion-item';
                        div.innerHTML = `${match.name} <span class="suggestion-type">${match.type.toUpperCase()} (${match.id})</span>`;
                        div.onclick = () => {
                            searchInput.value = match.name;
                            selectedEntry = match;
                            suggestionsBox.style.display = 'none';
                            // Check if current JSON has this value
                            checkForExistingValue(match);
                        };
                        suggestionsBox.appendChild(div);
                    });
                }
            } catch (err) {
                console.error("Autocomplete search error:", err);
            }
        });

        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (e.target !== searchInput) suggestionsBox.style.display = 'none';
        });
    }
    // #endregion

    /**
     * Checks if the selected item/group already has a multiplier defined in the textarea.
     * If it exists, it populates the modifier input with the current value and changes the button text to "Update".
     * @param {object} entry - The selected entry object { id, type, name }.
     */
    function checkForExistingValue(entry) {
        try {
            const data = JSON.parse(multipliersText.value);
            let key = String(entry.id);
            if (entry.type === 'group') key = `group:${entry.id}`;
            
            if (data[key] !== undefined) {
                modifierInput.value = (data[key] * 100).toFixed(2).replace(/\.00$/, '');
                addModifierBtn.textContent = "Update";
            } else {
                modifierInput.value = '';
                addModifierBtn.textContent = "Add";
            }
        } catch (e) {}
    }

    // #region Add/Update Modifier Logic
    // Event listener for the "Add" or "Update" button.
    if (addModifierBtn) {
        addModifierBtn.addEventListener('click', () => {
            if (!selectedEntry && !searchInput.value) {
                alert('Please select an item or group.');
                return;
            }

            // Fallback: If a user types an ID directly but doesn't click a suggestion.
            if (!selectedEntry && !isNaN(parseInt(searchInput.value))) {
                selectedEntry = { id: parseInt(searchInput.value), type: 'item', name: 'Custom ID' };
            }

            if (!selectedEntry) {
                alert('Please select a valid item from the list.');
                return;
            }

            const percentage = parseFloat(modifierInput.value);
            if (isNaN(percentage) || percentage < 0) {
                alert('Please enter a valid percentage.');
                return;
            }

            try {
                // Parse current JSON
                let data = {};
                try {
                    data = JSON.parse(multipliersText.value);
                } catch (e) {
                    data = {};
                }

                // Construct Key
                let key = String(selectedEntry.id);
                if (selectedEntry.type === 'group') {
                    key = `group:${selectedEntry.id}`;
                }

                // Update Data (Convert % to decimal)
                data[key] = parseFloat((percentage / 100).toFixed(4));

                // Update Textarea
                multipliersText.value = JSON.stringify(data, null, 2);
                
                // Trigger Save
                saveMultipliers();

                // Clear inputs
                searchInput.value = '';
                modifierInput.value = '';
                selectedEntry = null;
                addModifierBtn.textContent = "Add";

            } catch (e) {
                console.error('Error updating JSON:', e);
                alert('Error updating JSON data.');
            }
        });
    }
    // #endregion

    /**
     * Renders a human-readable, sorted list of the current multipliers.
     * It parses the JSON from the multipliers textarea, uses the name maps to get readable names,
     * sorts the list alphabetically, and injects the HTML into the readable-list table body.
     */
    function renderReadableList() {
        if (!readableListBody || !multipliersText.value) return;

        let data = {};
        try {
            data = JSON.parse(multipliersText.value);
        } catch (e) {
            return;
        }

        readableListBody.innerHTML = '';

        // Convert data to array for sorting
        const entries = Object.entries(data)
            .filter(([key]) => key !== '_default') // Exclude default from list
            .map(([key, value]) => {
            let id = key;
            let type = 'Item';
            let name = '';

            if (key.startsWith('group:')) {
                type = 'Group';
                id = key.split(':')[1];
                name = groupIdToNameMap[id] || `Group ${id}`;
            } else {
                name = idToNameMap[id] || `Item ${id}`;
            }

            return { key, id, type, name, value };
        });

        // Sort alphabetically by name
        entries.sort((a, b) => a.name.localeCompare(b.name));

        if (entries.length === 0) {
            readableListBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#888;">No modifiers set</td></tr>';
            return;
        }

        entries.forEach(entry => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="color: ${entry.type === 'Group' ? '#87cefa' : 'white'}">${entry.name}</td>
                <td><span style="font-size:0.8em; opacity:0.7;">${entry.key}</span></td>
                <td><span class="modifier-tag">${(entry.value * 100).toFixed(0)}%</span></td>
                <td>
                    <button class="delete-modifier-btn" data-key="${entry.key}" style="background:#f44336; border:none; color:white; border-radius:3px; padding:4px 8px; cursor:pointer;">&times;</button>
                </td>
            `;
            readableListBody.appendChild(tr);
        });

        // Attach delete handlers
        document.querySelectorAll('.delete-modifier-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const keyToDelete = e.target.getAttribute('data-key');
                deleteModifier(keyToDelete);
            });
        });
    }

    /**
     * Deletes a specific multiplier from the JSON data.
     * Prompts the user for confirmation before proceeding.
     * @param {string} key - The key of the multiplier to delete (e.g., "34" or "group:18").
     */
    function deleteModifier(key) {
        if (!confirm('Are you sure you want to remove this modifier?')) return;
        try {
            const data = JSON.parse(multipliersText.value);
            delete data[key];
            multipliersText.value = JSON.stringify(data, null, 2);
            saveMultipliers();
        } catch (e) {
            console.error('Error deleting modifier:', e);
        }
    }

    /**
     * Fetches the `multipliers.json` file from the server.
     * Uses a cache-busting timestamp to ensure the latest version is loaded.
     * Updates the status span and renders the readable list upon successful load.
     */
    async function loadMultipliers() {
        if (!multipliersText || !statusSpan) return;
        try {
            statusSpan.textContent = 'Loading...';
            const response = await fetch(`/jsons/multipliers.json?t=${Date.now()}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            multipliersText.value = JSON.stringify(data, null, 2);
            statusSpan.textContent = 'Loaded successfully';
            statusSpan.style.color = '#4CAF50';
            
            // Populate default modifier input from _default key
            if (defaultModifierInput && data['_default'] !== undefined) {
                defaultModifierInput.value = (data['_default'] * 100).toFixed(1).replace(/\.0$/, '');
            } else if (defaultModifierInput) {
                defaultModifierInput.value = '93'; // Fallback if not set
            }
            
            renderReadableList(); // Render list after loading
        } catch (error) {
            console.error('Error loading multipliers:', error);
            statusSpan.textContent = `Error loading: ${error.message}`;
            statusSpan.style.color = '#f44336';
        }
    }

    /**
     * Saves the current content of the multipliers textarea to the server.
     * It sends a POST request to the `/api/save-multipliers` endpoint.
     * Provides UI feedback during and after the save operation.
     */
    async function saveMultipliers() {
        if (!multipliersText || !statusSpan) return;
        try {
            let jsonData;
            try {
                jsonData = JSON.parse(multipliersText.value);
            } catch (parseError) {
                throw new Error('Invalid JSON format');
            }

            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
            statusSpan.textContent = 'Saving...';
            statusSpan.style.color = '#ff9800';

            const response = await fetch('/api/save-multipliers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(jsonData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            statusSpan.textContent = 'Saved successfully';
            statusSpan.style.color = '#4CAF50';
            
            renderReadableList(); // Re-render list after saving
        } catch (error) {
            console.error('Error saving multipliers:', error);
            statusSpan.textContent = `Error saving: ${error.message}`;
            statusSpan.style.color = '#f44336';
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save Multipliers';
        }
    }

    // #region Button Event Listeners
    // Attaches event listeners to the Save, Reload, and Download buttons.
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            const content = multipliersText.value;
            const blob = new Blob([content], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'multipliers.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }

    if (saveBtn) saveBtn.addEventListener('click', saveMultipliers);
    if (reloadBtn) reloadBtn.addEventListener('click', loadMultipliers);

    // Default modifier save handler
    if (saveDefaultBtn) {
        saveDefaultBtn.addEventListener('click', () => {
            const pct = parseFloat(defaultModifierInput.value);
            if (isNaN(pct) || pct < 0) {
                alert('Please enter a valid percentage.');
                return;
            }
            try {
                let data = {};
                try { data = JSON.parse(multipliersText.value); } catch (e) { data = {}; }
                data['_default'] = parseFloat((pct / 100).toFixed(4));
                multipliersText.value = JSON.stringify(data, null, 2);
                saveMultipliers();
            } catch (e) {
                console.error('Error saving default modifier:', e);
                alert('Error saving default modifier.');
            }
        });
    }

    // Initial data load if the multipliers tab is active when the page loads.
    if (multipliersContent && multipliersContent.classList.contains('active')) {
        loadMultipliers();
        loadItemData();
    }
    // #endregion
});