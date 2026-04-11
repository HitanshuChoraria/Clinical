/**
 * Medical Monitor AI Dashboard - Core Logic
 */

let currentTask = null;
let allTasks = [];
let state = {
    step: 0,
    max_steps: 0,
    observation: null,
    done: false,
    activeTab: 'protocol'
};

/**
 * Initialization
 */
async function init() {
    updateStatus('Connecting to Neural Core...');
    
    try {
        const res = await fetch('/tasks');
        if (!res.ok) throw new Error('API Unavailable');
        
        const data = await res.json();
        allTasks = data;              // ← bare list now
        
        renderTaskList();
        
        if (allTasks.length > 0) {
            const lastTask = localStorage.getItem('last_task') || allTasks[0].name;
            await selectTask(lastTask);
        }
        
        updateStatus('Systems Operational', 'success');
    } catch (err) {
        console.error('Core init failure:', err);
        updateStatus('Connection Error', 'error');
        showNotification('Failed to initialize workspace', 'error');
    }
}

/**
 * UI State Management
 */
function updateStatus(text, type = 'standby') {
    const statusEl = document.getElementById('env-status');
    statusEl.innerText = text;
    // Note: CSS handles the pulse animation based on status logic if we add classes, 
    // for now we just update text.
}

function showNotification(msg, type = 'info') {
    const container = document.getElementById('notifications') || document.body;
    const note = document.createElement('div');
    note.className = `notification ${type}`;
    note.innerText = msg;
    container.appendChild(note);
    setTimeout(() => note.remove(), 4000);
}

/**
 * Task Management
 */
function renderTaskList() {
    const list = document.getElementById('task-list');
    list.innerHTML = allTasks.map(t => `
        <li class="task-item ${currentTask === t.name ? 'active' : ''}" onclick="selectTask('${t.name}')">
            <h4>${formatName(t.name)}</h4>
            <span class="badge">Security Level: ${t.difficulty}</span>
        </li>
    `).join('');
}

function formatName(name) {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

async function selectTask(name) {
    if (name === currentTask && state.observation) return;
    
    currentTask = name;
    localStorage.setItem('last_task', name);
    renderTaskList();
    
    const taskInfo = allTasks.find(t => t.name === name);
    document.getElementById('current-task-name').innerText = formatName(name);
    document.getElementById('breadcrumb-task').innerText = formatName(name);
    document.getElementById('task-difficulty').innerText = taskInfo.difficulty.toUpperCase();
    
    await resetTask();
}

async function resetTask() {
    state.step = 0;
    state.done = false;
    
    // UI Reset
    document.getElementById('results-panel').style.display = 'none';
    document.getElementById('feedback-log').innerHTML = '';
    document.getElementById('findings-input').value = '';
    document.getElementById('rationale-input').value = '';
    
    try {
        updateStatus('Reinitializing Environment...');
        const res = await fetch('/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task: currentTask })
        });
        
        const data = await res.json();
        state.observation = data.observation;
        state.max_steps = allTasks.find(t => t.name === currentTask).max_steps;
        
        updateUI();
        updateStatus('Systems Operational', 'success');
    } catch (err) {
        console.error('Reset failed:', err);
        showNotification('Environment reset failed', 'error');
    }
}

/**
 * View Rendering
 */
function updateUI() {
    document.getElementById('task-step').innerText = `${state.step} / ${state.max_steps}`;
    renderDataViewer();
}

function renderDataViewer() {
    const viewer = document.getElementById('data-viewer');
    const obs = state.observation;
    
    if (!obs) return;

    let content = '';
    const tab = state.activeTab;

    if (tab === 'protocol') {
        content = `
            <div class="protocol-view">
                <div class="section-label">Executive Summary</div>
                <div class="summary-text">${obs.protocol_summary || 'No summary version available.'}</div>
                ${obs.protocol_text ? `
                    <div class="section-label" style="margin-top:2rem">Detailed Protocol Specification</div>
                    <pre class="protocol-raw">${obs.protocol_text}</pre>
                ` : ''}
            </div>
        `;
    } else if (tab === 'records') {
        content = renderTable(obs.patient_records, 'Subject Clinical Records');
    } else if (tab === 'events') {
        content = renderTable(obs.adverse_events, 'Reported Adverse Events (AE)');
    }
    
    viewer.innerHTML = content;
}

function renderTable(data, title) {
    if (!data || data.length === 0) {
        return `<div class="placeholder-content">No data records found in this environment.</div>`;
    }

    const keys = Object.keys(data[0]);
    return `
        <div class="table-container">
            <div class="section-label">${title}</div>
            <table class="data-table">
                <thead>
                    <tr>${keys.map(k => `<th>${k.replace(/_/g, ' ').toUpperCase()}</th>`).join('')}</tr>
                </thead>
                <tbody>
                    ${data.map(row => `
                        <tr>${keys.map(k => {
                            let val = row[k];
                            if (typeof val === 'object') val = JSON.stringify(val);
                            return `<td>${val}</td>`;
                        }).join('')}</tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * Interactions
 */
document.getElementById('tabs').addEventListener('click', (e) => {
    const btn = e.target.closest('.tab-btn');
    if (!btn) return;
    
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    state.activeTab = btn.dataset.tab;
    renderDataViewer();
});

function insertFindingTemplate() {
    const template = [
        {
            "finding_type": "protocol_deviation",
            "subject_id": "PT-001",
            "severity": "major",
            "description": "Exceeding dosage limits specified in section 4.2",
            "recommendation": "Corrective training for site staff and safety monitoring"
        }
    ];
    
    const input = document.getElementById('findings-input');
    input.value = JSON.stringify(template, null, 4);
}

async function submitStep() {
    if (state.done) {
        showNotification('Iteration complete. Please reset environment.', 'warning');
        return;
    }
    
    const findingsStr = document.getElementById('findings-input').value;
    const rationale = document.getElementById('rationale-input').value;
    
    let findings = [];
    try {
        if (findingsStr.trim()) {
            findings = JSON.parse(findingsStr);
        }
    } catch (e) {
        showNotification('Invalid JSON syntax in findings', 'error');
        return;
    }

    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.querySelector('.btn-text').innerText = 'Processing Neural Grading...';

    try {
        const res = await fetch('/step', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ findings, rationale })
        });
        
        if (!res.ok) throw new Error('Inference failed');
        
        const data = await res.json();
        
        state.step++;
        state.observation = data.observation;
        state.done = data.done;
        
        showResults(data);
        updateUI();
    } catch (err) {
        console.error('Step failure:', err);
        showNotification('Submission error', 'error');
    } finally {
        btn.disabled = false;
        btn.querySelector('.btn-text').innerText = 'Execute Analysis';
    }
}

function showResults(data) {
    const panel = document.getElementById('results-panel');
    panel.style.display = 'block';
    
    const scorePct = Math.round((data.reward || 0) * 100);
    document.getElementById('score-value').innerText = scorePct;
    document.getElementById('reward-value').innerText = `${data.reward >= 0 ? '+' : ''}${data.reward.toFixed(2)}`;
    
    // Progress Circle
    const circle = document.getElementById('progress-circle');
    circle.style.strokeDasharray = `${scorePct}, 100`;

    const log = document.getElementById('feedback-log');
    const entry = document.createElement('div');
    entry.className = 'feedback-item animate-fade';
    entry.innerHTML = `
        <span class="step-badge">STEP ${state.step}</span>
        <div style="margin-top:0.5rem; color:var(--text-mid); line-height:1.4">
            ${data.observation.feedback || 'System verification complete. Internal consistency high.'}
        </div>
    `;
    log.prepend(entry);
    
    if (state.done) {
        showNotification('Workflow Iteration Finalized', 'success');
    }
}

// Start
document.addEventListener('DOMContentLoaded', init);
