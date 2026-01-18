/**
 * Core Chat Module - Main Entry Point
 * 
 * Built-in chat interface that replaces the LLM plugin.
 * Uses LiteLLM backend for provider-agnostic LLM access.
 */

import { request } from '../connection.js';

// Chat state
let conversationHistory = [];
let isWaitingForResponse = false;
let currentCategory = 'fast';
let cssInjected = false;

/**
 * Inject chat CSS into the document
 */
function injectChatCSS() {
    if (cssInjected) return;

    const style = document.createElement('style');
    style.id = 'chat-module-styles';
    style.textContent = `
        /* Chat Container */
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 100%;
            background: var(--bg-app);
            overflow: hidden;
            font-family: var(--font-main, 'Inter', sans-serif);
        }

        /* Header */
        .chat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-subtle);
            background: var(--bg-card);
            flex-shrink: 0;
        }

        .chat-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            color: var(--text-primary);
            font-size: 14px;
        }

        .chat-title svg {
            width: 18px;
            height: 18px;
            color: var(--accent-primary);
        }

        .chat-actions { display: flex; gap: 4px; }
        .icon-btn {
            background: transparent;
            border: none;
            cursor: pointer;
            color: var(--text-secondary);
            padding: 4px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .icon-btn:hover {
            background: var(--bg-overlay, rgba(0,0,0,0.05));
            color: var(--text-primary);
        }

        /* Messages Area */
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            background: var(--bg-app);
        }

        /* Message Bubbles */
        .chat-message {
            display: flex;
            gap: 12px;
            max-width: 85%;
            animation: msgFadeIn 0.2s ease-out;
        }

        @keyframes msgFadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .chat-message-user { align-self: flex-end; flex-direction: row-reverse; }
        .chat-message-assistant { align-self: flex-start; }

        .chat-message-system {
            align-self: center;
            max-width: 90%;
        }

        .chat-message-system .message-content {
            background: transparent;
            color: var(--text-secondary);
            font-size: 13px;
            text-align: center;
            padding: 8px;
            border: none;
            box-shadow: none;
        }

        /* Avatar */
        .message-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

        .chat-message-user .message-avatar {
            background: var(--accent-primary);
            color: white;
        }

        .chat-message-assistant .message-avatar {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            color: var(--text-primary);
        }

        .message-avatar svg { width: 16px; height: 16px; }

        /* Message Content */
        .message-content {
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.5;
            word-wrap: break-word;
            font-size: 14px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .chat-message-user .message-content {
            background: var(--accent-primary);
            color: white;
            border-bottom-right-radius: 4px;
        }

        .chat-message-assistant .message-content {
            background: var(--bg-card);
            color: var(--text-primary);
            border: 1px solid var(--border-subtle);
            border-bottom-left-radius: 4px;
        }

        .message-error { color: #ef4444; }

        /* Loading Animation */
        .message-loading {
            display: flex;
            gap: 4px;
            padding: 4px 0;
        }

        .message-loading span {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--text-secondary);
            animation: loadingDot 1.4s infinite ease-in-out both;
        }

        .message-loading span:nth-child(1) { animation-delay: -0.32s; }
        .message-loading span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes loadingDot {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }

        /* Input Area */
        .chat-input-area {
            padding: 16px;
            border-top: 1px solid var(--border-subtle);
            background: var(--bg-card);
            flex-shrink: 0;
        }

        .chat-input-wrapper {
            display: flex;
            align-items: flex-end;
            gap: 8px;
            background: var(--bg-input, #fff);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 10px 14px;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .chat-input-wrapper:focus-within {
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 2px rgba(16, 163, 127, 0.1);
        }

        .chat-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 14px;
            line-height: 1.5;
            resize: none;
            min-height: 24px;
            max-height: 150px;
        }

        .chat-input::placeholder { color: var(--text-disabled); }

        .chat-send-btn {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: var(--accent-primary);
            color: white;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.2s;
        }

        .chat-send-btn:hover { background: var(--accent-hover, #0d8a6a); transform: scale(1.05); }
        .chat-send-btn:active { transform: scale(0.95); }
        .chat-send-btn svg { width: 16px; height: 16px; }

        /* Footer */
        .chat-footer {
            display: flex;
            justify-content: space-between;
            padding-top: 10px;
            font-size: 12px;
            color: var(--text-secondary);
        }

        .chat-model {
            padding: 2px 8px;
            background: var(--bg-overlay, rgba(0,0,0,0.05));
            border-radius: 4px;
            font-family: var(--font-mono, monospace);
            font-size: 11px;
            color: var(--text-secondary);
        }
    `;
    document.head.appendChild(style);
    cssInjected = true;
}

/**
 * Initialize the chat module
 */
export function initChat(containerEl) {
    if (!containerEl) {
        console.error('[Chat] Container element not provided');
        return;
    }

    // Inject CSS first
    injectChatCSS();

    // Render chat UI
    containerEl.innerHTML = getChatHTML();

    // Bind events
    bindEvents(containerEl);

    // Add welcome message
    addSystemMessage('Welcome! Type a message to start chatting.');

    // Initialize icons after a short delay
    setTimeout(() => {
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }, 50);

    console.log('[Chat] Core chat module initialized');
}

/**
 * Get the chat HTML template
 */
function getChatHTML() {
    return `
        <div class="chat-container">
            <div class="chat-header">
                <div class="chat-title">
                    <i data-lucide="message-square"></i>
                    <span>Chat</span>
                </div>
                <div class="chat-actions">
                    <button class="icon-btn" id="chat-clear" title="Clear Chat">
                        <i data-lucide="trash-2"></i>
                    </button>
                </div>
            </div>
            <div class="chat-messages" id="chat-messages">
                <!-- Messages will be inserted here -->
            </div>
            <div class="chat-input-area">
                <div class="chat-input-wrapper">
                    <textarea 
                        id="chat-input" 
                        class="chat-input" 
                        placeholder="Type your message..." 
                        rows="1"
                    ></textarea>
                    <button class="chat-send-btn" id="chat-send" title="Send Message">
                        <i data-lucide="send"></i>
                    </button>
                </div>
                <div class="chat-footer">
                    <span class="chat-status" id="chat-status">Ready</span>
                    <span class="chat-model" id="chat-model">fast</span>
                </div>
            </div>
        </div>
    `;
}

/**
 * Bind event listeners
 */
function bindEvents(container) {
    const input = container.querySelector('#chat-input');
    const sendBtn = container.querySelector('#chat-send');
    const clearBtn = container.querySelector('#chat-clear');

    // Send on button click
    sendBtn?.addEventListener('click', () => sendMessage());

    // Send on Enter (Shift+Enter for newline)
    input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    input?.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 150) + 'px';
    });

    // Clear chat
    clearBtn?.addEventListener('click', () => clearChat());

    // Initialize Lucide icons
    if (window.lucide) {
        setTimeout(() => window.lucide.createIcons(), 0);
    }
}

/**
 * Send a message
 */
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input?.value?.trim();

    if (!message || isWaitingForResponse) return;

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Add user message to UI
    addMessage('user', message);

    // Add to history
    conversationHistory.push({ role: 'user', content: message });

    // Show loading state
    setStatus('Thinking...');
    isWaitingForResponse = true;

    // Create assistant message placeholder
    const assistantMsgEl = addMessage('assistant', '', true);

    try {
        const res = await request('execute_command', {
            command: 'chat.send',
            args: {
                message: message,
                history: conversationHistory.slice(0, -1), // Exclude the just-added message
                category: currentCategory
            }
        });

        const result = res.result?.result || res.result || {};

        if (result.status === 'success') {
            const response = result.response || 'No response';

            // Update assistant message
            updateMessage(assistantMsgEl, response);

            // Add to history
            conversationHistory.push({ role: 'assistant', content: response });

            setStatus('Ready');
        } else {
            const error = result.error || 'Unknown error';
            updateMessage(assistantMsgEl, `Error: ${error}`, true);
            setStatus('Error');
        }
    } catch (e) {
        console.error('[Chat] Send error:', e);
        updateMessage(assistantMsgEl, `Error: ${e.message || e}`, true);
        setStatus('Error');
    } finally {
        isWaitingForResponse = false;
    }
}

/**
 * Add a message to the chat
 */
function addMessage(role, content, isLoading = false) {
    const messagesEl = document.getElementById('chat-messages');
    if (!messagesEl) return null;

    const msgEl = document.createElement('div');
    msgEl.className = `chat-message chat-message-${role}`;

    const iconName = role === 'user' ? 'user' : 'bot';

    msgEl.innerHTML = `
        <div class="message-avatar">
            <i data-lucide="${iconName}"></i>
        </div>
        <div class="message-content">
            ${isLoading ? '<div class="message-loading"><span></span><span></span><span></span></div>' : escapeHtml(content)}
        </div>
    `;

    messagesEl.appendChild(msgEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    // Render icons
    if (window.lucide) {
        setTimeout(() => window.lucide.createIcons(), 0);
    }

    return msgEl;
}

/**
 * Update an existing message element
 */
function updateMessage(msgEl, content, isError = false) {
    if (!msgEl) return;

    const contentEl = msgEl.querySelector('.message-content');
    if (contentEl) {
        contentEl.innerHTML = isError
            ? `<span class="message-error">${escapeHtml(content)}</span>`
            : escapeHtml(content);

        if (isError) {
            msgEl.classList.add('chat-message-error');
        }
    }

    // Scroll to bottom
    const messagesEl = document.getElementById('chat-messages');
    if (messagesEl) {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

/**
 * Add a system message
 */
function addSystemMessage(content) {
    const messagesEl = document.getElementById('chat-messages');
    if (!messagesEl) return;

    const msgEl = document.createElement('div');
    msgEl.className = 'chat-message chat-message-system';
    msgEl.innerHTML = `<div class="message-content">${escapeHtml(content)}</div>`;

    messagesEl.appendChild(msgEl);
}

/**
 * Clear the chat
 */
function clearChat() {
    conversationHistory = [];

    const messagesEl = document.getElementById('chat-messages');
    if (messagesEl) {
        messagesEl.innerHTML = '';
    }

    addSystemMessage('Chat cleared. Start a new conversation.');
    setStatus('Ready');
}

/**
 * Set the status text
 */
function setStatus(status) {
    const statusEl = document.getElementById('chat-status');
    if (statusEl) {
        statusEl.textContent = status;
    }
}

/**
 * Set the current model category
 */
export function setCategory(category) {
    currentCategory = category;
    const modelEl = document.getElementById('chat-model');
    if (modelEl) {
        modelEl.textContent = category;
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
}

/**
 * Get conversation history
 */
export function getHistory() {
    return conversationHistory;
}

/**
 * Export for global access
 */
export default {
    initChat,
    setCategory,
    getHistory,
    clearChat: () => clearChat()
};
