/**
 * GoldenLayout Configuration & Initialization
 * 
 * Sets up the main editor layout with panels for stage, chat, log, and controls.
 */

import { GoldenLayout } from 'golden-layout';
import 'golden-layout/dist/css/goldenlayout-base.css';
import 'golden-layout/dist/css/themes/goldenlayout-dark-theme.css';

/**
 * Default layout configuration
 */
const config = {
    header: {
        popout: false
    },
    content: [{
        type: 'row',
        content: [
            {
                type: 'component',
                componentName: 'stage',
                title: 'Stage',
                width: 65
            },
            {
                type: 'column',
                width: 35,
                content: [
                    {
                        type: 'stack',
                        height: 40,
                        content: [
                            {
                                type: 'component',
                                componentName: 'chat',
                                title: 'LLM Chat'
                            },
                            {
                                type: 'component',
                                componentName: 'log',
                                title: 'System Log'
                            }
                        ]
                    },
                    {
                        type: 'component',
                        componentName: 'controls',
                        title: 'Inspector',
                        height: 20
                    }
                ]
            }
        ]
    }]
};

/**
 * Initialize GoldenLayout with component registrations
 */
export function initLayout() {
    const layoutRoot = document.getElementById('layout-root');
    const myLayout = new GoldenLayout(config, layoutRoot);

    // Component: Stage
    myLayout.registerComponent('stage', function (container, state) {
        container.element.innerHTML = `
            <div class="panel-container">
                <div class="scrollable" id="plugin-area">
                    <div style="color:var(--text-disabled); text-align:center; margin-top:50px;">
                        Stage Area
                    </div>
                </div>
            </div>
        `;
    });

    // Component: Chat
    myLayout.registerComponent('chat', function (container, state) {
        container.element.innerHTML = `
            <div class="panel-container">
                <div class="scrollable" id="chat-area">
                    <div style="color:var(--text-disabled); text-align:center; padding-top:20px;">
                        Waiting for LLM...
                    </div>
                </div>
            </div>
        `;
    });

    // Component: Log
    myLayout.registerComponent('log', function (container, state) {
        container.element.innerHTML = `
            <div class="panel-container">
                <div class="scrollable" id="log-output"></div>
                <div class="toolbar flex-between">
                    <span class="text-label" style="font-family:var(--font-main);">SYSTEM OUTPUT</span>
                    <button id="clearLog" class="icon-btn" title="Clear Log">Clear</button>
                </div>
            </div>
        `;

        // Bind Clear Log
        const clearBtn = container.element.querySelector('#clearLog');
        if (clearBtn) {
            clearBtn.onclick = () => {
                const out = document.getElementById('log-output');
                if (out) out.innerHTML = '';
            };
        }
    });

    // Component: Controls
    myLayout.registerComponent('controls', function (container, state) {
        container.element.innerHTML = `
            <div class="panel-container">
                <div class="scrollable">
                    <label class="text-label" style="display:block; margin-bottom:4px; font-weight:600;">COMMAND INPUT</label>
                    <textarea id="cmd-input" rows="3" placeholder="demo.hello"></textarea>
                    
                    <label class="text-label" style="display:block; margin:8px 0 4px 0; font-weight:600;">ARGUMENTS (JSON)</label>
                    <input id="arg-input" placeholder='{"name": "User"}'>
                    
                    <button id="execBtn" class="btn btn-primary" style="width:100%; margin-top:12px;">Execute Command</button>
                </div>
            </div>
        `;

        // Bind Execute
        const execBtn = container.element.querySelector('#execBtn');
        if (execBtn) {
            execBtn.onclick = async () => {
                const cmd = document.getElementById('cmd-input').value;
                let args = {};
                try {
                    args = JSON.parse(document.getElementById('arg-input').value || '{}');
                    if (typeof args !== 'object' || args === null || Array.isArray(args)) {
                        throw new Error("Arguments must be a JSON object");
                    }
                } catch (e) {
                    window.log(`Invalid JSON args: ${e.message}`, 'error');
                    return;
                }

                try {
                    const res = await window.request('execute_command', { command: cmd, args: args });
                    window.log(JSON.stringify(res.result, null, 2));
                } catch (e) {
                    window.log(`Exec failed: ${e}`, 'error');
                }
            };
        }
    });

    myLayout.init();
    window.myLayout = myLayout;

    // Handle window resize
    window.addEventListener('resize', () => {
        if (myLayout.isInitialised) myLayout.updateSize();
    });

    return myLayout;
}

/**
 * Initialize sidebar resize functionality
 */
export function initResize() {
    const panel = document.getElementById('side-panel');
    const handle = document.getElementById('side-panel-resize');
    const mainEditor = document.querySelector('.main-editor');

    if (!panel || !handle || !mainEditor) return;

    let isResizing = false;
    let startX = 0;
    let startWidth = 0;

    handle.addEventListener('mousedown', (e) => {
        if (!panel.classList.contains('open')) return;
        isResizing = true;
        startX = e.clientX;
        startWidth = panel.offsetWidth;
        handle.classList.add('resizing');
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';
        mainEditor.style.pointerEvents = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        const delta = e.clientX - startX;
        const newWidth = Math.max(150, Math.min(500, startWidth + delta));
        panel.style.width = newWidth + 'px';
        if (window.myLayout) window.myLayout.updateSize();
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            handle.classList.remove('resizing');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            mainEditor.style.pointerEvents = '';
            if (window.myLayout) window.myLayout.updateSize();
        }
    });
}

/**
 * Logging function
 */
export function log(msg, type = 'info') {
    const out = document.getElementById('log-output');
    if (!out) return;

    const div = document.createElement('div');
    div.className = `log-entry ${type}`;
    const time = new Date().toLocaleTimeString().split(' ')[0];
    div.innerHTML = `<span class="ts">${time}</span>${msg}`;
    out.appendChild(div);
    out.scrollTop = out.scrollHeight;
}
