const API_URL = '';

const state = {
    token: localStorage.getItem('fulcrum_token'),
    user: null,
    isRegister: false,
    hasLLM: false
};

// DOM Elements
const authView = document.getElementById('auth-view');
const dashboardView = document.getElementById('dashboard-view');
const authForm = document.getElementById('auth-form');
const authToggle = document.getElementById('auth-toggle');
const authTitle = document.getElementById('auth-title');
const authSubmit = document.getElementById('auth-submit');
const registerFields = document.getElementById('register-fields');
const logoutBtn = document.getElementById('logout-btn');

// Initial Load
if (state.token) {
    showDashboard();
}

// Auth Toggle
authToggle.addEventListener('click', (e) => {
    e.preventDefault();
    state.isRegister = !state.isRegister;
    authTitle.textContent = state.isRegister ? 'Create Account' : 'Welcome to Fulcrum';
    authSubmit.textContent = state.isRegister ? 'Sign Up' : 'Login';
    registerFields.classList.toggle('hidden');
    document.getElementById('auth-toggle-text').textContent = state.isRegister ?
        'Already have an account?' : "Don't have an account?";
    authToggle.textContent = state.isRegister ? 'Login' : 'Sign up';
});

// Auth Submit
authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    if (state.isRegister) {
        const full_name = document.getElementById('full_name').value;
        await register(email, password, full_name);
    } else {
        await login(email, password);
    }
});

async function login(email, password) {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            localStorage.setItem('fulcrum_token', data.access_token);
            state.token = data.access_token;
            showDashboard();
        } else {
            alert(data.detail || 'Login failed');
        }
    } catch (err) {
        console.error(err);
        alert('Server error connecting to login');
    }
}

async function register(email, password, full_name) {
    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, full_name })
        });
        const data = await res.json();

        if (res.ok) {
            localStorage.setItem('fulcrum_token', data.access_token);
            state.token = data.access_token;
            showDashboard();
        } else {
            alert(data.detail || 'Registration failed');
        }
    } catch (err) {
        console.error(err);
        alert('Server error connecting to register');
    }
}

function showDashboard() {
    authView.classList.add('hidden');
    dashboardView.classList.remove('hidden');
    loadOverview();
}

logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('fulcrum_token');
    location.reload();
});

// Navigation Logic
const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        const viewName = item.getAttribute('data-view');
        if (!viewName) return;

        e.preventDefault();

        // Update nav UI
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');

        // Switch containers
        views.forEach(view => view.classList.add('hidden'));
        const targetView = document.getElementById(`view-${viewName}`);
        if (targetView) targetView.classList.remove('hidden');

        // Load data if needed
        if (viewName === 'overview') loadOverview();
        if (viewName === 'projects') loadProjects();
        if (viewName === 'accounts') loadAccounts();
    });
});

async function loadOverview() {
    try {
        const res = await fetch(`${API_URL}/projects/overview`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const data = await res.json();

        if (res.ok) {
            document.getElementById('stat-projects').textContent = data.project_count || 0;
            document.getElementById('stat-llm').textContent = data.llm_status;
            state.hasLLM = data.llm_status !== "No LLM configured";
            renderProjects(data.projects, 'project-list');
        } else if (res.status === 401) {
            logoutBtn.click();
        }
    } catch (err) {
        console.error(err);
    }
}

async function loadProjects() {
    try {
        const res = await fetch(`${API_URL}/projects/`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const data = await res.json();
        if (res.ok) {
            renderProjects(data, 'full-project-list');
        }
    } catch (err) {
        console.error(err);
    }
}

function renderProjects(projects, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = projects.length ? '' : '<p class="subtitle">No projects registered yet.</p>';

    projects.forEach(p => {
        const card = document.createElement('div');
        card.className = 'glass-panel project-card';
        card.innerHTML = `
            <h3>${p.name}</h3>
            <p style="font-size: 0.875rem; color: var(--text-dim); margin-top: 8px;">${p.description || 'No description'}</p>
            <p style="font-size: 0.75rem; color: var(--accent); margin-top: 12px;">ID: ${p.id.substring(0, 8)}...</p>
        `;
        container.appendChild(card);
    });
}

// Project Modal Logic
const projectModal = document.getElementById('project-modal');
const projectForm = document.getElementById('project-form');

document.querySelectorAll('.open-project-modal').forEach(btn => {
    btn.addEventListener('click', () => {
        projectModal.classList.remove('hidden');
    });
});

if (projectForm) {
    projectForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const nameVal = document.getElementById('p-name').value;
        const descVal = document.getElementById('p-desc').value;
        const urlVal = document.getElementById('p-url').value;

        const projectData = {
            name: nameVal,
            description: descVal || null,
            source_type: 'local',
            remote_url: urlVal || null
        };

        try {
            const res = await fetch(`${API_URL}/projects/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify(projectData)
            });

            if (res.ok) {
                projectModal.classList.add('hidden');
                projectForm.reset();
                loadOverview();
                loadProjects();
            } else {
                const errData = await res.json();
                console.error('Project creation failed:', errData);
                alert('Error creating project: ' + (errData.detail || 'Internal error'));
            }
        } catch (err) {
            console.error('Fetch error:', err);
            alert('Server network error when creating project');
        }
    });
}

// Load and display AI accounts
async function loadAccounts() {
    try {
        const res = await fetch(`${API_URL}/accounts/`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const data = await res.json();

        if (res.ok) {
            renderAccounts(data);
        }
    } catch (err) {
        console.error(err);
    }
}

function renderAccounts(accounts) {
    const container = document.getElementById('accounts-list');
    if (!container) return;

    if (accounts.length === 0) {
        container.innerHTML = '<p class="subtitle">No AI accounts configured yet.</p>';
        return;
    }

    container.innerHTML = '';
    accounts.forEach(acc => {
        const card = document.createElement('div');
        card.className = 'glass-panel';
        card.style.padding = '16px';
        card.style.display = 'flex';
        card.style.justifyContent = 'space-between';
        card.style.alignItems = 'center';

        const providerBadge = acc.is_global ?
            '<span style="background: var(--accent); padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; margin-left: 8px;">Global</span>' :
            '<span style="background: rgba(99, 102, 241, 0.3); padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; margin-left: 8px;">Personal</span>';

        card.innerHTML = `
            <div>
                <h4 style="margin: 0; font-size: 1rem;">${acc.name || acc.provider.toUpperCase()}${providerBadge}</h4>
                <p style="font-size: 0.875rem; color: var(--text-dim); margin: 4px 0 0 0;">
                    ${acc.provider.toUpperCase()} • ${acc.api_endpoint || 'Default endpoint'} • Model: ${acc.model_name || 'default'}
                </p>
            </div>
            <div style="display: flex; gap: 8px;">
                <button class="btn-secondary" onclick="editAccountName('${acc.id}', '${(acc.name || '').replace(/'/g, \"&#39;\")}')" style="padding: 8px 16px;">
                    Edit name
                </button>
                <button class="btn-secondary" onclick="deleteAccount('${acc.id}')" style="padding: 8px 16px; background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.5); color: #ef4444;">
                    Delete
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

async function deleteAccount(accountId) {
    if (!confirm('Are you sure you want to delete this AI account?')) return;

    try {
        const res = await fetch(`${API_URL}/accounts/${accountId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${state.token}` }
        });

        if (res.ok) {
            loadAccounts();
            loadOverview(); // Refresh LLM status
        } else {
            const errData = await res.json();
            alert('Error deleting account: ' + (errData.detail || 'Unknown error'));
        }
    } catch (err) {
        console.error(err);
        alert('Server error deleting account');
    }
}

async function editAccountName(accountId, currentName) {
    const newName = prompt('New account name:', currentName || '');
    if (newName === null) return;

    try {
        const res = await fetch(`${API_URL}/accounts/${accountId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.token}`
            },
            body: JSON.stringify({ name: newName.trim() || null })
        });
        const data = await res.json();

        if (res.ok) {
            loadAccounts();
            loadOverview();
        } else {
            alert(data.detail || 'Failed to update account');
        }
    } catch (err) {
        console.error(err);
        alert('Server error updating account');
    }
}

// LLM Account Configuration
const llmForm = document.getElementById('llm-form');
if (llmForm) {
    llmForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const providerValue = document.getElementById('llm-provider').value;
        const nameValue = document.getElementById('llm-name').value.trim();
        const apiKeyValue = document.getElementById('llm-key').value.trim();
        const endpointInput = document.getElementById('llm-endpoint').value.trim();
        let endpointValue = endpointInput || "https://api.openai.com/v1";
        if (providerValue === 'ollama-local' && !endpointInput) {
            endpointValue = 'http://localhost:11434/v1';
        }
        const configData = {
            provider: providerValue,
            name: nameValue || null,
            api_key: apiKeyValue || null,  // Send null if empty (for Ollama self-hosted)
            api_endpoint: endpointValue,
            is_global: document.getElementById('llm-global').checked
        };

        try {
            const res = await fetch(`${API_URL}/accounts/llm`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify(configData)
            });
            const data = await res.json();

            if (res.ok) {
                alert('LLM Credentials saved successfully!');
                llmForm.reset();
                loadOverview();
                loadAccounts(); // Refresh accounts list
            } else {
                alert(data.detail || 'Failed to save credentials');
            }
        } catch (err) {
            console.error(err);
            alert('Server error saving LLM accounts');
        }
    });
}

// PM Settings Modal
const pmSettingsModal = document.getElementById('pm-settings-modal');
const pmSettingsForm = document.getElementById('pm-settings-form');
const openPMSettingsBtn = document.getElementById('open-pm-settings');
const pmAccountSelect = document.getElementById('pm-account');
const pmModelSelect = document.getElementById('pm-model');

if (openPMSettingsBtn) {
    openPMSettingsBtn.addEventListener('click', async () => {
        await loadPMSettings();
        pmSettingsModal.classList.remove('hidden');
    });
}

async function loadPMSettings() {
    try {
        const res = await fetch(`${API_URL}/accounts/`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const accounts = await res.json();

        if (res.ok) {
            pmAccountSelect.innerHTML = '<option value="">Select an account...</option>';
            accounts.forEach(acc => {
                const option = document.createElement('option');
                option.value = acc.id;
                option.textContent = `${acc.name || acc.provider.toUpperCase()} - ${acc.api_endpoint || 'default'}`;
                pmAccountSelect.appendChild(option);
            });

            // Load saved settings
            const savedAccount = localStorage.getItem('pm_account_id');
            const savedModel = localStorage.getItem('pm_model');
            if (savedAccount) {
                pmAccountSelect.value = savedAccount;
                await loadModelsForAccount(savedAccount);
                if (savedModel) pmModelSelect.value = savedModel;
            }
        }
    } catch (err) {
        console.error(err);
    }
}

pmAccountSelect.addEventListener('change', async (e) => {
    const accountId = e.target.value;
    if (accountId) {
        await loadModelsForAccount(accountId);
    } else {
        pmModelSelect.innerHTML = '<option value="">Select account first...</option>';
    }
});

async function loadModelsForAccount(accountId) {
    pmModelSelect.innerHTML = '<option value="">Loading models...</option>';
    pmModelSelect.disabled = true;

    try {
        const res = await fetch(`${API_URL}/chat/models/${accountId}`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const data = await res.json();

        if (res.ok) {
            pmModelSelect.innerHTML = '<option value="">Select a model...</option>';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                pmModelSelect.appendChild(option);
            });
            pmModelSelect.disabled = false;
        } else {
            pmModelSelect.innerHTML = '<option value="">Error loading models</option>';
            pmModelSelect.disabled = true;
            alert(`Could not load models: ${data.detail || 'Unknown error'}\n\nPlease verify your API endpoint and credentials are correct.`);
        }
    } catch (err) {
        console.error(err);
        pmModelSelect.innerHTML = '<option value="">Network error</option>';
        pmModelSelect.disabled = true;
        alert('Network error loading models. Please check your connection and try again.');
    }
}

if (pmSettingsForm) {
    pmSettingsForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const accountId = pmAccountSelect.value;
        const model = pmModelSelect.value;

        if (accountId && model) {
            localStorage.setItem('pm_account_id', accountId);
            localStorage.setItem('pm_model', model);
            pmSettingsModal.classList.add('hidden');
            alert('PM Settings saved!');
        }
    });
}

// Real Chat Logic
const chatInput = document.getElementById('chat-input');
const sendChatBtn = document.getElementById('send-chat');
const chatMessages = document.getElementById('chat-messages');

if (sendChatBtn) {
    sendChatBtn.addEventListener('click', async () => {
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';

        if (!state.hasLLM) {
            appendMessage('system', "I don't have an AI account configured yet. Please go to <b>AI Accounts</b> and add your credentials so I can process your requests!");
            return;
        }

        // Show typing indicator
        const typingId = appendMessage('system', '...');

        try {
            const res = await fetch(`${API_URL}/chat/pm`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify({ message: text })
            });

            const data = await res.json();

            // Remove typing indicator
            document.getElementById(typingId).remove();

            if (res.ok) {
                appendMessage('system', data.response);
            } else {
                appendMessage('system', `Error: ${data.detail || 'Failed to get response'}`);
            }
        } catch (err) {
            document.getElementById(typingId).remove();
            console.error(err);
            appendMessage('system', 'Network error. Please try again.');
        }
    });

    // Allow Enter key to send
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatBtn.click();
        }
    });
}

function appendMessage(sender, text) {
    const msgDiv = document.createElement('div');
    const msgId = 'msg-' + Date.now();
    msgDiv.id = msgId;
    msgDiv.className = `message ${sender}`;
    msgDiv.style.alignSelf = sender === 'user' ? 'flex-end' : 'flex-start';
    msgDiv.style.background = sender === 'user' ? 'var(--primary)' : 'rgba(255,255,255,0.05)';
    msgDiv.style.padding = '12px 18px';
    msgDiv.style.borderRadius = '16px';
    msgDiv.style.color = 'white';
    msgDiv.style.maxWidth = '80%';
    msgDiv.innerHTML = `<p>${text}</p>`;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgId;
}
