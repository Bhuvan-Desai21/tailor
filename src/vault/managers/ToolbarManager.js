/**
 * ToolbarManager - Manages toolbar buttons in the activity bar
 * 
 * Handles button registration and command execution.
 */
export class ToolbarManager {
    constructor() {
        this.buttons = new Map(); // id -> { icon, title, command }
        this._ensureToolbar();
    }

    _ensureToolbar() {
        // Create toolbar container if it doesn't exist
        if (!document.getElementById('plugin-toolbar')) {
            const activityBar = document.getElementById('activity-bar');
            if (activityBar) {
                const separator = document.createElement('div');
                separator.className = 'activity-separator';
                separator.style.cssText = 'height:1px; background:var(--border-color); margin:8px 4px;';

                const toolbar = document.createElement('div');
                toolbar.id = 'plugin-toolbar';
                toolbar.className = 'plugin-toolbar';

                activityBar.appendChild(separator);
                activityBar.appendChild(toolbar);
            }
        }
    }

    registerButton(id, icon, title, command) {
        console.log(`[ToolbarManager] Registering button: ${id}, command: ${command}`);

        if (this.buttons.has(id)) {
            console.log(`[ToolbarManager] Button ${id} already registered`);
            return;
        }

        this.buttons.set(id, { icon, title, command });
        this._ensureToolbar();

        const toolbar = document.getElementById('plugin-toolbar');
        if (toolbar) {
            const btn = document.createElement('div');
            btn.className = 'activity-action toolbar-btn';
            btn.title = title;
            btn.dataset.id = id;
            btn.dataset.command = command;
            btn.innerHTML = `<i data-lucide="${icon}"></i>`;

            btn.onclick = async () => {
                console.log(`[ToolbarManager] Executing command: ${command}`);
                try {
                    await window.request('execute_command', { command: command, args: {} });
                } catch (e) {
                    console.error(`[ToolbarManager] Command failed:`, e);
                }
            };

            toolbar.appendChild(btn);

            if (window.lucide) window.lucide.createIcons();
        }
    }
}
