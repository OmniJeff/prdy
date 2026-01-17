const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const generateBtn = document.getElementById('generate-btn');
const clearBtn = document.getElementById('clear-btn');
const copyBtn = document.getElementById('copy-btn');
const prdPreview = document.getElementById('prd-preview');
const prdContent = document.getElementById('prd-content');
const prdFilename = document.getElementById('prd-filename');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');

// Sidebar elements
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const prdsList = document.getElementById('prds-list');
const prdsCount = document.getElementById('prds-count');
const noPrds = document.getElementById('no-prds');
const navNew = document.getElementById('nav-new');
const navPrds = document.getElementById('nav-prds');
const navHelp = document.getElementById('nav-help');
const navResearch = document.getElementById('nav-research');

// Research modal elements
const researchModal = document.getElementById('research-modal');
const researchModalClose = document.getElementById('research-modal-close');
const researchSource = document.getElementById('research-source');
const runContextResearchBtn = document.getElementById('run-context-research');
const researchCustomQuery = document.getElementById('research-custom-query');
const runCustomResearchBtn = document.getElementById('run-custom-research');

// Save modal elements
const saveModal = document.getElementById('save-modal');
const saveModalClose = document.getElementById('save-modal-close');
const saveToPrdBtn = document.getElementById('save-to-prd');
const saveSeparateBtn = document.getElementById('save-separate');
const prdSelectSection = document.getElementById('prd-select-section');
const savePrdSelect = document.getElementById('save-prd-select');
const confirmSavePrdBtn = document.getElementById('confirm-save-prd');

// Store current research data for saving
let currentResearchData = null;

// Multi-select elements
const selectToggle = document.getElementById('select-toggle');
const bulkActions = document.getElementById('bulk-actions');
const archiveSelectedBtn = document.getElementById('archive-selected');

let messageCount = 0;
let currentPrdContent = '';
let multiSelectMode = false;
let selectedPrds = new Set();

// Load existing PRDs on page load
loadExistingPrds();

// Sidebar toggle
sidebarToggle.addEventListener('click', function() {
    sidebar.classList.toggle('collapsed');
});

// Nav item: New PRD
navNew.addEventListener('click', function() {
    setActiveNav(navNew);
    clearBtn.click();
});

// Nav item: My PRDs - scroll to PRDs section
navPrds.addEventListener('click', function() {
    setActiveNav(navPrds);
    const prdsSection = document.getElementById('prds-section');
    prdsSection.scrollIntoView({ behavior: 'smooth' });
});

// Nav item: Help
navHelp.addEventListener('click', function() {
    alert('PRDy Help\n\n' +
        '1. Describe your product idea in the chat\n' +
        '2. Answer the assistant\'s questions\n' +
        '3. Click "Generate PRD" when ready\n' +
        '4. Your PRD will be saved to the output/ folder\n\n' +
        'To iterate on an existing PRD, click it in the sidebar.\n\n' +
        'Use Research to gather competitive intelligence from the web.');
});

// Nav item: Research - open modal and populate PRD dropdown
navResearch.addEventListener('click', async function() {
    await populateResearchDropdown();
    researchModal.classList.remove('hidden');
});

// Close research modal
researchModalClose.addEventListener('click', function() {
    researchModal.classList.add('hidden');
});

// Close modal on backdrop click
researchModal.addEventListener('click', function(e) {
    if (e.target === researchModal) {
        researchModal.classList.add('hidden');
    }
});

// Run context-aware research
runContextResearchBtn.addEventListener('click', async function() {
    const source = researchSource.value;
    researchModal.classList.add('hidden');
    await runContextResearch(source);
});

// Run custom research
runCustomResearchBtn.addEventListener('click', async function() {
    const query = researchCustomQuery.value.trim();
    if (!query) {
        alert('Please enter a search query');
        researchCustomQuery.focus();
        return;
    }

    researchModal.classList.add('hidden');
    await runCustomSearch(query);
});

// Handle Enter key in custom query input
researchCustomQuery.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        runCustomResearchBtn.click();
    }
});

// Save modal handlers
saveModalClose.addEventListener('click', function() {
    saveModal.classList.add('hidden');
    prdSelectSection.classList.add('hidden');
});

saveModal.addEventListener('click', function(e) {
    if (e.target === saveModal) {
        saveModal.classList.add('hidden');
        prdSelectSection.classList.add('hidden');
    }
});

saveToPrdBtn.addEventListener('click', async function() {
    // Populate PRD dropdown and show selection
    await populateSavePrdDropdown();
    prdSelectSection.classList.remove('hidden');
});

saveSeparateBtn.addEventListener('click', async function() {
    saveModal.classList.add('hidden');
    await saveResearch('separate_file');
});

confirmSavePrdBtn.addEventListener('click', async function() {
    saveModal.classList.add('hidden');
    prdSelectSection.classList.add('hidden');
    await saveResearch('append_prd', savePrdSelect.value);
});

async function populateResearchDropdown() {
    try {
        const response = await fetch('/api/prds');
        const data = await response.json();

        // Reset dropdown
        researchSource.innerHTML = '<option value="conversation">Current Conversation</option>';

        // Add PRD options
        if (data.prds && data.prds.length > 0) {
            data.prds.forEach(prd => {
                const option = document.createElement('option');
                option.value = prd.filename;
                option.textContent = `${prd.name} (${prd.date})`;
                researchSource.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load PRDs for research:', error);
    }
}

async function populateSavePrdDropdown() {
    try {
        const response = await fetch('/api/prds');
        const data = await response.json();

        savePrdSelect.innerHTML = '';

        if (data.prds && data.prds.length > 0) {
            data.prds.forEach(prd => {
                const option = document.createElement('option');
                option.value = prd.filename;
                option.textContent = `${prd.name} (${prd.date})`;
                savePrdSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load PRDs:', error);
    }
}

async function runContextResearch(source) {
    showLoading('Analyzing and researching competitors...');

    try {
        const response = await fetch('/api/research/context', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ source: source })
        });

        const data = await response.json();

        if (!response.ok) {
            addMessage(data.message || data.error || 'Research failed', 'assistant');
            return;
        }

        // Store research data for saving
        currentResearchData = {
            analysis: data.analysis,
            product_name: data.product_name,
            source: data.source
        };

        // Add research message to chat
        const sourceLabel = source === 'conversation' ? 'current conversation' : source;
        addMessage(`Researching competitors for: ${data.product_name}`, 'user');

        // Debug: show research stats
        if (data.debug) {
            console.log('Research debug:', data.debug);
            addMessage(`[DEBUG] Search: "${data.debug.search_term}" | Analysis: ${data.debug.analysis_length} chars`, 'assistant');
        }

        // Add analysis to chat
        if (data.analysis) {
            addMessage(data.analysis, 'assistant');
        }

        // Enable generate button
        generateBtn.disabled = false;

        // Show save options modal
        saveModal.classList.remove('hidden');

    } catch (error) {
        addMessage('Error: Failed to conduct research. Please try again.', 'assistant');
        console.error('Research error:', error);
    } finally {
        hideLoading();
    }
}

async function runCustomSearch(query) {
    showLoading('Searching...');

    try {
        const response = await fetch('/api/research/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        });

        const data = await response.json();

        if (data.error) {
            addMessage('Search Error: ' + data.error, 'assistant');
            return;
        }

        // Format and display results
        let resultsText = `Search results for "${query}":\n\n`;
        if (data.results && data.results.length > 0) {
            data.results.forEach(r => {
                resultsText += `**${r.title}**\n${r.snippet}\n\n`;
            });
        } else {
            resultsText = 'No results found.';
        }

        addMessage(query, 'user');
        addMessage(resultsText, 'assistant');

    } catch (error) {
        addMessage('Error: Search failed', 'assistant');
        console.error('Search error:', error);
    } finally {
        hideLoading();
        researchCustomQuery.value = '';
    }
}

async function saveResearch(saveType, prdFilename = '') {
    if (!currentResearchData) {
        addMessage('No research data to save.', 'assistant');
        return;
    }

    showLoading('Saving...');

    try {
        const response = await fetch('/api/research/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: currentResearchData.analysis,
                save_type: saveType,
                prd_filename: prdFilename,
                product_name: currentResearchData.product_name
            })
        });

        const data = await response.json();

        if (data.error) {
            addMessage('Save Error: ' + data.error, 'assistant');
            return;
        }

        addMessage(data.message, 'assistant');

        // Refresh PRD list
        loadExistingPrds();

        // Clear current research data
        currentResearchData = null;

    } catch (error) {
        addMessage('Error: Failed to save research', 'assistant');
        console.error('Save error:', error);
    } finally {
        hideLoading();
    }
}

function setActiveNav(activeItem) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    activeItem.classList.add('active');
}

// Auto-resize textarea
messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
});

// Handle Enter to send (Shift+Enter for new line)
messageInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

// Send message
chatForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message) return;

    // Add user message to chat
    addMessage(message, 'user');
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Show loading
    showLoading('Thinking...');
    sendBtn.disabled = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        if (data.error) {
            addMessage('Error: ' + data.error, 'assistant');
        } else {
            addMessage(data.response, 'assistant');
            messageCount = data.message_count;

            // Enable generate button after a few exchanges
            if (messageCount >= 4) {
                generateBtn.disabled = false;
            }
        }
    } catch (error) {
        addMessage('Error: Failed to connect to server', 'assistant');
    } finally {
        hideLoading();
        sendBtn.disabled = false;
        messageInput.focus();
    }
});

// Generate PRD
generateBtn.addEventListener('click', async function() {
    showLoading('Generating PRD...');
    generateBtn.disabled = true;

    try {
        const response = await fetch('/api/generate-prd', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            currentPrdContent = data.prd;
            prdContent.textContent = data.prd;
            prdFilename.textContent = data.filename;
            prdPreview.classList.remove('hidden');
            prdPreview.scrollIntoView({ behavior: 'smooth' });
            // Refresh the sidebar PRD list
            loadExistingPrds();
        }
    } catch (error) {
        alert('Error: Failed to generate PRD');
    } finally {
        hideLoading();
        generateBtn.disabled = false;
    }
});

// Clear conversation
clearBtn.addEventListener('click', async function() {
    if (!confirm('Start a new conversation? This will clear the current chat.')) {
        return;
    }

    try {
        await fetch('/api/clear', { method: 'POST' });

        // Reset UI
        chatMessages.innerHTML = `
            <div class="message assistant">
                <div class="message-content">
                    <p>Hello! I'm PRDy, your AI-powered Product Requirements Document assistant. I'll help you define and create a comprehensive PRD for your product or feature.</p>
                    <p>What product or feature would you like to define today?</p>
                </div>
            </div>
        `;
        prdPreview.classList.add('hidden');
        generateBtn.disabled = true;
        messageCount = 0;
        currentPrdContent = '';
    } catch (error) {
        alert('Error: Failed to clear conversation');
    }
});

// Copy PRD to clipboard
copyBtn.addEventListener('click', async function() {
    if (!currentPrdContent) return;

    try {
        await navigator.clipboard.writeText(currentPrdContent);
        copyBtn.textContent = 'Copied!';
        copyBtn.classList.add('copied');

        setTimeout(() => {
            copyBtn.textContent = 'Copy to Clipboard';
            copyBtn.classList.remove('copied');
        }, 2000);
    } catch (error) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = currentPrdContent;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);

        copyBtn.textContent = 'Copied!';
        copyBtn.classList.add('copied');

        setTimeout(() => {
            copyBtn.textContent = 'Copy to Clipboard';
            copyBtn.classList.remove('copied');
        }, 2000);
    }
});

function addMessage(content, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Split content into paragraphs
    const paragraphs = content.split('\n\n');
    paragraphs.forEach(p => {
        if (p.trim()) {
            const para = document.createElement('p');
            para.textContent = p.trim();
            contentDiv.appendChild(para);
        }
    });

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showLoading(text) {
    loadingText.textContent = text;
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

// Load and display existing PRDs
async function loadExistingPrds() {
    try {
        const response = await fetch('/api/prds');
        const data = await response.json();

        if (data.prds && data.prds.length > 0) {
            displayPrds(data.prds);
            prdsCount.textContent = data.prds.length;
            noPrds.classList.add('hidden');
        } else {
            prdsList.innerHTML = '';
            prdsCount.textContent = '0';
            noPrds.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Failed to load existing PRDs:', error);
    }
}

function displayPrds(prds) {
    prdsList.innerHTML = '';
    selectedPrds.clear();
    updateBulkActionsVisibility();

    prds.forEach(prd => {
        // Create PRD group container
        const prdGroup = document.createElement('div');
        prdGroup.className = 'prd-group';

        // Create the PRD item
        const item = document.createElement('div');
        item.className = 'prd-item';
        item.dataset.filename = prd.filename;

        // Checkbox for multi-select
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'prd-checkbox';
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            if (checkbox.checked) {
                selectedPrds.add(prd.filename);
            } else {
                selectedPrds.delete(prd.filename);
            }
            updateBulkActionsVisibility();
        });
        checkbox.addEventListener('click', (e) => e.stopPropagation());

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'prd-item-content';

        const name = document.createElement('span');
        name.className = 'prd-name';
        name.textContent = prd.name;
        name.title = prd.name;

        const date = document.createElement('span');
        date.className = 'prd-date';
        date.textContent = prd.date;

        contentWrapper.appendChild(name);
        contentWrapper.appendChild(date);

        const archiveBtn = document.createElement('button');
        archiveBtn.className = 'prd-archive-btn';
        archiveBtn.innerHTML = '&times;';
        archiveBtn.title = 'Archive PRD and related research';
        archiveBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            showArchiveDropdown(prd.filename, prd.name, archiveBtn);
        });

        item.appendChild(checkbox);
        item.appendChild(contentWrapper);
        item.appendChild(archiveBtn);

        contentWrapper.addEventListener('click', () => {
            if (!multiSelectMode) {
                loadPrd(prd.filename);
            }
        });

        // In multi-select mode, clicking the item toggles the checkbox
        item.addEventListener('click', () => {
            if (multiSelectMode) {
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change'));
            }
        });

        prdGroup.appendChild(item);

        // Add research sub-items if any
        if (prd.research && prd.research.length > 0) {
            const researchList = document.createElement('div');
            researchList.className = 'prd-research-list';

            prd.research.forEach(research => {
                const researchItem = document.createElement('div');
                researchItem.className = 'prd-research-item';
                researchItem.dataset.filename = research.filename;

                // Checkbox for multi-select
                const researchCheckbox = document.createElement('input');
                researchCheckbox.type = 'checkbox';
                researchCheckbox.className = 'prd-checkbox';
                researchCheckbox.addEventListener('change', (e) => {
                    e.stopPropagation();
                    if (researchCheckbox.checked) {
                        selectedPrds.add(research.filename);
                    } else {
                        selectedPrds.delete(research.filename);
                    }
                    updateBulkActionsVisibility();
                });
                researchCheckbox.addEventListener('click', (e) => e.stopPropagation());

                const researchContent = document.createElement('div');
                researchContent.className = 'prd-item-content';

                const researchName = document.createElement('span');
                researchName.className = 'prd-name research-name';
                researchName.textContent = 'Competitive Analysis';
                researchName.title = research.name;

                const researchDate = document.createElement('span');
                researchDate.className = 'prd-date';
                researchDate.textContent = research.date;

                researchContent.appendChild(researchName);
                researchContent.appendChild(researchDate);

                const researchArchiveBtn = document.createElement('button');
                researchArchiveBtn.className = 'prd-archive-btn';
                researchArchiveBtn.innerHTML = '&times;';
                researchArchiveBtn.title = 'Archive this research';
                researchArchiveBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    showArchiveDropdown(research.filename, research.name, researchArchiveBtn);
                });

                researchItem.appendChild(researchCheckbox);
                researchItem.appendChild(researchContent);
                researchItem.appendChild(researchArchiveBtn);

                researchContent.addEventListener('click', () => {
                    if (!multiSelectMode) {
                        loadPrd(research.filename);
                    }
                });

                researchItem.addEventListener('click', () => {
                    if (multiSelectMode) {
                        researchCheckbox.checked = !researchCheckbox.checked;
                        researchCheckbox.dispatchEvent(new Event('change'));
                    }
                });

                researchList.appendChild(researchItem);
            });

            prdGroup.appendChild(researchList);
        }

        prdsList.appendChild(prdGroup);
    });
}

// Toggle multi-select mode
selectToggle.addEventListener('click', () => {
    multiSelectMode = !multiSelectMode;
    prdsList.classList.toggle('multi-select-mode', multiSelectMode);
    selectToggle.innerHTML = multiSelectMode ? '&#10003;' : '&#9998;';
    selectToggle.title = multiSelectMode ? 'Done selecting' : 'Select multiple';

    if (!multiSelectMode) {
        // Clear selections when exiting multi-select
        selectedPrds.clear();
        document.querySelectorAll('.prd-checkbox').forEach(cb => cb.checked = false);
    }
    updateBulkActionsVisibility();
});

// Archive selected PRDs
archiveSelectedBtn.addEventListener('click', async () => {
    if (selectedPrds.size === 0) return;

    const filenames = Array.from(selectedPrds);

    // Exit multi-select mode first
    multiSelectMode = false;
    prdsList.classList.remove('multi-select-mode');
    selectToggle.innerHTML = '&#9998;';
    selectToggle.title = 'Select multiple';
    selectedPrds.clear();
    updateBulkActionsVisibility();

    // Archive all selected (skip reload until the end)
    for (const filename of filenames) {
        await doArchivePrd(filename, true);
    }

    // Reload the list once at the end
    await loadExistingPrds();
});

function updateBulkActionsVisibility() {
    if (multiSelectMode) {
        bulkActions.classList.remove('hidden');
        const count = selectedPrds.size;
        archiveSelectedBtn.textContent = count > 0 ? `Archive Selected (${count})` : 'Archive Selected';
        archiveSelectedBtn.disabled = count === 0;
    } else {
        bulkActions.classList.add('hidden');
    }
}

function showArchiveDropdown(filename, name, buttonElement) {
    // Remove any existing dropdown
    const existing = document.querySelector('.archive-dropdown');
    if (existing) existing.remove();

    // Create dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'archive-dropdown';

    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'archive-confirm';
    confirmBtn.textContent = 'Archive';
    confirmBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        dropdown.remove();
        await doArchivePrd(filename);
    });

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'archive-cancel';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.remove();
    });

    dropdown.appendChild(confirmBtn);
    dropdown.appendChild(cancelBtn);

    // Position dropdown relative to button
    const rect = buttonElement.getBoundingClientRect();
    dropdown.style.position = 'fixed';
    dropdown.style.top = `${rect.bottom + 4}px`;
    dropdown.style.right = `${window.innerWidth - rect.right}px`;

    document.body.appendChild(dropdown);

    // Close dropdown when clicking outside
    const closeHandler = (e) => {
        if (!dropdown.contains(e.target) && e.target !== buttonElement) {
            dropdown.remove();
            document.removeEventListener('click', closeHandler);
        }
    };
    setTimeout(() => document.addEventListener('click', closeHandler), 0);
}

async function doArchivePrd(filename, skipReload = false) {
    try {
        const response = await fetch(`/api/prds/${encodeURIComponent(filename)}/archive`, {
            method: 'POST'
        });

        if (response.ok) {
            if (!skipReload) {
                await loadExistingPrds();
            }
        } else {
            const data = await response.json();
            console.error(data.error || 'Failed to archive PRD');
        }
    } catch (error) {
        console.error('Archive error:', error);
    }
}

async function loadPrd(filename) {
    if (!confirm('Load this PRD for iteration? This will replace your current conversation.')) {
        return;
    }

    showLoading('Loading PRD...');

    try {
        const response = await fetch(`/api/load-prd/${encodeURIComponent(filename)}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }

        // Update chat with the loaded PRD context
        chatMessages.innerHTML = `
            <div class="message user">
                <div class="message-content">
                    <p>I have an existing PRD that I'd like to iterate on and improve.</p>
                </div>
            </div>
            <div class="message assistant">
                <div class="message-content">
                    <p>I've reviewed your existing PRD. I can help you iterate on and improve it. What changes or additions would you like to make? For example:</p>
                    <p>- Add or modify features</p>
                    <p>- Clarify requirements</p>
                    <p>- Update technical considerations</p>
                    <p>- Refine user stories</p>
                    <p>- Add missing sections</p>
                    <p>Just let me know what you'd like to focus on!</p>
                </div>
            </div>
        `;

        messageCount = data.message_count;
        generateBtn.disabled = false;

        // Show the PRD in the preview
        currentPrdContent = data.content;
        prdContent.textContent = data.content;
        prdFilename.textContent = filename;
        prdPreview.classList.remove('hidden');

        messageInput.focus();
    } catch (error) {
        alert('Error: Failed to load PRD');
    } finally {
        hideLoading();
    }
}

