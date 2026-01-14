/**
 * Vault Settings Modal Module
 * 
 * Handles the settings button and modal for vault configuration.
 */

/**
 * Initialize the settings button
 */
export function initSettings() {
    // Initialize Lucide icon for settings button
    if (window.lucide) {
        window.lucide.createIcons();
    }

    const settingsBtn = document.getElementById('vault-settings-btn');
    if (!settingsBtn) return;

    settingsBtn.addEventListener('click', async () => {
        console.log('[Settings] Opening vault settings');

        // Get current vault path from URL params
        const params = new URLSearchParams(window.location.search);
        const vaultPath = params.get('vault') || params.get('path') || '';

        if (window.ui && window.ui.showModal) {
            const settingsHtml = `
                <div class="vault-settings-modal">
                    <div class="settings-nav-modal">
                        <div class="settings-nav-item-modal active" data-section="general">
                            <i data-lucide="settings"></i>
                            <span>General</span>
                        </div>
                        <div class="settings-nav-item-modal" data-section="plugins">
                            <i data-lucide="puzzle"></i>
                            <span>Plugins</span>
                        </div>
                        <div class="settings-nav-item-modal" data-section="ai">
                            <i data-lucide="brain"></i>
                            <span>AI Models</span>
                        </div>
                    </div>
                    <div id="settings-modal-content" style="padding: 20px;">
                        <h3>General Settings</h3>
                        <p style="color: var(--text-secondary); margin-bottom: 20px;">
                            Configure your vault settings here.
                        </p>
                        <div style="display: flex; flex-direction: column; gap: 12px;">
                            <div class="setting-item">
                                <strong>Vault Path:</strong>
                                <code style="background: var(--surface-color); padding: 4px 8px; border-radius: 4px;">${vaultPath}</code>
                            </div>
                            <button class="btn btn-secondary" onclick="window.request('system.client_ready', {}); window.ui.closeModal();">
                                <i data-lucide="refresh-cw"></i>
                                Reload
                            </button>
                        </div>
                    </div>
                </div>
            `;
            window.ui.showModal('Vault Settings', settingsHtml, '600px');

            // Reinitialize Lucide icons in modal
            setTimeout(() => {
                if (window.lucide) window.lucide.createIcons();
                setupSettingsNavigation();
            }, 50);
        } else {
            if (window.log) window.log('Settings modal not available', 'info');
            alert('Vault settings are being loaded...');
        }
    });
}

/**
 * Setup settings navigation between sections
 */
function setupSettingsNavigation() {
    const navItems = document.querySelectorAll('.settings-nav-item-modal');
    const contentEl = document.getElementById('settings-modal-content');

    if (!navItems.length || !contentEl) return;

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            const section = item.dataset.section;
            renderSettingsSection(contentEl, section);
        });
    });
}

/**
 * Render settings section content
 */
function renderSettingsSection(container, section) {
    const params = new URLSearchParams(window.location.search);
    const vaultPath = params.get('vault') || params.get('path') || '';

    switch (section) {
        case 'general':
            container.innerHTML = `
                <h3>General Settings</h3>
                <p style="color: var(--text-secondary); margin-bottom: 20px;">
                    Configure your vault settings here.
                </p>
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <div class="setting-item">
                        <strong>Vault Path:</strong>
                        <code style="background: var(--surface-color); padding: 4px 8px; border-radius: 4px;">${vaultPath}</code>
                    </div>
                    <button class="btn btn-secondary" onclick="window.request('system.client_ready', {}); window.ui.closeModal();">
                        <i data-lucide="refresh-cw"></i>
                        Reload
                    </button>
                </div>
            `;
            break;
        case 'plugins':
            container.innerHTML = `
                <h3>Plugins</h3>
                <p style="color: var(--text-secondary); margin-bottom: 20px;">
                    Manage your installed plugins. Click the Plugin Store button in the activity bar for the full plugin manager.
                </p>
                <button class="btn btn-primary" onclick="document.getElementById('plugin-store-btn').click(); window.ui.closeModal();">
                    <i data-lucide="package-plus"></i>
                    Open Plugin Manager
                </button>
            `;
            break;
        case 'ai':
            container.innerHTML = `
                <h3>AI Models</h3>
                <p style="color: var(--text-secondary); margin-bottom: 20px;">
                    Configure AI model settings in your .vault.json file.
                </p>
                <div class="setting-item" style="margin-bottom: 12px;">
                    <strong>API Configuration:</strong>
                    <p style="color: var(--text-secondary); font-size: 0.9rem;">
                        Set your OpenAI API key in the .env file or .vault.json to enable AI features.
                    </p>
                </div>
            `;
            break;
        default:
            container.innerHTML = '<p>Section not found.</p>';
    }

    if (window.lucide) window.lucide.createIcons();
}
