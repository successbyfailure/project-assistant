const API_URL = '';

const state = {
    token: localStorage.getItem('fulcrum_token'),
    user: null,
    isRegister: false,
    hasLLM: false,
    accounts: []
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
        if (viewName === 'integrations') {
            loadAccounts();
            loadGithubStatus();
            loadCoderAccounts();
        }
        if (viewName === 'workspaces') {
            populateCoderAccountSelect(workspacesCoderSelect).then(() => {
                autoLoadCoderWorkspaces(workspacesCoderSelect, workspacesCoderList);
            });
        }
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
        const workspaceLabel = p.workspace_name ? `Workspace: ${p.workspace_name}` : (p.workspace_id ? `Workspace: ${p.workspace_id}` : null);
        const workspacePath = p.workspace_path ? `Path: ${p.workspace_path}` : null;
        const workspaceInfo = [workspaceLabel, workspacePath].filter(Boolean).join(' • ');
        const thumb = p.thumbnail_url ? `<img class="project-thumb" src="${p.thumbnail_url}" alt="${p.name} thumbnail" onerror="this.style.display='none'">` : '';
        card.innerHTML = `
            ${thumb}
            <h3>${p.name}</h3>
            <p style="font-size: 0.875rem; color: var(--text-dim); margin-top: 8px;">${p.description || 'No description'}</p>
            ${workspaceInfo ? `<p style="font-size: 0.75rem; color: var(--text-dim); margin-top: 10px;">${workspaceInfo}</p>` : ''}
            <p style="font-size: 0.75rem; color: var(--accent); margin-top: 12px;">ID: ${p.id.substring(0, 8)}...</p>
        `;
        card.addEventListener('click', () => openProjectViewer(p));
        container.appendChild(card);
    });
}

// Project Modal Logic
const projectModal = document.getElementById('project-modal');
const projectForm = document.getElementById('project-form');
const projectViewerModal = document.getElementById('project-viewer-modal');
const projectViewerClose = document.getElementById('project-viewer-close');
const projectViewerTitle = document.getElementById('project-viewer-title');
const projectViewerDesc = document.getElementById('project-viewer-desc');
const projectViewerThumb = document.getElementById('project-viewer-thumb');
const projectSettingsForm = document.getElementById('project-settings-form');
const projectWorkspaceAccount = document.getElementById('project-workspace-account');
const projectWorkspaceSelect = document.getElementById('project-workspace-select');
const projectWorkspaceLoad = document.getElementById('project-workspace-load');
const projectWorkspaceStatus = document.getElementById('project-workspace-status');
const projectWorkspacePath = document.getElementById('project-workspace-path');
const projectBrowsePath = document.getElementById('project-browse-path');
const projectGitUrl = document.getElementById('project-git-url');
const projectProdUrl = document.getElementById('project-prod-url');
const projectTestUrl = document.getElementById('project-test-url');
const projectThumbnailUrl = document.getElementById('project-thumbnail-url');
const projectPathModal = document.getElementById('project-path-modal');
const projectPathClose = document.getElementById('project-path-close');
const projectPathUse = document.getElementById('project-path-use');
const projectPathList = document.getElementById('project-path-list');
const projectPathCurrent = document.getElementById('project-path-current');
const projectPathAlert = document.getElementById('project-path-alert');
const projectPathAlertText = document.getElementById('project-path-alert-text');
const projectPathOpenCoder = document.getElementById('project-path-open-coder');
let activeProjectId = null;
let activeProject = null;
let currentBrowsePath = '/';
let projectWorkspaceMap = new Map();
let coderAccountMap = new Map();

function normalizeWorkspacePath(rawPath) {
    if (!rawPath) return '';
    let path = rawPath.trim();
    if (path === '~' || path.startsWith('~/')) {
        path = `/home/coder${path.slice(1)}`;
    }
    if (!path.startsWith('/')) {
        path = `/${path}`;
    }
    if (path === '/') return '';
    return path;
}

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
        const workspaceVal = document.getElementById('p-workspace').value;
        const pathVal = document.getElementById('p-path').value;

        const projectData = {
            name: nameVal,
            description: descVal || null,
            source_type: 'local',
            remote_url: urlVal || null,
            workspace_id: workspaceVal || null,
            workspace_name: null,
            workspace_path: pathVal || null,
            production_url: null,
            testing_url: null,
            thumbnail_url: null
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

function openProjectViewer(project) {
    activeProjectId = project.id;
    activeProject = project;
    if (projectViewerTitle) projectViewerTitle.textContent = project.name || 'Project';
    if (projectViewerDesc) projectViewerDesc.textContent = project.description || 'No description yet.';
    if (projectWorkspacePath) projectWorkspacePath.value = project.workspace_path || '';
    if (projectGitUrl) projectGitUrl.value = project.remote_url || '';
    if (projectProdUrl) projectProdUrl.value = project.production_url || '';
    if (projectTestUrl) projectTestUrl.value = project.testing_url || '';
    if (projectThumbnailUrl) projectThumbnailUrl.value = project.thumbnail_url || '';
    if (projectViewerThumb) {
        if (project.thumbnail_url) {
            projectViewerThumb.src = project.thumbnail_url;
            projectViewerThumb.classList.remove('hidden');
        } else {
            projectViewerThumb.classList.add('hidden');
            projectViewerThumb.removeAttribute('src');
        }
    }
    if (projectViewerModal) projectViewerModal.classList.remove('hidden');

    if (projectWorkspaceAccount) {
        populateCoderAccountSelect(projectWorkspaceAccount).then(() => {
            if (!projectWorkspaceAccount.value && projectWorkspaceAccount.options.length > 1) {
                projectWorkspaceAccount.value = projectWorkspaceAccount.options[1].value;
            }
            if (projectWorkspaceSelect && project.workspace_id) {
                loadProjectWorkspaces().then(() => {
                    projectWorkspaceSelect.value = project.workspace_id || '';
                    updateProjectWorkspaceStatus();
                });
            }
        });
    }
}

if (projectViewerClose) {
    projectViewerClose.addEventListener('click', () => {
        projectViewerModal.classList.add('hidden');
    });
}

async function loadProjectWorkspaces() {
    if (!projectWorkspaceSelect || !projectWorkspaceAccount?.value) return;
    projectWorkspaceSelect.innerHTML = '<option value="">Loading...</option>';
    try {
        const res = await fetch(`${API_URL}/integrations/coder/workspaces?account_id=${encodeURIComponent(projectWorkspaceAccount.value)}`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const data = await res.json();
        if (res.ok && Array.isArray(data.workspaces)) {
            projectWorkspaceMap = new Map();
            projectWorkspaceSelect.innerHTML = '<option value="">Select a workspace...</option>';
            data.workspaces.forEach(ws => {
                const option = document.createElement('option');
                option.value = ws.id;
                option.textContent = ws.name || ws.id;
                if (ws.workspace_ref) {
                    option.dataset.workspaceRef = ws.workspace_ref;
                }
                projectWorkspaceSelect.appendChild(option);
                projectWorkspaceMap.set(ws.id, {
                    name: ws.name || ws.id,
                    ref: ws.workspace_ref || null,
                    status: ws.status || null
                });
            });
            updateProjectWorkspaceStatus();
        } else {
            projectWorkspaceSelect.innerHTML = '<option value="">No workspaces found</option>';
        }
    } catch (err) {
        console.error(err);
        projectWorkspaceSelect.innerHTML = '<option value="">Error loading workspaces</option>';
    }
}

if (projectWorkspaceLoad) {
    projectWorkspaceLoad.addEventListener('click', async () => {
        await loadProjectWorkspaces();
    });
}

if (projectWorkspaceAccount) {
    projectWorkspaceAccount.addEventListener('change', async () => {
        if (!projectWorkspaceAccount.value) return;
        await loadProjectWorkspaces();
        if (projectPathAlert) projectPathAlert.classList.add('hidden');
    });
}

if (projectWorkspaceSelect) {
    projectWorkspaceSelect.addEventListener('change', () => {
        updateProjectWorkspaceStatus();
        if (projectPathAlert) projectPathAlert.classList.add('hidden');
    });
}

function updateProjectWorkspaceStatus() {
    if (!projectWorkspaceStatus || !projectWorkspaceSelect) return;
    const meta = projectWorkspaceMap.get(projectWorkspaceSelect.value);
    if (meta && meta.status) {
        projectWorkspaceStatus.textContent = `Workspace status: ${meta.status}`;
    } else {
        projectWorkspaceStatus.textContent = '';
    }
}

if (projectSettingsForm) {
    projectSettingsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!activeProjectId) return;

        const selectedWorkspaceId = projectWorkspaceSelect?.value || null;
        const workspaceMeta = selectedWorkspaceId ? projectWorkspaceMap.get(selectedWorkspaceId) : null;
        const selectedWorkspaceName = workspaceMeta ? workspaceMeta.name : null;
        const payload = {
            workspace_id: selectedWorkspaceId,
            workspace_name: selectedWorkspaceName,
            workspace_path: projectWorkspacePath?.value || null,
            remote_url: projectGitUrl?.value || null,
            production_url: projectProdUrl?.value || null,
            testing_url: projectTestUrl?.value || null,
            thumbnail_url: projectThumbnailUrl?.value || null
        };

        try {
            const res = await fetch(`${API_URL}/projects/${activeProjectId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                activeProject = data;
                loadOverview();
                loadProjects();
                alert('Project settings saved.');
            } else {
                alert(data.detail || 'Failed to save project settings');
            }
        } catch (err) {
            console.error(err);
            alert('Server error saving project settings');
        }
    });
}

async function loadWorkspaceFolders(path) {
    if (!projectWorkspaceAccount?.value || !projectWorkspaceSelect?.value) return;
    if (!projectPathList) return;
    if (projectPathCurrent) {
        projectPathCurrent.textContent = `Loading ${path}...`;
    }
    const selectedOption = projectWorkspaceSelect.selectedOptions?.[0];
    const workspaceRef = selectedOption?.dataset?.workspaceRef
        || projectWorkspaceMap.get(projectWorkspaceSelect.value)?.ref
        || '';
    projectPathList.innerHTML = '<p class="subtitle">Loading folders...</p>';
    try {
        const params = new URLSearchParams({
            account_id: projectWorkspaceAccount.value,
            workspace_id: projectWorkspaceSelect.value,
            path
        });
        if (workspaceRef) {
            params.set('workspace_ref', workspaceRef);
        }
        const res = await fetch(`${API_URL}/integrations/coder/workspaces/files?${params.toString()}`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        let data = {};
        try {
            const raw = await res.text();
            data = raw ? JSON.parse(raw) : {};
        } catch (parseErr) {
            console.error('Invalid JSON response', parseErr);
            data = { detail: 'Invalid JSON response from server.' };
        }
        if (projectPathAlert) projectPathAlert.classList.add('hidden');
        if (res.ok && Array.isArray(data.folders)) {
            currentBrowsePath = data.path || path;
            if (projectPathCurrent) projectPathCurrent.textContent = currentBrowsePath;
            projectPathList.innerHTML = '';
            if (currentBrowsePath !== '/') {
                const upItem = document.createElement('div');
                upItem.className = 'folder-item';
                const upName = document.createElement('div');
                upName.className = 'folder-name';
                upName.textContent = '..';
                upItem.addEventListener('click', () => {
                    const parts = currentBrowsePath.split('/').filter(Boolean);
                    parts.pop();
                    const parent = '/' + parts.join('/');
                    loadWorkspaceFolders(parent || '/');
                });
                upItem.appendChild(upName);
                projectPathList.appendChild(upItem);
            }
            if (!data.folders.length) {
                projectPathList.innerHTML = '<p class="subtitle">No folders found.</p>';
                return;
            }
            data.folders.forEach(folder => {
                const row = document.createElement('div');
                row.className = 'folder-item';
                const name = document.createElement('div');
                name.className = 'folder-name';
                name.textContent = folder.name || folder.path || 'Folder';
                row.addEventListener('click', () => {
                    loadWorkspaceFolders(folder.path);
                });
                row.appendChild(name);
                projectPathList.appendChild(row);
            });
            return { ok: true, status: res.status, path: currentBrowsePath };
        } else {
            const detail = data.detail || `Failed to load folders (HTTP ${res.status})`;
            projectPathList.innerHTML = `<p class="subtitle">${detail}</p>`;
            if (res.status === 409 && projectPathAlert && projectPathAlertText) {
                projectPathAlertText.textContent = detail;
                projectPathAlert.classList.remove('hidden');
            }
            return { ok: false, status: res.status, path };
        }
    } catch (err) {
        console.error(err);
        projectPathList.innerHTML = '<p class="subtitle">Error loading folders</p>';
        return { ok: false, status: 0, path };
    }
}

if (projectBrowsePath) {
    projectBrowsePath.addEventListener('click', async () => {
        if (!projectWorkspaceAccount?.value || !projectWorkspaceSelect?.value) {
            alert('Select a Coder connection and workspace first.');
            return;
        }
        if (projectPathModal) projectPathModal.classList.remove('hidden');
        const savedPath = normalizeWorkspacePath(projectWorkspacePath?.value);
        if (savedPath) {
            await loadWorkspaceFolders(savedPath);
            return;
        }
        const preferredPaths = ['/home/coder/Projects', '/home/coder'];
        let loaded = false;
        for (const p of preferredPaths) {
            const result = await loadWorkspaceFolders(p);
            loaded = result.ok;
            if (loaded && result.path && result.path !== '/') break;
            if (result.status === 409) return;
        }
        if (!loaded) {
            await loadWorkspaceFolders('/');
        }
    });
}

if (projectPathClose) {
    projectPathClose.addEventListener('click', () => {
        projectPathModal.classList.add('hidden');
    });
}

if (projectPathOpenCoder) {
    projectPathOpenCoder.addEventListener('click', () => {
        const selectedOption = projectWorkspaceSelect?.selectedOptions?.[0];
        const workspaceRef = selectedOption?.dataset?.workspaceRef
            || projectWorkspaceMap.get(projectWorkspaceSelect?.value || '')?.ref
            || '';
        const accountMeta = coderAccountMap.get(projectWorkspaceAccount?.value || '');
        const base = accountMeta?.api_endpoint?.replace(/\/+$/, '') || '';
        if (!base) return;
        const target = workspaceRef ? `${base}/@${workspaceRef}` : base;
        window.open(target, '_blank');
    });
}

if (projectPathUse) {
    projectPathUse.addEventListener('click', () => {
        if (projectWorkspacePath) projectWorkspacePath.value = currentBrowsePath;
        projectPathModal.classList.add('hidden');
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
    state.accounts = accounts;

    if (accounts.length === 0) {
        container.innerHTML = '<p class="subtitle">No AI accounts configured yet.</p>';
        return;
    }

    container.innerHTML = '';
    accounts.forEach(acc => {
        const item = document.createElement('div');
        item.className = 'account-item';

        const meta = document.createElement('div');
        meta.className = 'account-meta';

        const title = document.createElement('div');
        title.className = 'account-title';
        const name = document.createElement('strong');
        name.textContent = acc.name || acc.provider.toUpperCase();
        title.appendChild(name);

        const badge = document.createElement('span');
        badge.className = `account-badge ${acc.is_global ? 'account-badge-global' : 'account-badge-personal'}`;
        badge.textContent = acc.is_global ? 'Global' : 'Personal';
        title.appendChild(badge);

        const details = document.createElement('span');
        details.className = 'subtitle';
        details.textContent = `${acc.provider.toUpperCase()} • ${acc.api_endpoint || 'Default endpoint'} • Model: ${acc.model_name || 'default'}`;

        meta.appendChild(title);
        meta.appendChild(details);

        const actions = document.createElement('div');
        actions.className = 'integration-actions';

        const editBtn = document.createElement('button');
        editBtn.className = 'btn-secondary btn-compact';
        editBtn.textContent = 'Edit name';
        editBtn.addEventListener('click', () => openAccountEditor(acc.id));

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn-danger btn-compact';
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', () => deleteAccount(acc.id));

        actions.appendChild(editBtn);
        actions.appendChild(deleteBtn);

        item.appendChild(meta);
        item.appendChild(actions);
        container.appendChild(item);
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

function findAccountById(accountId) {
    return (state.accounts || []).find(acc => acc.id === accountId);
}

const accountEditModal = document.getElementById('account-edit-modal');
const accountEditForm = document.getElementById('account-edit-form');
const accountEditName = document.getElementById('account-edit-name');
const accountEditEndpoint = document.getElementById('account-edit-endpoint');
const accountEditModels = document.getElementById('account-edit-models');
const accountEditDefault = document.getElementById('account-edit-model-default');
let editingAccountId = null;

function openAccountEditor(accountId) {
    const account = findAccountById(accountId);
    if (!account) return;

    editingAccountId = accountId;
    accountEditName.value = account.name || '';
    accountEditEndpoint.value = account.api_endpoint || '';
    accountEditModels.innerHTML = '<option value="">Loading models...</option>';
    accountEditModels.disabled = true;
    accountEditDefault.innerHTML = '<option value="">Loading models...</option>';
    accountEditDefault.disabled = true;
    accountEditModal.classList.remove('hidden');

    loadModelsForAccountId(accountId, account.model_name || null, account.enabled_models || []);
}

async function loadModelsForAccountId(accountId, selectedModel, enabledModels) {
    try {
        const res = await fetch(`${API_URL}/accounts/${accountId}/models`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const data = await res.json();

        if (res.ok && Array.isArray(data.models) && data.models.length) {
            accountEditModels.innerHTML = '';
            const allOption = document.createElement('option');
            allOption.value = '*';
            allOption.textContent = 'All models';
            if (!enabledModels || !enabledModels.length || enabledModels.includes('*')) {
                allOption.selected = true;
            }
            accountEditModels.appendChild(allOption);

            accountEditDefault.innerHTML = '';
            data.models.forEach((model, idx) => {
                const optEnabled = document.createElement('option');
                optEnabled.value = model;
                optEnabled.textContent = model;
                if (enabledModels && enabledModels.includes(model)) {
                    optEnabled.selected = true;
                }
                accountEditModels.appendChild(optEnabled);

                const optDefault = document.createElement('option');
                optDefault.value = model;
                optDefault.textContent = model;
                if (selectedModel && model === selectedModel) optDefault.selected = true;
                if (!selectedModel && idx === 0) optDefault.selected = true;
                accountEditDefault.appendChild(optDefault);
            });
            accountEditModels.disabled = false;
            accountEditDefault.disabled = false;
        } else {
            accountEditModels.innerHTML = '<option value="">No models found</option>';
            accountEditModels.disabled = true;
            accountEditDefault.innerHTML = '<option value="">No models found</option>';
            accountEditDefault.disabled = true;
        }
    } catch (err) {
        console.error(err);
        accountEditModels.innerHTML = '<option value="">Error loading models</option>';
        accountEditModels.disabled = true;
        accountEditDefault.innerHTML = '<option value="">Error loading models</option>';
        accountEditDefault.disabled = true;
    }
}

if (accountEditForm) {
    accountEditForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!editingAccountId) return;

        const enabledModels = Array.from(accountEditModels.selectedOptions).map(opt => opt.value).filter(Boolean);
        const enabledModelsPayload = enabledModels.includes('*') ? ['*'] : enabledModels;
        let defaultModel = accountEditDefault.value || null;
        if (enabledModelsPayload.length && enabledModelsPayload[0] !== '*' && defaultModel && !enabledModelsPayload.includes(defaultModel)) {
            defaultModel = enabledModelsPayload[0] || null;
        }
        const payload = {
            name: accountEditName.value.trim() || null,
            api_endpoint: accountEditEndpoint.value.trim() || null,
            enabled_models: enabledModelsPayload.length ? enabledModelsPayload : null,
            model_name: defaultModel
        };

        try {
            const res = await fetch(`${API_URL}/accounts/${editingAccountId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (res.ok) {
                accountEditModal.classList.add('hidden');
                editingAccountId = null;
                loadAccounts();
                loadOverview();
            } else {
                alert(data.detail || 'Failed to update account');
            }
        } catch (err) {
            console.error(err);
            alert('Server error updating account');
        }
    });
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
        const enabledModelsSelect = document.getElementById('llm-models');
        const defaultModelSelect = document.getElementById('llm-model-default');
        const enabledModels = enabledModelsSelect
            ? Array.from(enabledModelsSelect.selectedOptions).map(opt => opt.value).filter(Boolean)
            : [];
        const defaultModelValue = defaultModelSelect?.value || '';
        let endpointValue = endpointInput || "https://api.openai.com/v1";
        if (providerValue === 'ollama-local' && !endpointInput) {
            endpointValue = 'http://localhost:11434/v1';
        }
        // Normalize Ollama endpoints to include /v1
        if ((providerValue === 'ollama' || providerValue === 'ollama-local') && endpointValue) {
            const trimmed = endpointValue.replace(/\/+$/, '');
            endpointValue = trimmed.endsWith('/v1') ? trimmed : `${trimmed}/v1`;
        }
        const enabledModelsPayload = enabledModels.includes('*') ? ['*'] : enabledModels;
        let defaultModel = defaultModelValue || null;
        if (enabledModelsPayload.length && enabledModelsPayload[0] !== '*' && defaultModel && !enabledModelsPayload.includes(defaultModel)) {
            defaultModel = enabledModelsPayload[0] || null;
        }
        const configData = {
            provider: providerValue,
            name: nameValue || null,
            api_key: apiKeyValue || null,  // Send null if empty (for Ollama self-hosted)
            api_endpoint: endpointValue,
            enabled_models: enabledModelsPayload.length ? enabledModelsPayload : null,
            model_name: defaultModel,
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
                if (!localStorage.getItem('pm_account_id')) {
                    localStorage.setItem('pm_account_id', data.id);
                    if (data.model_name) {
                        localStorage.setItem('pm_model', data.model_name);
                    }
                }
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

async function loadLlmModels() {
    const providerValue = document.getElementById('llm-provider').value;
    const apiKeyValue = document.getElementById('llm-key').value.trim();
    const endpointInput = document.getElementById('llm-endpoint').value.trim();
    const enabledSelect = document.getElementById('llm-models');
    const defaultSelect = document.getElementById('llm-model-default');
    if (!enabledSelect || !defaultSelect) return;

    let endpointValue = endpointInput || "https://api.openai.com/v1";
    if (providerValue === 'ollama-local' && !endpointInput) {
        endpointValue = 'http://localhost:11434/v1';
    }
    if ((providerValue === 'ollama' || providerValue === 'ollama-local') && endpointValue) {
        const trimmed = endpointValue.replace(/\/+$/, '');
        endpointValue = trimmed.endsWith('/v1') ? trimmed : `${trimmed}/v1`;
    }

    enabledSelect.innerHTML = '<option value="">Loading models...</option>';
    enabledSelect.disabled = true;
    defaultSelect.innerHTML = '<option value="">Loading models...</option>';
    defaultSelect.disabled = true;

    try {
        const res = await fetch(`${API_URL}/accounts/llm/models`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.token}`
            },
            body: JSON.stringify({
                provider: providerValue,
                api_endpoint: endpointValue,
                api_key: apiKeyValue || null
            })
        });
        const data = await res.json();

        if (res.ok && Array.isArray(data.models) && data.models.length) {
            enabledSelect.innerHTML = '';
            const allOption = document.createElement('option');
            allOption.value = '*';
            allOption.textContent = 'All models';
            allOption.selected = true;
            enabledSelect.appendChild(allOption);

            defaultSelect.innerHTML = '';
            data.models.forEach((model, idx) => {
                const optEnabled = document.createElement('option');
                optEnabled.value = model;
                optEnabled.textContent = model;
                enabledSelect.appendChild(optEnabled);

                const optDefault = document.createElement('option');
                optDefault.value = model;
                optDefault.textContent = model;
                if (idx === 0) optDefault.selected = true;
                defaultSelect.appendChild(optDefault);
            });
            enabledSelect.disabled = false;
            defaultSelect.disabled = false;
        } else {
            enabledSelect.innerHTML = '<option value="">No models found</option>';
            enabledSelect.disabled = true;
            defaultSelect.innerHTML = '<option value="">No models found</option>';
            defaultSelect.disabled = true;
            if (data.detail) {
                alert(data.detail);
            }
        }
    } catch (err) {
        console.error(err);
        enabledSelect.innerHTML = '<option value="">Error loading models</option>';
        enabledSelect.disabled = true;
        defaultSelect.innerHTML = '<option value="">Error loading models</option>';
        defaultSelect.disabled = true;
    }
}

// Auto-load models when endpoint/provider changes
const llmProvider = document.getElementById('llm-provider');
const llmEndpoint = document.getElementById('llm-endpoint');
const llmKey = document.getElementById('llm-key');
if (llmProvider && llmEndpoint && llmKey) {
    const triggerLoad = () => {
        if (!state.token) return;
        loadLlmModels();
    };
    llmProvider.addEventListener('change', triggerLoad);
    llmEndpoint.addEventListener('change', triggerLoad);
    llmKey.addEventListener('change', triggerLoad);
}

// GitHub Integration
const githubConnectBtn = document.getElementById('github-connect');
const githubReposBtn = document.getElementById('github-load-repos');
const githubStatusText = document.getElementById('github-status-text');
const githubReposContainer = document.getElementById('github-repos');

// Coder Integration
const coderForm = document.getElementById('coder-form');
const coderNameInput = document.getElementById('coder-name');
const coderUrlInput = document.getElementById('coder-url');
const coderTokenInput = document.getElementById('coder-token');
const coderSessionToggle = document.getElementById('coder-session-token');
const coderOpenCliAuthBtn = document.getElementById('coder-open-cli-auth');
const coderAccountSelect = document.getElementById('coder-account-select');
const coderLoadWorkspacesBtn = document.getElementById('coder-load-workspaces');
const coderWorkspacesContainer = document.getElementById('coder-workspaces');
const coderDeleteConnectionBtn = document.getElementById('coder-delete-connection');
const coderOauthConnectBtn = document.getElementById('coder-oauth-connect');
const workspacesCoderSelect = document.getElementById('workspaces-coder-select');
const workspacesCoderLoadBtn = document.getElementById('workspaces-coder-load');
const workspacesCoderList = document.getElementById('workspaces-coder-list');

async function loadGithubStatus() {
    if (!githubStatusText) return;
    try {
        const res = await fetch(`${API_URL}/integrations/github/status`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const data = await res.json();
        if (res.ok && data.connected) {
            githubStatusText.textContent = `Connected as ${data.username || 'GitHub user'}.`;
            if (githubConnectBtn) githubConnectBtn.disabled = true;
            if (githubReposBtn) githubReposBtn.disabled = false;
        } else if (res.ok && data.configured === false) {
            githubStatusText.textContent = 'GitHub OAuth not configured.';
            if (githubConnectBtn) githubConnectBtn.disabled = true;
            if (githubReposBtn) githubReposBtn.disabled = true;
        } else {
            githubStatusText.textContent = 'Not connected.';
            if (githubConnectBtn) githubConnectBtn.disabled = false;
            if (githubReposBtn) githubReposBtn.disabled = false;
        }
    } catch (err) {
        console.error(err);
        githubStatusText.textContent = 'Status unavailable.';
    }
}

async function populateCoderAccountSelect(selectEl) {
    if (!selectEl) return;
    selectEl.innerHTML = '<option value="">Loading...</option>';
    try {
        const res = await fetch(`${API_URL}/integrations/coder/accounts`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const data = await res.json();
        if (res.ok && Array.isArray(data.accounts)) {
            selectEl.innerHTML = '<option value="">Select a connection...</option>';
            if (selectEl === coderAccountSelect || selectEl === projectWorkspaceAccount || selectEl === workspacesCoderSelect) {
                coderAccountMap = new Map();
            }
            data.accounts.forEach(acc => {
                const option = document.createElement('option');
                option.value = acc.id;
                option.textContent = `${acc.name || acc.api_endpoint}`;
                option.dataset.apiEndpoint = acc.api_endpoint || '';
                selectEl.appendChild(option);
                coderAccountMap.set(acc.id, { api_endpoint: acc.api_endpoint || '' });
            });
        } else {
            selectEl.innerHTML = '<option value="">No connections found</option>';
        }
    } catch (err) {
        console.error(err);
        selectEl.innerHTML = '<option value="">Error loading connections</option>';
    }
}

async function loadCoderAccounts() {
    if (!coderAccountSelect) return;
    await populateCoderAccountSelect(coderAccountSelect);
    await autoLoadCoderWorkspaces(coderAccountSelect, coderWorkspacesContainer);
}

async function autoLoadCoderWorkspaces(selectEl, container) {
    if (!selectEl || !container) return;
    const hasSelection = Boolean(selectEl.value);
    if (!hasSelection && selectEl.options.length > 1) {
        selectEl.selectedIndex = 1;
    }
    if (selectEl.value) {
        await loadCoderWorkspaces(selectEl.value, container);
    } else {
        container.innerHTML = '';
    }
}

function renderCoderWorkspaces(container, workspaces) {
    if (!container) return;
    container.innerHTML = '';
    if (!workspaces.length) {
        container.innerHTML = '<p class="subtitle">No workspaces found.</p>';
        return;
    }
    workspaces.forEach(ws => {
        const item = document.createElement('div');
        item.className = 'workspace-item';

        const meta = document.createElement('div');
        meta.className = 'workspace-meta';

        const name = document.createElement('strong');
        name.textContent = ws.name || 'Untitled workspace';
        meta.appendChild(name);

        const status = document.createElement('span');
        const statusValue = (ws.status || 'unknown').toLowerCase();
        status.className = `status-pill status-${statusValue}`;
        status.textContent = ws.status || 'Unknown';
        meta.appendChild(status);

        const actions = document.createElement('div');
        actions.className = 'integration-actions';

        const copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.className = 'btn-secondary btn-compact';
        copyBtn.textContent = 'Copy ID';
        copyBtn.addEventListener('click', async () => {
            if (!ws.id) return;
            try {
                await navigator.clipboard.writeText(ws.id);
                copyBtn.textContent = 'Copied';
                setTimeout(() => {
                    copyBtn.textContent = 'Copy ID';
                }, 1500);
            } catch (err) {
                console.error(err);
                alert('Copy failed. Please copy manually.');
            }
        });
        actions.appendChild(copyBtn);

        item.appendChild(meta);
        item.appendChild(actions);
        container.appendChild(item);
    });
}

async function loadCoderWorkspaces(accountId, container) {
    if (!container || !accountId) return;
    container.innerHTML = '<p class="subtitle">Loading workspaces...</p>';
    try {
        const res = await fetch(`${API_URL}/integrations/coder/workspaces?account_id=${encodeURIComponent(accountId)}`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        const data = await res.json();
        if (res.ok && Array.isArray(data.workspaces)) {
            renderCoderWorkspaces(container, data.workspaces);
        } else {
            container.innerHTML = `<p class="subtitle">${data.detail || 'Failed to load workspaces'}</p>`;
        }
    } catch (err) {
        console.error(err);
        container.innerHTML = '<p class="subtitle">Error loading workspaces</p>';
    }
}

if (coderForm) {
    coderForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!coderUrlInput.value.trim() || !coderTokenInput.value.trim()) return;
        try {
            const endpoint = coderSessionToggle?.checked
                ? `${API_URL}/integrations/coder/exchange`
                : `${API_URL}/integrations/coder/connect`;
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify({
                    name: coderNameInput.value.trim() || null,
                    url: coderUrlInput.value.trim(),
                    token: coderTokenInput.value.trim()
                })
            });
            const data = await res.json();
            if (res.ok) {
                alert('Coder connection saved');
                coderForm.reset();
                await loadCoderAccounts();
            } else {
                alert(data.detail || 'Failed to save Coder connection');
            }
        } catch (err) {
            console.error(err);
            alert('Server error saving Coder connection');
        }
    });
}

if (coderOpenCliAuthBtn) {
    coderOpenCliAuthBtn.addEventListener('click', () => {
        if (!coderUrlInput.value.trim()) {
            alert('Please enter a Coder URL first.');
            return;
        }
        const base = coderUrlInput.value.trim().replace(/\/+$/, '');
        window.open(`${base}/cli-auth`, '_blank');
    });
}

if (coderOauthConnectBtn) {
    coderOauthConnectBtn.addEventListener('click', async () => {
        try {
            const res = await fetch(`${API_URL}/integrations/coder/oauth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                }
            });
            const data = await res.json();
            if (res.ok && data.url) {
                window.location.href = data.url;
            } else {
                alert(data.detail || 'Failed to start Coder OAuth');
            }
        } catch (err) {
            console.error(err);
            alert('Server error starting Coder OAuth');
        }
    });
}

if (coderLoadWorkspacesBtn) {
    coderLoadWorkspacesBtn.addEventListener('click', async () => {
        if (!coderAccountSelect?.value) return;
        await loadCoderWorkspaces(coderAccountSelect.value, coderWorkspacesContainer);
    });
}

if (coderAccountSelect) {
    coderAccountSelect.addEventListener('change', async () => {
        await autoLoadCoderWorkspaces(coderAccountSelect, coderWorkspacesContainer);
    });
}

if (coderDeleteConnectionBtn) {
    coderDeleteConnectionBtn.addEventListener('click', async () => {
        if (!coderAccountSelect?.value) return;
        if (!confirm('Delete this Coder connection?')) return;
        try {
            const res = await fetch(`${API_URL}/integrations/coder/accounts/${encodeURIComponent(coderAccountSelect.value)}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${state.token}` }
            });
            const data = await res.json();
            if (res.ok) {
                await loadCoderAccounts();
                if (coderWorkspacesContainer) coderWorkspacesContainer.innerHTML = '';
                if (workspacesCoderSelect) {
                    await populateCoderAccountSelect(workspacesCoderSelect);
                    await autoLoadCoderWorkspaces(workspacesCoderSelect, workspacesCoderList);
                }
                alert('Coder connection deleted.');
            } else {
                alert(data.detail || 'Failed to delete Coder connection');
            }
        } catch (err) {
            console.error(err);
            alert('Server error deleting Coder connection');
        }
    });
}

if (workspacesCoderLoadBtn) {
    workspacesCoderLoadBtn.addEventListener('click', async () => {
        if (!workspacesCoderSelect?.value) return;
        await loadCoderWorkspaces(workspacesCoderSelect.value, workspacesCoderList);
    });
}

if (workspacesCoderSelect) {
    workspacesCoderSelect.addEventListener('change', async () => {
        await autoLoadCoderWorkspaces(workspacesCoderSelect, workspacesCoderList);
    });
}

if (githubConnectBtn) {
    githubConnectBtn.addEventListener('click', async () => {
        if (githubConnectBtn.disabled) return;
        try {
            const res = await fetch(`${API_URL}/integrations/github/login`, {
                headers: { 'Authorization': `Bearer ${state.token}` }
            });
            const data = await res.json();
            if (res.ok && data.url) {
                window.location.href = data.url;
            } else {
                alert(data.detail || 'Failed to start GitHub OAuth');
            }
        } catch (err) {
            console.error(err);
            alert('Server error starting GitHub OAuth');
        }
    });
}

if (githubReposBtn) {
    githubReposBtn.addEventListener('click', async () => {
        if (githubReposBtn.disabled) return;
        if (!githubReposContainer) return;
        githubReposContainer.innerHTML = '<p class="subtitle">Loading repositories...</p>';
        try {
            const res = await fetch(`${API_URL}/integrations/github/repos`, {
                headers: { 'Authorization': `Bearer ${state.token}` }
            });
            const data = await res.json();
            if (res.ok && Array.isArray(data.repos)) {
                githubReposContainer.innerHTML = '';
                if (!data.repos.length) {
                    githubReposContainer.innerHTML = '<p class="subtitle">No repositories found.</p>';
                }
                data.repos.forEach(repo => {
                    const item = document.createElement('div');
                    item.className = 'repo-item';

                    const meta = document.createElement('div');
                    meta.className = 'repo-meta';

                    const name = document.createElement('strong');
                    name.textContent = repo.full_name || 'Unnamed repo';
                    meta.appendChild(name);

                    if (repo.description) {
                        const desc = document.createElement('span');
                        desc.className = 'subtitle';
                        desc.textContent = repo.description;
                        meta.appendChild(desc);
                    }

                    item.appendChild(meta);
                    githubReposContainer.appendChild(item);
                });
            } else {
                githubReposContainer.innerHTML = `<p class="subtitle">${data.detail || 'Failed to load repos'}</p>`;
            }
        } catch (err) {
            console.error(err);
            githubReposContainer.innerHTML = '<p class="subtitle">Error loading repos</p>';
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
            state.accounts = accounts;
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
                const account = accounts.find(acc => acc.id === savedAccount);
                const defaultModel = savedModel || (account ? account.model_name : null);
                await loadModelsForAccount(savedAccount, defaultModel);
                if (defaultModel) pmModelSelect.value = defaultModel;
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

async function loadModelsForAccount(accountId, defaultModel) {
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
            if (defaultModel && data.models.includes(defaultModel)) {
                pmModelSelect.value = defaultModel;
            }
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
            appendMessage('system', "I don't have an AI account configured yet. Please go to <b>Integrations</b> and add your credentials so I can process your requests!");
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
                body: JSON.stringify({
                    message: text,
                    model_name: localStorage.getItem('pm_model') || null,
                    account_id: localStorage.getItem('pm_account_id') || null
                })
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
