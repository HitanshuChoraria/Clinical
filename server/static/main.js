let currentTask = null;
let tasks = [];
let state = {
    step: 0,
    max_steps: 0,
    observation: null,
    done: false
};

async function init() {
    try {
        const res = await fetch('/tasks');
        const data = await res.json();
        tasks = data.tasks;
        renderTaskList();
        
        // Auto-select first task
        if (tasks.length > 0) {
            selectTask(tasks[0].name);
        }
        
        document.getElementById('env-status').innerText = 'Backend Connected';
    } catch (err) {
        console.error('Failed to fetch tasks:', err);
        document.getElementById('env-status').innerText = 'Connection Failed';
    }
}

function renderTaskList() {
    const list = document.getElementById('task-list');
    list.innerHTML = tasks.map(t => `
        <li class="task-item ${currentTask === t.name ? 'active' : ''}" onclick="selectTask('${t.name}')">
            <h4>${formatName(t.name)}</h4>
            <span class="badge">${t.difficulty}</span>
        </li>
    `).join('');
}

function formatName(name) {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

async function selectTask(name) {
    currentTask = name;
    renderTaskList();
    
    const taskInfo = tasks.find(t => t.name === name);
    document.getElementById('current-task-name').innerText = formatName(name);
    document.getElementById('task-difficulty').innerText = `Difficulty: ${taskInfo.difficulty}`;
    
    await resetTask();
}

async function resetTask() {
    state.step = 0;
    state.done = false;
    document.getElementById('results-panel').style.display = 'none';
    document.getElementById('feedback-log').innerText = '';
    
    try {
        const res = await fetch('/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task: currentTask })
        });
        const data = await res.json();
        state.observation = data.observation;
        state.max_steps = tasks.find(t => t.name === currentTask).max_steps;
        
        updateView();
    } catch (err) {
        console.error('Reset failed:', err);
    }
}

function updateView() {
    document.getElementById('task-step').innerText = `Step: ${state.step}/${state.max_steps}`;
    
    const obs = state.observation;
    // Cache data for tab switching
    window._obs = obs;
    
    switchTab('protocol');
}

function switchTab(tab) {
    const viewer = document.getElementById('data-viewer');
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    
    const obs = window._obs;
    if (!obs) return;

    let content = '';
    if (tab === 'protocol') {
        content = `<h3>Protocol Summary</h3><pre>${obs.protocol_summary || 'No summary available'}</pre>`;
        if (obs.protocol_text) {
            content += `<h3 style="margin-top:1.5rem">Protocol Text</h3><pre>${obs.protocol_text}</pre>`;
        }
    } else if (tab === 'records') {
        content = `<h3>Patient Records</h3><pre>${JSON.stringify(obs.patient_records || [], null, 2)}</pre>`;
    } else if (tab === 'events') {
        content = `<h3>Adverse Event Reports</h3><pre>${JSON.stringify(obs.adverse_events || [], null, 2)}</pre>`;
    }
    
    viewer.innerHTML = content;
}

// Tab click listeners
document.getElementById('tabs').addEventListener('click', (e) => {
    if (e.target.classList.contains('tab')) {
        switchTab(e.target.dataset.tab);
    }
});

async function submitStep() {
    if (state.done) return alert('Session complete. Reset to try again.');
    
    const findingsStr = document.getElementById('findings-input').value;
    const rationale = document.getElementById('rationale-input').value;
    
    let findings = [];
    try {
        findings = JSON.parse(findingsStr || '[]');
    } catch (e) {
        return alert('Findings must be a valid JSON array.');
    }

    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.innerText = 'Analyzing...';

    try {
        const res = await fetch('/step', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ findings, rationale })
        });
        const data = await res.json();
        
        state.step++;
        state.observation = data.observation;
        state.done = data.done;
        
        showResults(data);
        updateView();
    } catch (err) {
        console.error('Step failed:', err);
    } finally {
        btn.disabled = false;
        btn.innerText = 'Submit Findings';
    }
}

function showResults(data) {
    const panel = document.getElementById('results-panel');
    panel.style.display = 'block';
    
    const scorePct = Math.round(data.reward * 100);
    document.getElementById('score-value').innerText = scorePct;
    document.getElementById('reward-value').innerText = `+${data.reward.toFixed(2)}`;
    
    // Update progress circle
    const circle = document.getElementById('progress-circle');
    const radius = 45;
    const circumference = 2 * Math.PI * radius;
    circle.style.strokeDasharray = circumference;
    circle.style.strokeDashoffset = circumference - (scorePct / 100) * circumference;

    const log = document.getElementById('feedback-log');
    const entry = document.createElement('div');
    entry.style.marginBottom = '1rem';
    entry.innerHTML = `<strong style="color:var(--accent-cyan)">STEP ${state.step}:</strong><pre style="font-size:0.7rem; margin-top:0.3rem">${data.observation.feedback || 'No specific feedback'}</pre>`;
    log.prepend(entry);
}

document.addEventListener('DOMContentLoaded', init);
