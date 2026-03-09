/**
 * Markdown Rendering Module
 * 
 * Renders markdown to sanitized HTML with syntax highlighting.
 * Uses: marked (parsing), DOMPurify (XSS), highlight.js (code).
 */

import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';

// Configure marked with highlight.js integration
marked.setOptions({
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(code, { language: lang }).value;
            } catch (e) { /* fall through */ }
        }
        try {
            return hljs.highlightAuto(code).value;
        } catch (e) { /* fall through */ }
        return code;
    },
    breaks: true,
    gfm: true
});

/**
 * Render markdown string to sanitized HTML.
 * @param {string} raw - Raw markdown text
 * @returns {string} Sanitized HTML string
 */
export function renderMarkdown(raw) {
    if (!raw) return '';
    const html = marked.parse(raw);
    return DOMPurify.sanitize(html, {
        ADD_TAGS: ['code', 'pre', 'span'],
        ADD_ATTR: ['class']
    });
}

/**
 * Post-process a container to add copy buttons to code blocks.
 * Call after inserting rendered HTML into DOM.
 * @param {HTMLElement} container
 */
export function addCodeCopyButtons(container) {
    if (!container) return;
    container.querySelectorAll('pre code').forEach(block => {
        // Skip if already has copy button
        if (block.parentElement.querySelector('.code-copy-btn')) return;

        // Detect language for label
        const langMatch = block.className.match(/language-(\w+)/);
        const lang = langMatch ? langMatch[1] : '';

        // Create header bar with language label + copy button
        const header = document.createElement('div');
        header.className = 'code-block-header';

        if (lang) {
            const langLabel = document.createElement('span');
            langLabel.className = 'code-lang-label';
            langLabel.textContent = lang;
            header.appendChild(langLabel);
        }

        const btn = document.createElement('button');
        btn.className = 'code-copy-btn';
        btn.title = 'Copy code';
        btn.innerHTML = '<i data-lucide="copy"></i> Copy';
        btn.addEventListener('click', () => {
            navigator.clipboard.writeText(block.textContent).then(() => {
                btn.innerHTML = '<i data-lucide="check"></i> Copied!';
                if (window.lucide) window.lucide.createIcons({ nodes: [btn] });
                setTimeout(() => {
                    btn.innerHTML = '<i data-lucide="copy"></i> Copy';
                    if (window.lucide) window.lucide.createIcons({ nodes: [btn] });
                }, 2000);
            });
        });
        header.appendChild(btn);

        const pre = block.parentElement;
        pre.style.position = 'relative';
        pre.insertBefore(header, pre.firstChild);
    });

    // Initialize lucide icons in new buttons
    if (window.lucide) {
        window.lucide.createIcons();
    }
}
