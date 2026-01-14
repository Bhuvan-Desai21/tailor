/**
 * ModalManager - Manages modal dialogs
 * 
 * Provides show/close functionality for plugin modals.
 */
export class ModalManager {
    constructor() {
        this.isOpen = false;
        this._ensureModal();
    }

    _ensureModal() {
        if (!document.getElementById('plugin-modal-overlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'plugin-modal-overlay';
            overlay.className = 'modal-overlay';
            overlay.style.cssText = `
                display: none;
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.6);
                z-index: 1000;
                justify-content: center;
                align-items: center;
            `;
            overlay.innerHTML = `
                <div id="plugin-modal" class="modal-dialog" style="
                    background: var(--surface-color);
                    border-radius: 8px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                    max-height: 80vh;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                ">
                    <div class="modal-header" style="
                        padding: 16px 20px;
                        border-bottom: 1px solid var(--border-color);
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <h3 id="modal-title" style="margin:0; font-size:1rem;"></h3>
                        <button id="modal-close-btn" class="icon-btn" style="
                            background: none; border: none; cursor: pointer;
                            color: var(--text-secondary); font-size: 1.2rem;
                        ">&times;</button>
                    </div>
                    <div id="modal-content" class="modal-body" style="
                        padding: 20px;
                        overflow-y: auto;
                        flex: 1;
                    "></div>
                </div>
            `;

            document.body.appendChild(overlay);

            // Close handlers
            overlay.onclick = (e) => {
                if (e.target === overlay) this.close();
            };
            document.getElementById('modal-close-btn').onclick = () => this.close();
        }
    }

    show(title, html, width = '500px') {
        console.log(`[ModalManager] Showing modal: ${title}`);
        this._ensureModal();

        const overlay = document.getElementById('plugin-modal-overlay');
        const modal = document.getElementById('plugin-modal');
        const titleEl = document.getElementById('modal-title');
        const contentEl = document.getElementById('modal-content');

        titleEl.textContent = title;
        contentEl.innerHTML = html;
        modal.style.width = width;
        overlay.style.display = 'flex';
        this.isOpen = true;

        if (window.lucide) window.lucide.createIcons();
    }

    close() {
        console.log(`[ModalManager] Closing modal`);
        const overlay = document.getElementById('plugin-modal-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
        this.isOpen = false;
    }
}
