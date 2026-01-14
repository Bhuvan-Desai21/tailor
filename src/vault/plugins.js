/**
 * Plugin Loading & Event Handling Module
 * 
 * Handles loading plugins and processing UI commands from the backend.
 */

import { request } from './connection.js';

const log = () => window.log || console.log;

/**
 * Load plugins with retry logic
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

        // List Commands
        const res = await request('list_commands');
        logFn(`list_commands response: ${JSON.stringify(res).slice(0, 200)}`, 'in');

        const commands = res.result?.commands || {};
        const commandList = Object.keys(commands);
        logFn(`Available commands: ${commandList.length}`, 'info');

        // Check for UI commands
        const hasLLM = commandList.includes('llm.get_ui');
        logFn(`Has llm.get_ui: ${hasLLM}`, 'info');

        // Retry if no commands found
        if (commandList.length === 0 && retryCount < maxRetries) {
            logFn(`No commands found, retrying in ${retryDelay}ms... (attempt ${retryCount + 1}/${maxRetries})`, 'info');
            await new Promise(resolve => setTimeout(resolve, retryDelay));
            return loadPlugins(retryCount + 1);
        }

        if (hasLLM) {
            logFn('Loading LLM UI...', 'out');
            const uiRes = await request('execute_command', {
                command: 'llm.get_ui',
                args: {}
            });

            logFn(`llm.get_ui response: ${JSON.stringify(uiRes).slice(0, 300)}`, 'in');

            // Handle various result structures
            let html = null;
            if (uiRes.result?.result?.html) {
                html = uiRes.result.result.html;
            } else if (uiRes.result?.html) {
                html = uiRes.result.html;
            } else if (uiRes.html) {
                html = uiRes.html;
            }

            if (html) {
                const stage = document.getElementById('chat-area');
                if (!stage) {
                    logFn('Chat pane not found', 'error');
                    return;
                }

                const range = document.createRange();
                range.selectNode(stage);
                const fragment = range.createContextualFragment(`<div class="panel-container" style="height:100%;">${html}</div>`);
                stage.innerHTML = '';
                stage.appendChild(fragment);

                if (window.lucide) window.lucide.createIcons();
                logFn('Loaded LLM UI into Chat Pane', 'in');
            } else {
                logFn('No HTML in llm.get_ui response', 'error');
            }
        } else if (!hasLLM && retryCount < maxRetries) {
            logFn(`LLM plugin not found, retrying... (attempt ${retryCount + 1}/${maxRetries})`, 'info');
            await new Promise(resolve => setTimeout(resolve, retryDelay));
            return loadPlugins(retryCount + 1);
        } else {
            // Show default chat UI
            const stage = document.getElementById('chat-area');
            if (stage) {
                stage.innerHTML = `
                    <div style="text-align:center; padding:40px; color:var(--text-disabled);">
                        <div style="font-size:2rem; margin-bottom:10px;">💬</div>
                        <p>LLM plugin not loaded</p>
                        <p style="font-size:0.8rem;">Enable the LLM plugin in .vault.json</p>
                    </div>
                `;
            }
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
