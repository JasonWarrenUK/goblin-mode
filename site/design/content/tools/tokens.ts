// Tokenise the tutorial draft: h2, h3, paragraphs, fences, callout bullets.
import { readFileSync } from 'node:fs';

export const DRAFT = '/Users/jasonwarren/.claude/.claude/worktrees/site-pages-site/site/design/content/tutorial-draft.md';

export type Token =
	| { k: 'h2'; text: string; line: number }
	| { k: 'h3'; text: string; line: number }
	| { k: 'para'; text: string; line: number }
	| { k: 'fence'; lang: string; text: string; line: number }
	| { k: 'bullet'; label: string; text: string; line: number };

export function tokenise(): Token[] {
	const lines = readFileSync(DRAFT, 'utf8').split('\n');
	const out: Token[] = [];
	let i = 0;
	while (i < lines.length) {
		const l = lines[i]!;
		if (l === '## Open Questions') break;
		const fence = /^(`{3,})(\w*)$/.exec(l);
		if (fence) {
			const close = fence[1]!;
			const body: string[] = [];
			const start = i + 1;
			i++;
			while (lines[i] !== close) {
				if (i >= lines.length) throw new Error('unclosed fence at ' + start);
				body.push(lines[i]!);
				i++;
			}
			out.push({ k: 'fence', lang: fence[2]!, text: body.join('\n'), line: start });
			i++;
			continue;
		}
		if (l.startsWith('## ')) out.push({ k: 'h2', text: l.slice(3), line: i + 1 });
		else if (l.startsWith('### ')) out.push({ k: 'h3', text: l.slice(4), line: i + 1 });
		else if (l.startsWith('- **')) {
			const m = /^- \*\*([^*]+)\*\* (.*)$/.exec(l);
			if (!m) throw new Error('odd bullet ' + l);
			out.push({ k: 'bullet', label: m[1]!, text: m[2]!, line: i + 1 });
		} else if (l.trim() === '' || l === '---') {
			// skip
		} else {
			if (lines[i + 1] !== undefined && lines[i + 1]!.trim() !== '' && lines[i + 1] !== '---' && !lines[i + 1]!.startsWith('```')) {
				throw new Error('multi-line paragraph at ' + (i + 1));
			}
			out.push({ k: 'para', text: l, line: i + 1 });
		}
		i++;
	}
	return out;
}

if (import.meta.main) {
	for (const t of tokenise()) {
		if (t.line > 996) break;
		const s = t.k === 'fence' ? `[${t.lang}] ${t.text.split('\n').length} lines: ${t.text.split('\n')[0]}` : 'text' in t ? t.text.slice(0, 70) : '';
		console.log(t.line, t.k, t.k === 'bullet' ? t.label : '', s);
	}
}
