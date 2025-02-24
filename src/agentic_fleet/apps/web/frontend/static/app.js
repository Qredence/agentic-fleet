/**
 * AgenticFleet Console Frontend Application
 * 
 * This module handles the frontend logic for the AgenticFleet console,
 * including WebSocket communication, UI updates, and agent configuration.
 */

// Application state
const state = {
    ws: null,
    sessionId: null,
    selectedAgent: null,
    agents: {},
    connected: false
};

// UI elements
const elements = {
    messagesContainer: document.getElementById('messages'),
    inputField: document.getElementById('input'),
    agentSelector: document.getElementById('agent'),
    configPanel: document.getElementById('agent-config'),
    statusIndicator: document.getElementById('connection-status')
};

/**
 * Initialize the application
 */
async function initialize() {
    state.sessionId = generateSessionId();
    await loadAgents();
    initializeWebSocket();
    setupEventListeners();
}

/**
 * Generate a unique session ID
 */
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

/**
 * Load available agents and their configurations
 */
async function loadAgents() {
    try {
        const response = await fetch('/api/chat/agents');
        const data = await response.json();
        
        state.agents = data.agents.reduce((acc, agent) => {
            acc[agent.name] = agent;
            return acc;
        }, {});
        
        updateAgentSelector();
        updateConfigPanel();
    } catch (error) {
        console.error('Error loading agents:', error);
        addSystemMessage('Error loading agent configurations');
    }
}

/**
 * Update agent selector dropdown
 */
function updateAgentSelector() {
    elements.agentSelector.innerHTML = Object.values(state.agents)
        .map(agent => `
            <option value="${agent.name}">
                ${agent.name} - ${agent.description}
            </option>
        `)
        .join('');
    
    elements.agentSelector.addEventListener('change', (event) => {
        state.selectedAgent = event.target.value;
        updateConfigPanel();
    });
}

/**
 * Update agent configuration panel
 */
function updateConfigPanel() {
    const agent = state.agents[state.selectedAgent || elements.agentSelector.value];
    if (!agent) return;
    
    elements.configPanel.innerHTML = `
        <h3>${agent.name} Configuration</h3>
        <div class="capabilities">
            <h4>Capabilities:</h4>
            <ul>
                ${agent.capabilities.map(cap => `<li>${cap}</li>`).join('')}
            </ul>
        </div>
        <div class="parameters">
            <h4>Parameters:</h4>
            <form id="config-form">
                ${Object.entries(agent.parameters).map(([key, value]) => `
                    <div class="form-group">
                        <label for="${key}">${key}:</label>
                        <input type="text" id="${key}" name="${key}" 
                               value="${value}" class="config-input">
                    </div>
                `).join('')}
                <button type="submit" class="config-save">Save Configuration</button>
            </form>
        </div>
    `;
    
    document.getElementById('config-form').addEventListener('submit', updateAgentConfig);
}

/**
 * Update agent configuration
 */
async function updateAgentConfig(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const parameters = {};
    
    for (let [key, value] of formData.entries()) {
        parameters[key] = value;
    }
    
    try {
        const response = await fetch(
            `/api/chat/agents/${state.selectedAgent}/config`,
            {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ parameters })
            }
        );
        
        if (response.ok) {
            addSystemMessage('Agent configuration updated successfully');
            await loadAgents();
        } else {
            throw new Error('Failed to update configuration');
        }
    } catch (error) {
        console.error('Error updating configuration:', error);
        addSystemMessage('Error updating agent configuration');
    }
}

/**
 * Initialize WebSocket connection
 */
function initializeWebSocket() {
    state.ws = new WebSocket(`ws://${window.location.host}/api/chat`);
    
    state.ws.onopen = () => {
        state.connected = true;
        updateConnectionStatus();
        addSystemMessage('Connected to AgenticFleet');
    };
    
    state.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        addMessage(message.content, message.sender);
        saveChatHistory(message);
    };
    
    state.ws.onclose = () => {
        state.connected = false;
        updateConnectionStatus();
        addSystemMessage('Disconnected from AgenticFleet. Reconnecting...');
        setTimeout(initializeWebSocket, 1000);
    };
    
    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        addSystemMessage('Error connecting to AgenticFleet');
    };
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus() {
    elements.statusIndicator.className = state.connected ? 'connected' : 'disconnected';
    elements.statusIndicator.textContent = state.connected ? 'Connected' : 'Disconnected';
}

/**
 * Send a message to the server
 */
function sendMessage() {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        addSystemMessage('Not connected to server');
        return;
    }
    
    const content = elements.inputField.value.trim();
    if (!content) return;
    
    const message = {
        content: content,
        agent: elements.agentSelector.value,
        timestamp: Date.now(),
        metadata: {
            session_id: state.sessionId,
            agent_name: elements.agentSelector.value
        }
    };
    
    state.ws.send(JSON.stringify(message));
    addMessage(content, 'user');
    saveChatHistory({
        content: content,
        sender: 'user',
        timestamp: Date.now(),
        metadata: message.metadata
    });
    
    elements.inputField.value = '';
}

/**
 * Save message to chat history
 */
async function saveChatHistory(message) {
    try {
        await fetch(`/api/chat/history/${state.sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(message)
        });
    } catch (error) {
        console.error('Error saving chat history:', error);
    }
}

/**
 * Add a message to the chat container
 */
function addMessage(content, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender === 'user' ? 'user-message' : 'system-message'}`;
    
    const timestamp = new Date().toLocaleTimeString();
    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="sender">${sender}</span>
            <span class="timestamp">${timestamp}</span>
        </div>
        <div class="message-content">${content}</div>
    `;
    
    elements.messagesContainer.appendChild(messageDiv);
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

/**
 * Add a system message to the chat
 */
function addSystemMessage(content) {
    addMessage(content, 'system');
}

/**
 * Handle Enter key press in input field
 */
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    elements.inputField.addEventListener('keypress', handleKeyPress);
    document.getElementById('clear-history').addEventListener('click', clearChatHistory);
}

/**
 * Clear chat history
 */
async function clearChatHistory() {
    try {
        await fetch(`/api/chat/history/${state.sessionId}`, {
            method: 'DELETE'
        });
        elements.messagesContainer.innerHTML = '';
        addSystemMessage('Chat history cleared');
    } catch (error) {
        console.error('Error clearing chat history:', error);
        addSystemMessage('Error clearing chat history');
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', initialize);
