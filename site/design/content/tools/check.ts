// Independent checks on site/src/lib/content/tutorial.ts against the draft.
// Parses the draft line by line on its own; shares nothing with gen.ts.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { TUTORIAL } from '../../../src/lib/content/tutorial.ts';
import type { Callout, FileView } from '../../../src/lib/content/tutorial.types.ts';

const DRAFT = fileURLToPath(new URL('../tutorial-draft.md', import.meta.url));
const errors: string[] = [];
const notes: string[] = [];
const fail = (s: string): void => void errors.push(s);

// ---------- structural checks ----------
const nLines = (f: FileView): number => f.text.split('\n').length;
const MARK = /<mark data-c="([^"]+)">/g;
const marksIn = (s: string): string[] => [...s.matchAll(MARK)].map((m) => m[1]!);
const words = (html: string[]): number => html.join(' ').replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;

function checkGroup(where: string, files: FileView[], callouts: Callout[], htmls: string[]): void {
	const byPath = new Map<string, FileView>();
	for (const f of files) {
		if (byPath.has(f.path)) fail(`${where}: two files at ${f.path}`);
		byPath.set(f.path, f);
		const n = nLines(f);
		for (const a of f.added ?? []) if (a < 1 || a > n) fail(`${where} ${f.path}: added ${a} outside 1..${n}`);
		for (const r of f.removed ?? []) if (r.before < 1 || r.before > n) fail(`${where} ${f.path}: removed before ${r.before} outside`);
		let visible = n;
		for (const [a, b] of f.fold ?? []) {
			if (a < 1 || b > n || a > b) fail(`${where} ${f.path}: bad fold ${a}-${b}`);
			visible -= b - a;
			for (let i = a; i <= b; i++) if (f.added?.includes(i)) fail(`${where} ${f.path}: folded line ${i} is added`);
		}
		if (f.fold) notes.push(`fold ${where} ${f.path}: ${f.fold.map(([a, b]) => `${a}-${b}`).join(', ')} (${n} lines, ${visible} visible)`);
		if (visible > 26) notes.push(`TALL ${where} ${f.path}: ${visible} visible lines`);
	}
	for (const c of callouts) {
		const f = byPath.get(c.file);
		if (!f) {
			fail(`${where} ${c.label}: no file ${c.file}`);
			continue;
		}
		const n = nLines(f);
		const to = c.to ?? c.line;
		if (c.line < 1 || c.line > n || to < c.line || to > n) fail(`${where} ${c.label}: lines ${c.line}-${to} outside 1..${n}`);
		for (let i = c.line; i <= to; i++) {
			for (const [a, b] of f.fold ?? []) if (i >= a && i <= b) fail(`${where} ${c.label}: targets folded line ${i}`);
		}
	}
	const labels = new Set(callouts.map((c) => c.label));
	for (const h of [...htmls, ...callouts.map((c) => c.html)]) {
		for (const m of marksIn(h)) if (!labels.has(m)) fail(`${where}: mark ${m} has no callout here`);
	}
}

const labelKey = (l: string): string => (l.startsWith('R.') ? `9.${l.slice(2)}` : l);
for (const lv of TUTORIAL) {
	const all: string[] = [];
	if (lv.opening) {
		checkGroup(`L${lv.n} opening`, lv.opening.files, [], lv.opening.prose);
		if (lv.opening.prose.some((p) => marksIn(p).length)) fail(`L${lv.n} opening has marks`);
	}
	for (const s of lv.steps) {
		checkGroup(s.id, s.files, s.callouts, s.prose);
		all.push(...s.callouts.map((c) => c.label));
		for (const c of s.callouts) if (!c.label.startsWith(s.id)) fail(`${s.id}: callout ${c.label} in wrong step`);
		const w = words(s.prose);
		if (w > 140) notes.push(`LONG ${s.id}: ${w} words of prose`);
	}
	if (lv.realThing) {
		const r = lv.realThing;
		checkGroup(`L${lv.n} real`, r.files, r.callouts, [r.intro, ...(r.after ?? [])]);
		all.push(...r.callouts.map((c) => c.label));
	}
	if (new Set(all).size !== all.length) fail(`L${lv.n}: duplicate labels`);
	const sorted = [...all].sort((a, b) => labelKey(a).localeCompare(labelKey(b)));
	if (sorted.join() !== all.join()) fail(`L${lv.n}: labels out of order: ${all.join(' ')}`);
	const strs = [lv.intro, ...lv.exercise.prompt, ...lv.exercise.answer.flatMap((a) => ('prose' in a ? [a.prose] : []))];
	for (const s of strs) if (marksIn(s).length) fail(`L${lv.n}: mark outside a step`);
	notes.push(`L${lv.n}: ${lv.steps.length} steps, ${lv.steps.reduce((n, s) => n + s.files.length, 0)} step files, ${lv.steps.reduce((n, s) => n + s.callouts.length, 0)} step callouts; real thing ${lv.realThing ? `${lv.realThing.files.length} files, ${lv.realThing.callouts.length} callouts` : 'none'}; opening ${lv.opening ? 'yes' : 'none'}`);
}

// ---------- coverage of the draft ----------
const allStrings: string[] = [];
(function walk(v: unknown): void {
	if (typeof v === 'string') allStrings.push(v);
	else if (Array.isArray(v)) v.forEach(walk);
	else if (v && typeof v === 'object') Object.values(v).forEach(walk);
})(TUTORIAL);
const norm = (s: string): string => s.replace(/<mark data-c="[^"]+">/g, '').replace(/<\/mark>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const haystack = allStrings.map(norm);
const codeStrings = new Set<string>();
(function walkCode(v: unknown, key?: string): void {
	if (typeof v === 'string' && (key === 'text' || key === 'code')) codeStrings.add(v);
	else if (Array.isArray(v)) v.forEach((x) => walkCode(x, key));
	else if (v && typeof v === 'object') Object.entries(v).forEach(([k, x]) => walkCode(x, k));
})(TUTORIAL);
const found = (s: string): boolean => haystack.some((h) => h.includes(s));
const toHtml = (s: string): string => s.replace(/`([^`]+)`/g, '<code>$1</code>');

const lines = readFileSync(DRAFT, 'utf8').split('\n');
let fence: string | null = null;
let buf: string[] = [];
let fenceStart = 0;
const missingParas: string[] = [];
for (let i = 8; i < lines.length; i++) {
	const l = lines[i]!;
	if (l === '## Open Questions') break;
	if (fence) {
		if (l === fence) {
			const text = buf.join('\n');
			if (!codeStrings.has(text)) notes.push(`FENCE not carried whole (draft line ${fenceStart}): ${text.split('\n')[0]}…`);
			fence = null;
		} else buf.push(l);
		continue;
	}
	const f = /^(`{3,})\w*$/.exec(l);
	if (f) {
		fence = f[1]!;
		buf = [];
		fenceStart = i + 2;
		continue;
	}
	if (l.trim() === '' || l === '---') continue;
	if (l.startsWith('## ')) {
		const t = l.slice(3).replace(/^Level \d: /, '');
		if (!found(t)) fail(`title missing: ${l}`);
		continue;
	}
	if (l.startsWith('### ')) {
		const t = l.slice(4).replace(/^\d\.\d /, '').replace(/^The Real Thing: /, '');
		if (!found(t) && !found(t.replace(/`/g, ''))) notes.push(`HEADING not carried as is (line ${i + 1}): ${l}`);
		continue;
	}
	const b = /^- \*\*([^*]+)\*\* (.*)$/.exec(l);
	const text = b ? b[2]! : l.replace(/^\*\*Answer\.\*\* /, '');
	if (found(toHtml(text))) continue;
	// not found whole: report which sentences are missing
	const sentences = text.split(/(?<=[.:])\s+(?=[A-Z`])/);
	const missing = sentences.filter((s) => !found(toHtml(s).replace(/:$/, '')));
	missingParas.push(`line ${i + 1}: ${missing.length === sentences.length ? text : 'part: ' + missing.join(' | ')}`);
}

console.log('== notes');
for (const n of notes) console.log(n);
console.log('\n== draft prose not carried as a paragraph');
for (const m of missingParas) console.log(m);
console.log('\n== errors');
for (const e of errors) console.log(e);
console.log(errors.length ? `${errors.length} errors` : 'no errors');
