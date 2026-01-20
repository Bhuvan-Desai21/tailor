/**
 * Plugin Loading & Event Handling Module
 * 
 * Handles loading plugins and processing UI commands from the backend.
 * Chat is now a core feature, not a plugin.
 */

import { request } from './connection.js';
import { initChat } from './chat/index.js';

const log = () => window.log || console.log;

/**
 * Load plugins and initialize core chat
 */
export async function loadPlugins(retryCount = 0) {
    const maxRetries = 3;
    const retryDelay = 500;
    const logFn = log();

    try {
        // Notify Backend Client is Ready
        logFn('Notifying backend: system.client_ready', 'out');
        await request('system.client_ready', {})
            .catch(e => console.warn('system.client_ready failed', e));

        // Wait for sidecar to finish initializing
        const initDelay = retryCount === 0 ? 1000 : 300;
        await new Promise(resolve => setTimeout(resolve, initDelay));

        // Initialize Core Chat (always available, not a plugin)
        const chatArea = document.getElementById('chat-area');
        if (chatArea) {
            logFn('Initializing core chat module', 'info');
            initChat(chatArea);
            logFn('Core chat initialized', 'in');
        } else {
            logFn('Chat area not found', 'error');
        }

        // List Commands for plugins
        const res = await request('list_commands');
        logFn(`list_commands response: ${JSON.stringify(res).slice(0, 200)}`, 'in');

        const commands = res.result?.commands || {};
        const commandList = Object.keys(commands);
        logFn(`Available commands: ${commandList.length}`, 'info');

        // Retry if no commands found
        if (commandList.length === 0 && retryCount < maxRetries) {
            logFn(`No commands found, retrying in ${retryDelay}ms... (attempt ${retryCount + 1}/${maxRetries})`, 'info');
            await new Promise(resolve => setTimeout(resolve, retryDelay));
            return loadPlugins(retryCount + 1);
        }

    } catch (e) {
        logFn(`Plugin Load Error: ${e}`, 'error');
        console.error('loadPlugins error:', e);

        if (retryCount < maxRetries) {
            logFn(`Retrying after error... (attempt ${retryCount + 1}/${maxRetries})`, 'info');
            await new Promise(resolve => setTimeout(resolve, retryDelay));
            return loadPlugins(retryCount + 1);
        }
    }
}

/**
 * Handle events from the backend
 */
export function handleEvent(evt) {
    const logFn = log();
    logFn(`Event: ${evt.event_type}`, 'in');

    // Dispatch to window (plugins can listen)
    const eventType = evt.event_type;
    const detail = evt.data || {};

    const customEvent = new CustomEvent(eventType, { detail });
    window.dispatchEvent(customEvent);

    // Handle UI Commands from Backend
    if (eventType === 'UI_COMMAND') {
        console.log('[handleEvent] UI_COMMAND received:', evt.data);
        const data = evt.data;

        switch (data.action) {
            // Sidebar
            case 'register_sidebar':
                console.log('[handleEvent] Registering sidebar:', data.id, data.icon, data.title);
                window.ui.registerSidebarView(data.id, data.icon, data.title);
                break;
            case 'set_sidebar':
                console.log('[handleEvent] Setting sidebar content:', data.id);
                window.ui.setSidebarContent(data.id, data.html);
                break;

            // Panels
            case 'register_panel':
                console.log('[handleEvent] Registering panel:', data.id, data.title);
                window.ui.registerPanel(data.id, data.title, data.icon, data.position);
                break;
            case 'set_panel':
                console.log('[handleEvent] Setting panel content:', data.id);
                window.ui.setPanelContent(data.id, data.html);
                break;
            case 'remove_panel':
                console.log('[handleEvent] Removing panel:', data.id);
                window.ui.removePanel(data.id);
                break;

            // Toolbar
            case 'register_toolbar':
                console.log('[handleEvent] Registering toolbar button:', data.id, data.command);
                window.ui.registerToolbarButton(data.id, data.icon, data.title, data.command);
                break;

            // Stage
            case 'set_stage':
                console.log('[handleEvent] Setting stage content');
                window.ui.setStageContent(data.html);
                break;

            // Modal
            case 'show_modal':
                console.log('[handleEvent] Showing modal:', data.title);
                window.ui.showModal(data.title, data.html, data.width);
                break;
            case 'close_modal':
                console.log('[handleEvent] Closing modal');
                window.ui.closeModal();
                break;

            // Message Action Toolbar
            case 'register_message_action':
                // Legacy - auto-set location
                console.log('[handleEvent] Registering message action (legacy):', data.id);
                if (window.ui.registerAction) {
                    window.ui.registerAction({
                        id: data.id,
                        icon: data.icon,
                        label: data.label,
                        position: data.position || 100,
                        type: data.type || 'button',
                        command: data.command,
                        location: 'message-actionbar'
                    });
                }
                break;

            // Action Toolbar (new API with location support)
            case 'register_action':
                console.log('[handleEvent] Registering action:', data.id, 'at', data.location);
                if (window.ui.registerAction) {
                    window.ui.registerAction({
                        id: data.id,
                        icon: data.icon,
                        label: data.label,
                        position: data.position || 100,
                        type: data.type || 'button',
                        command: data.command,
                        location: data.location || 'message-actionbar'
                    });
                }
                break;

            // Input field control
            case 'request_input':
                console.log('[handleEvent] Requesting input for:', data.callback_command);
                const inputEl = document.querySelector('#llm-input, #chat-input, .chat-input, .llm-input');
                const inputText = inputEl ? inputEl.value : '';
                if (data.callback_command && window.request) {
                    window.request(data.callback_command, { text: inputText });
                }
                break;
            case 'set_input':
                console.log('[handleEvent] Setting input text:', data.text);
                const targetInput = document.querySelector('#llm-input, #chat-input, .chat-input, .llm-input');
                if (targetInput) {
                    targetInput.value = data.text || '';
                    targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                    targetInput.focus();
                }
                break;

            default:
                console.warn('[handleEvent] Unknown UI action:', data.action);
        }
    }
}
