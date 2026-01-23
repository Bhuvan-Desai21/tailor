/**
 * Chat Branches Plugin - Frontend Module
 * 
 * Handles branch UI rendering and event management independently from core chat.
 */
(function () {
    'use strict';

    console.log('[ChatBranches] Frontend module loading...');

    // State
    let lastMetadata = null;
    let isRendering = false;

    /**
     * Cache metadata when history is loaded
     */
    window.addEventListener('chat:historyLoaded', (e) => {
        const { result } = e.detail;
        if (result && result.branches) {
            // Transform metadata to include ID in the object for easier sorting/filtering
            const transformed = {};
            Object.entries(result.branches).forEach(([id, meta]) => {
                transformed[id] = { ...meta, id };
            });
            lastMetadata = transformed;
            console.log('[ChatBranches] Metadata cached:', Object.keys(lastMetadata).length, 'branches');
        }
    });

    /**
     * Inject UI after core chat has rendered
     */
    window.addEventListener('chat:rendered', (e) => {
        if (isRendering || !lastMetadata) return;

        const { history } = e.detail;
        console.log('[ChatBranches] History rendered, injecting branch UI...');

        try {
            isRendering = true;
            injectBranchUI(history, lastMetadata);
        } catch (err) {
            console.error('[ChatBranches] Injection error:', err);
        } finally {
            isRendering = false;
        }
    });

    /**
     * Inject branch dividers and tabs into the chat messages
     */
    function injectBranchUI(history, branchesMetadata) {
        const messagesEl = document.getElementById('chat-messages');
        if (!messagesEl) return;

        let lastBranchId = history[0]?.source_branch || null;

        history.forEach((msg, idx) => {
            const currentBranchId = msg.source_branch || null;

            // Detect branch transitions
            if (idx > 0 && currentBranchId !== lastBranchId) {
                const targetBranchId = currentBranchId || lastBranchId;
                const branchToRender = branchesMetadata[targetBranchId];

                if (branchToRender) {
                    const parentId = branchToRender.parent_branch;
                    const siblings = Object.values(branchesMetadata).filter(b =>
                        b.parent_branch === parentId
                    );

                    // SORTING FIX: Ensure we handle missing IDs or different structures safely
                    siblings.sort((a, b) => (a.id || '').localeCompare(b.id || ''));

                    if (siblings.length > 1 || currentBranchId) {
                        const msgEl = messagesEl.querySelector(`[data-message-index="${idx}"]`);
                        if (msgEl) {
                            const divider = createBranchTabsElement(siblings, currentBranchId);
                            messagesEl.insertBefore(divider, msgEl);
                        }
                    }
                }
            }
            lastBranchId = currentBranchId;
        });

        // Forward navigation at the end
        if (lastBranchId && branchesMetadata[lastBranchId]) {
            const children = Object.values(branchesMetadata).filter(b =>
                b.parent_branch === lastBranchId
            );

            if (children.length > 0) {
                children.sort((a, b) => (a.id || '').localeCompare(b.id || ''));
                const forwardTabs = createForwardTabsElement(children);
                messagesEl.appendChild(forwardTabs);
                messagesEl.scrollTop = messagesEl.scrollHeight;
            }
        }

        if (window.lucide) window.lucide.createIcons();
    }

    function createBranchTabsElement(siblings, activeBranchId) {
        const div = document.createElement('div');
        div.className = 'chat-message chat-message-system branch-divider';
        div.style.margin = '10px 0';
        div.style.padding = '5px 0';
        div.style.borderTop = '1px solid rgba(255,255,255,0.05)';

        const tabsHtml = siblings.map(b => {
            const isActive = b.id === activeBranchId;
            const name = b.display_name || (b.id ? b.id.substring(0, 8) : 'branch');
            const bg = isActive ? 'var(--color-accent, #3b82f6)' : 'rgba(255,255,255,0.05)';
            const color = isActive ? 'white' : 'var(--text-muted, #888)';

            return `
                <button 
                    class="branch-tab-btn"
                    data-branch-id="${b.id || ''}"
                    style="
                        background: ${bg};
                        color: ${color};
                        border: 1px solid ${isActive ? 'transparent' : 'rgba(255,255,255,0.1)'};
                        border-radius: 4px;
                        padding: 3px 10px;
                        margin-right: 6px;
                        font-size: 0.85em;
                        cursor: ${isActive ? 'default' : 'pointer'};
                        transition: opacity 0.2s;
                    "
                    ${isActive ? 'disabled' : ''}
                >
                    <i data-lucide="git-branch" style="width:14px; height:14px; vertical-align:middle; margin-right:4px;"></i>
                    ${escapeHtml(name)}
                </button>
            `;
        }).join('');

        div.innerHTML = `<div class="message-content" style="display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 4px;">${tabsHtml}</div>`;

        div.querySelectorAll('.branch-tab-btn').forEach(btn => {
            if (!btn.disabled && btn.dataset.branchId) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    window.dispatchEvent(new CustomEvent('chat:switchBranch', {
                        detail: { branchId: btn.dataset.branchId }
                    }));
                });
            }
        });

        return div;
    }

    function createForwardTabsElement(children) {
        const div = document.createElement('div');
        div.className = 'chat-message chat-message-system branch-divider';
        div.style.marginTop = '15px';

        const tabsHtml = children.map(b => {
            const name = b.display_name || (b.id ? b.id.substring(0, 8) : 'branch');
            return `
                <button 
                    class="branch-tab-btn"
                    data-branch-id="${b.id || ''}"
                    style="
                        background: rgba(255,255,255,0.05);
                        color: var(--text-muted, #888);
                        border: 1px solid rgba(255,255,255,0.1);
                        border-radius: 4px;
                        padding: 3px 10px;
                        margin-right: 6px;
                        font-size: 0.85em;
                        cursor: pointer;
                    "
                >
                    <i data-lucide="git-branch" style="width:14px; height:14px; vertical-align:middle; margin-right:4px;"></i>
                    ${escapeHtml(name)}
                </button>
            `;
        }).join('');

        div.innerHTML = `
            <div class="message-content" style="text-align: center;">
                <div style="font-size: 0.8em; opacity: 0.6; margin-bottom: 8px;">Explore other paths:</div>
                <div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 4px;">
                    ${tabsHtml}
                </div>
            </div>`;

        div.querySelectorAll('.branch-tab-btn').forEach(btn => {
            if (btn.dataset.branchId) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    window.dispatchEvent(new CustomEvent('chat:switchBranch', {
                        detail: { branchId: btn.dataset.branchId }
                    }));
                });
            }
        });

        return div;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Event Listeners for API calls
     */
    window.addEventListener('chat:createBranch', async (e) => {
        const { messageId } = e.detail;
        const activeChatId = window.chatModule?.activeChatId;

        if (!activeChatId) return;

        try {
            const res = await window.request('branch.create', {
                chat_id: activeChatId,
                message_id: messageId
            });
            const result = res.result || res;
            if (result.status === 'success') {
                window.chatModule.loadHistory(activeChatId);
            } else {
                alert('Branch creation failed: ' + result.error);
            }
        } catch (err) { console.error(err); }
    });

    window.addEventListener('chat:switchBranch', async (e) => {
        const { branchId } = e.detail;
        const activeChatId = window.chatModule?.activeChatId;

        if (!activeChatId) return;

        try {
            const res = await window.request('branch.switch', {
                chat_id: activeChatId,
                branch: branchId
            });
            const result = res.result || res;
            if (result.status === 'success') {
                window.chatModule.loadHistory(activeChatId);
            }
        } catch (err) { console.error(err); }
    });

    console.log('[ChatBranches] Registered. Ready to branch! 🚀');
})();
