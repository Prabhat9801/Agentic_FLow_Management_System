// FMS Frontend - Agentic Chatbot Application
const API_URL = window.location.origin;
const WS_URL = API_URL.replace('http', 'ws');

let websocket = null;
let isProcessing = false;

// DOM Elements
const chatArea = document.getElementById('chatArea');
const chatMessages = document.getElementById('chatMessages');
const promptInput = document.getElementById('promptInput');
const sendBtn = document.getElementById('sendBtn');
const sendText = document.getElementById('sendText');
const sendIcon = document.getElementById('sendIcon');
const logPanel = document.getElementById('logPanel');
const logContent = document.getElementById('logContent');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const welcomeCard = document.getElementById('welcomeCard');
const modal = document.getElementById('modal');
const modalTitle = document.getElementById('modalTitle');
const modalBody = document.getElementById('modalBody');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    autoResizeTextarea();
});

// WebSocket Connection
function connectWebSocket() {
    try {
        websocket = new WebSocket(`${WS_URL}/ws/logs`);
        
        websocket.onopen = () => {
            console.log('WebSocket connected');
            updateStatus('connected', 'Connected');
            
            // Keep alive
            setInterval(() => {
                if (websocket.readyState === WebSocket.OPEN) {
                    websocket.send('ping');
                }
            }, 30000);
        };
        
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateStatus('disconnected', 'Error');
        };
        
        websocket.onclose = () => {
            console.log('WebSocket disconnected');
            updateStatus('disconnected', 'Disconnected');
            
            // Reconnect after 3 seconds
            setTimeout(connectWebSocket, 3000);
        };
    } catch (error) {
        console.error('WebSocket connection failed:', error);
        updateStatus('disconnected', 'Failed');
    }
}

// Update connection status
function updateStatus(status, text) {
    statusDot.className = `status-dot ${status}`;
    statusText.textContent = text;
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'log':
            addLogEntry(data);
            break;
        case 'complete':
            addAgentMessage(data.message, data.result);
            setProcessing(false);
            break;
        case 'error':
            addAgentMessage(data.message, null, 'error');
            setProcessing(false);
            break;
        case 'pong':
            // Keep alive response
            break;
        default:
            console.log('Unknown message type:', data);
    }
}

// Add log entry
function addLogEntry(log) {
    // Remove empty message if exists
    const emptyMsg = logContent.querySelector('.log-empty');
    if (emptyMsg) emptyMsg.remove();
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${log.level.toLowerCase()}`;
    
    const timestamp = new Date(log.timestamp).toLocaleTimeString();
    
    entry.innerHTML = `
        <div class="log-timestamp">${timestamp}</div>
        <div class="log-stage">${log.stage}</div>
        <div class="log-message">${log.message}</div>
    `;
    
    logContent.appendChild(entry);
    logContent.scrollTop = logContent.scrollHeight;
}

// Clear logs
function clearLogs() {
    logContent.innerHTML = '<div class="log-empty">No logs yet.</div>';
}

// Create workflow
async function createWorkflow() {
    const prompt = promptInput.value.trim();
    
    if (!prompt || isProcessing) return;
    
    // Hide welcome card
    if (welcomeCard) {
        welcomeCard.style.display = 'none';
    }
    
    // Add user message
    addUserMessage(prompt);
    
    // Clear input
    promptInput.value = '';
    autoResizeTextarea();
    
    // Set processing state
    setProcessing(true);
    
    // Clear previous logs
    clearLogs();
    
    // Show logs panel
    if (logPanel.classList.contains('hidden')) {
        toggleLogs();
    }
    
    try {
        const response = await fetch(`${API_URL}/api/workflow/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: prompt,
                model: 'gpt-4o',
                temperature: 1.0
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message || 'Workflow creation failed');
        }
        
        // WebSocket will handle the completion message
        
    } catch (error) {
        console.error('Error creating workflow:', error);
        addAgentMessage(`❌ Error: ${error.message}`, null, 'error');
        setProcessing(false);
    }
}

// Add user message to chat
function addUserMessage(text) {
    const message = document.createElement('div');
    message.className = 'message user';
    message.innerHTML = `
        <div class="message-avatar">👤</div>
        <div class="message-content">${escapeHtml(text)}</div>
    `;
    chatMessages.appendChild(message);
    scrollToBottom();
}

// Add agent message to chat
function addAgentMessage(text, result = null, type = 'info') {
    const message = document.createElement('div');
    message.className = 'message agent';
    
    let resultHtml = '';
    if (result) {
        resultHtml = `
            <div class="message-result">
                <div class="result-item">
                    <span class="result-label">📊 System:</span>
                    <span class="result-value">${result.flow?.system_name || 'Created'}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">📋 Sheets:</span>
                    <span class="result-value">${result.sheets_count || 0}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">⚙️ Formulas:</span>
                    <span class="result-value">${result.formulas_count || 0}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">⏱️ Time:</span>
                    <span class="result-value">${result.execution_time?.toFixed(2) || 0}s</span>
                </div>
                ${result.spreadsheet_url ? `
                <div class="result-item">
                    <span class="result-label">🔗 Spreadsheet:</span>
                    <a href="${result.spreadsheet_url}" target="_blank" class="result-link">Open in Google Sheets →</a>
                </div>
                ` : ''}
            </div>
        `;
    }
    
    message.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            ${escapeHtml(text)}
            ${resultHtml}
        </div>
    `;
    
    chatMessages.appendChild(message);
    scrollToBottom();
}

// Set quick prompt
function setPrompt(text) {
    promptInput.value = text;
    autoResizeTextarea();
    promptInput.focus();
}

// Toggle logs panel
function toggleLogs() {
    logPanel.classList.toggle('hidden');
}

// Show projects
async function showProjects() {
    openModal('📁 Your Projects');
    modalBody.innerHTML = '<div class="loading">Loading projects...</div>';
    
    try {
        const response = await fetch(`${API_URL}/api/projects`);
        const data = await response.json();
        
        if (data.projects.length === 0) {
            modalBody.innerHTML = '<div class="log-empty">No projects yet. Create your first workflow!</div>';
            return;
        }
        
        modalBody.innerHTML = data.projects.map(project => {
            const meta = project.metadata;
            const created = new Date(meta.project_info?.created_at).toLocaleString();
            
            return `
                <div class="project-card" onclick="viewProject('${project.folder}')">
                    <div class="project-title">${meta.system?.name || 'Untitled'}</div>
                    <div class="project-meta">
                        📅 ${created} | 
                        📋 ${meta.system?.total_sheets || 0} sheets | 
                        📂 ${project.folder}
                    </div>
                    <div class="project-meta" style="margin-top: 0.5rem;">
                        ${meta.project_info?.prompt || ''}
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading projects:', error);
        modalBody.innerHTML = '<div class="log-empty">Error loading projects.</div>';
    }
}

// View project details
async function viewProject(projectId) {
    openModal('📊 Project Details');
    modalBody.innerHTML = '<div class="loading">Loading project details...</div>';
    
    try {
        const response = await fetch(`${API_URL}/api/projects/${projectId}`);
        const project = await response.json();
        
        const meta = project.metadata;
        
        modalBody.innerHTML = `
            <div style="line-height: 1.8;">
                <h3 style="color: var(--primary-light); margin-bottom: 1rem;">${meta.system?.name || 'Untitled'}</h3>
                
                <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
                    ${meta.system?.description || ''}
                </p>
                
                <div style="background: var(--bg-tertiary); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <div style="margin-bottom: 0.5rem;"><strong>📝 Prompt:</strong> ${meta.project_info?.prompt || ''}</div>
                    <div style="margin-bottom: 0.5rem;"><strong>📅 Created:</strong> ${new Date(meta.project_info?.created_at).toLocaleString()}</div>
                    <div style="margin-bottom: 0.5rem;"><strong>⏱️ Execution:</strong> ${meta.project_info?.execution_time_seconds}s</div>
                    <div style="margin-bottom: 0.5rem;"><strong>📋 Sheets:</strong> ${meta.system?.total_sheets || 0}</div>
                    <div>
                        <strong>🔗 Spreadsheet:</strong> 
                        <a href="${meta.spreadsheet?.url}" target="_blank" class="result-link">Open →</a>
                    </div>
                </div>
                
                ${meta.system?.workflow_stages ? `
                <div style="margin-bottom: 1rem;">
                    <strong>🔄 Workflow Stages:</strong>
                    <div style="margin-top: 0.5rem;">
                        ${meta.system.workflow_stages.map(stage => `
                            <span style="display: inline-block; background: var(--bg-tertiary); padding: 0.25rem 0.75rem; border-radius: 0.25rem; margin: 0.25rem;">${stage}</span>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                
                <div>
                    <strong>📚 Documentation:</strong>
                    <div style="margin-top: 0.5rem;">
                        <button class="btn-secondary" onclick="window.open('${API_URL}/projects/${projectId}/README.md', '_blank')" style="width: 100%;">
                            📄 View README
                        </button>
                    </div>
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading project:', error);
        modalBody.innerHTML = '<div class="log-empty">Error loading project details.</div>';
    }
}

// Modal controls
function openModal(title) {
    modalTitle.textContent = title;
    modal.classList.add('active');
}

function closeModal() {
    modal.classList.remove('active');
}

// Click outside modal to close
modal.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

// Processing state
function setProcessing(processing) {
    isProcessing = processing;
    sendBtn.disabled = processing;
    promptInput.disabled = processing;
    
    if (processing) {
        sendText.textContent = 'Creating...';
        sendIcon.textContent = '⏳';
    } else {
        sendText.textContent = 'Create';
        sendIcon.textContent = '🚀';
    }
}

// Auto-resize textarea
function autoResizeTextarea() {
    promptInput.style.height = 'auto';
    promptInput.style.height = Math.min(promptInput.scrollHeight, 150) + 'px';
}

promptInput.addEventListener('input', autoResizeTextarea);

// Handle Enter key
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        createWorkflow();
    }
}

// Scroll chat to bottom
function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export functions for inline onclick handlers
window.createWorkflow = createWorkflow;
window.setPrompt = setPrompt;
window.toggleLogs = toggleLogs;
window.showProjects = showProjects;
window.viewProject = viewProject;
window.closeModal = closeModal;
window.handleKeyPress = handleKeyPress;
