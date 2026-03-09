import { describe, it, expect, beforeEach } from 'vitest';
import { renderMarkdown } from '../vault/chat/markdown.js';

describe('renderMarkdown', () => {
    beforeEach(() => {
        document.body.innerHTML = '';
    });

    it('renders bold text', () => {
        const html = renderMarkdown('**hello**');
        expect(html).toContain('<strong>hello</strong>');
    });

    it('renders code blocks with hljs class', () => {
        const html = renderMarkdown('```python\nprint("hi")\n```');
        expect(html).toContain('<code');
        expect(html).toContain('print');
    });

    it('sanitizes XSS', () => {
        const html = renderMarkdown('<script>alert("xss")</script>');
        expect(html).not.toContain('<script>');
    });

    it('renders inline code', () => {
        const html = renderMarkdown('Use `foo()` here');
        expect(html).toContain('<code>foo()</code>');
    });

    it('renders lists', () => {
        const html = renderMarkdown('- item 1\n- item 2');
        expect(html).toContain('<li>');
    });

    it('handles empty input', () => {
        expect(renderMarkdown('')).toBe('');
        expect(renderMarkdown(null)).toBe('');
    });

    it('renders headers', () => {
        const html = renderMarkdown('# Title\n## Subtitle');
        expect(html).toContain('<h1');
        expect(html).toContain('<h2');
    });

    it('renders tables', () => {
        const html = renderMarkdown('| A | B |\n|---|---|\n| 1 | 2 |');
        expect(html).toContain('<table>');
        expect(html).toContain('<td>');
    });

    it('renders blockquotes', () => {
        const html = renderMarkdown('> quote text');
        expect(html).toContain('<blockquote>');
    });

    it('renders links safely', () => {
        const html = renderMarkdown('[click](https://example.com)');
        expect(html).toContain('href="https://example.com"');
        expect(html).toContain('click');
    });
});
