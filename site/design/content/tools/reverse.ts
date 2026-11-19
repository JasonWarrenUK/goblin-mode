import { readFileSync } from 'node:fs';
import { TUTORIAL } from '/Users/jasonwarren/.claude/.claude/worktrees/site-pages-site/site/src/lib/content/tutorial.ts';
const lines = readFileSync('/Users/jasonwarren/.claude/.claude/worktrees/site-pages-site/site/design/content/tutorial-draft.md', 'utf8').split('\n');
const units = new Set<string>();
let inFence: string | null = null;
for (const l of lines) {
	if (l === '## Open Questions') break;
	if (inFence) { if (l === inFence) inFence = null; continue; }
	const f = /^(`{3,})\w*$/.exec(l); if (f) { inFence = f[1]!; continue; }
	if (!l.trim() || l === '---' || l.startsWith('#')) continue;
	const b = /^- \*\*([^*]+)\*\* (.*)$/.exec(l);
	units.add((b ? b[2]! : l.replace(/^\*\*Answer\.\*\* /, '')).replace(/`([^`]+)`/g, '<code>$1</code>'));
}
units.add('Both scripts are unchanged from 4.1 and 2.3.');
const norm = (s: string): string => s.replace(/<mark data-c="[^"]+">/g, '').replace(/<\/mark>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
let bad = 0, n = 0;
const marks: string[] = [];
function chk(where: string, s: string): void {
	n++;
	if (!units.has(norm(s))) { bad++; console.log('NOT EXACT', where, s.slice(0, 100)); }
	for (const m of s.matchAll(/<mark data-c="([^"]+)">(.*?)<\/mark>/g)) marks.push(`${where} ${m[1]}: ${m[2]}`);
}
for (const lv of TUTORIAL) {
	chk(`L${lv.n} intro`, lv.intro);
	lv.opening?.prose.forEach((p) => chk(`L${lv.n} opening`, p));
	for (const s of lv.steps) { s.prose.forEach((p) => chk(s.id, p)); s.callouts.forEach((c) => chk(c.label, c.html)); }
	if (lv.realThing) { chk(`L${lv.n} real intro`, lv.realThing.intro); lv.realThing.after?.forEach((p) => chk(`L${lv.n} real after`, p)); lv.realThing.callouts.forEach((c) => chk(`L${lv.n} ${c.label}`, c.html)); }
	lv.exercise.prompt.forEach((p) => chk(`L${lv.n} ex`, p));
	lv.exercise.answer.forEach((a) => 'prose' in a && chk(`L${lv.n} answer`, a.prose));
}
console.log(`${n} prose fields, ${bad} not exact`);
console.log(marks.join('\n'));
