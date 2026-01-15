/**
 * StageManager - Manages the plugin content area
 */
export class StageManager {
    setContent(html) {
        console.log(`[StageManager] Setting stage content`);
        const stage = document.getElementById('plugin-area');
        if (stage) {
            stage.innerHTML = html;
            if (window.lucide) window.lucide.createIcons();
        }
    }
}
