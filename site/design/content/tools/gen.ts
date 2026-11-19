// Builds site/src/lib/content/tutorial.ts from the approved draft.
import { writeFileSync } from 'node:fs';
import { tokenise, type Token } from './tokens.ts';

const OUT = '/Users/jasonwarren/.claude/.claude/worktrees/site-pages-site/site/src/lib/content/tutorial.ts';
const T = tokenise();

// ---------- draft access ----------
interface Sec {
	h: string;
	p: (i: number) => string;
	f: (i: number) => string;
	flang: (i: number) => string;
	b: (label: string) => string;
	paras: string[];
}

function levelTokens(n: number): Token[] {
	const start = T.findIndex((t) => t.k === 'h2' && t.text.startsWith(`Level ${n}:`));
	if (start < 0) throw new Error('no level ' + n);
	let end = T.findIndex((t, i) => i > start && t.k === 'h2');
	if (end < 0) end = T.length;
	return T.slice(start, end);
}

function mkSec(toks: Token[], h: string): Sec {
	const paras = toks.filter((t) => t.k === 'para').map((t) => t.text);
	const fences = toks.filter((t) => t.k === 'fence') as Extract<Token, { k: 'fence' }>[];
	const bullets = toks.filter((t) => t.k === 'bullet') as Extract<Token, { k: 'bullet' }>[];
	return {
		h,
		paras,
		p: (i) => {
			const v = paras[i];
			if (v === undefined) throw new Error(`${h}: no para ${i}`);
			return v;
		},
		f: (i) => {
			const v = fences[i];
			if (!v) throw new Error(`${h}: no fence ${i}`);
			return v.text;
		},
		flang: (i) => fences[i]!.lang,
		b: (label) => {
			const v = bullets.find((x) => x.label === label);
			if (!v) throw new Error(`${h}: no bullet ${label}`);
			return v.text;
		},
	};
}

function sec(n: number, prefix: string): Sec {
	const toks = levelTokens(n);
	const start = toks.findIndex((t) => t.k === 'h3' && t.text.startsWith(prefix));
	if (start < 0) throw new Error(`level ${n}: no section ${prefix}`);
	let end = toks.findIndex((t, i) => i > start && t.k === 'h3');
	if (end < 0) end = toks.length;
	return mkSec(toks.slice(start + 1, end), (toks[start] as { text: string }).text);
}

function levelHead(n: number): { title: string; intro: string } {
	const toks = levelTokens(n);
	const h = (toks[0] as { text: string }).text.replace(/^Level \d: /, '');
	const intro = toks[1];
	if (!intro || intro.k !== 'para') throw new Error('no intro for ' + n);
	return { title: h, intro: md(intro.text) };
}

// ---------- markdown to the allowed HTML ----------
const esc = (s: string): string => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
function md(s: string): string {
	if (/\*\*/.test(s.replace(/`[^`]*`/g, ''))) throw new Error('bold outside code: ' + s);
	return esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');
}
const ANSWER = '**Answer.** ';
function answerPara(s: string): string {
	if (!s.startsWith(ANSWER)) throw new Error('not an answer: ' + s);
	return md(s.slice(ANSWER.length));
}
function mark(html: string, marks: [string, string][]): string {
	let out = html;
	for (const [phrase, label] of marks) {
		const count = out.split(phrase).length - 1;
		if (count !== 1) throw new Error(`mark ${label}: phrase found ${count} times: ${phrase}`);
		out = out.replace(phrase, `<mark data-c="${label}">${phrase}</mark>`);
	}
	return out;
}

// ---------- files ----------
interface FileView {
	path: string;
	lang: string;
	text: string;
	added?: number[];
	removed?: { before: number; text: string }[];
	fold?: [number, number][];
}
interface Callout { label: string; file: string; line: number; to?: number; html?: string }

const linesOf = (f: FileView | string): string[] => (typeof f === 'string' ? f : f.text).split('\n');
/** 1-based number of the only line containing `needle` (or the nth). */
function at(f: FileView | string, needle: string, nth = 1): number {
	const hit = (l: string): boolean => (needle.startsWith('^') ? l.startsWith(needle.slice(1)) : l.includes(needle));
	const hits = linesOf(f).flatMap((l, i) => (hit(l) ? [i + 1] : []));
	if (nth === 1 && hits.length !== 1) throw new Error(`at: ${hits.length} lines contain ${needle}`);
	const v = hits[nth - 1];
	if (v === undefined) throw new Error('at: no line ' + needle);
	return v;
}
const range = (a: number, b: number): number[] => Array.from({ length: b - a + 1 }, (_, i) => a + i);
const every = (text: string): number[] => range(1, text.split('\n').length);

function fv(path: string, lang: string, text: string, extra: Partial<FileView> = {}): FileView {
	return { path, lang, text, ...extra };
}
function co(label: string, s: Sec, file: FileView, line: number, to?: number): Callout {
	const c: Callout = { label, file: file.path, line };
	if (to !== undefined && to !== line) c.to = to;
	c.html = md(s.b(label));
	return c;
}

const SKILL = '.claude/skills/tidy-imports/SKILL.md';
const SCRIPT = '.claude/skills/tidy-imports/scripts/sort-imports.sh';
const CHECK_SKILL = '.claude/skills/tidy-imports-check/SKILL.md';
const CHECK_SCRIPT = '.claude/skills/tidy-imports-check/scripts/check-imports.sh';

function caption(s: Sec, i: number, expect: string): void {
	if (!s.p(i).startsWith(expect)) throw new Error(`${s.h}: caption ${i} is "${s.p(i)}", expected ${expect}`);
}

// ================= Level 1 =================
const L1 = levelHead(1);
const s11 = sec(1, '1.1');
caption(s11, 1, '`.claude/skills/tidy-imports/SKILL.md` after step 1.1:');
const sk11 = fv(SKILL, 'markdown', s11.f(1), { added: every(s11.f(1)) });
const mkdir = fv('Terminal', 'bash', s11.f(0));
const s12 = sec(1, '1.2');
caption(s12, 1, '`.claude/skills/tidy-imports/SKILL.md` after step 1.2:');
const sk12text = s12.f(0);
const sk12 = fv(SKILL, 'markdown', sk12text, {
	added: [at(sk12text, 'arguments: [path]'), at(sk12text, 'argument-hint'), at(sk12text, 'Tidy the imports in $path.')],
});
const s13 = sec(1, '1.3');
caption(s13, 1, '`src/app.ts` before the run:');
caption(s13, 2, '`src/app.ts` after the run:');
caption(s13, 3, '`.claude/skills/tidy-imports/SKILL.md` after step 1.3: unchanged from 1.2.');
const app13 = fv('src/app.ts', 'ts', s13.f(2));
const sk13 = fv(SKILL, 'markdown', sk12text);
const run13 = fv('Claude Code', 'text', s13.f(0));
const e1 = sec(1, 'Try it');

const level1 = {
	n: 1,
	title: L1.title,
	intro: L1.intro,
	steps: [
		{
			id: '1.1',
			title: s11.h.replace(/^1\.1 /, ''),
			prose: [mark(md(s11.p(0)), [['everything after that is the instructions Claude follows', '1.1c']])],
			files: [sk11, mkdir],
			callouts: [
				co('1.1a', s11, sk11, at(sk11, 'name: tidy-imports')),
				co('1.1b', s11, sk11, at(sk11, 'description:')),
				co('1.1c', s11, sk11, at(sk11, 'Sort the import statements at the top of the file'), at(sk11, 'the imports exactly as it was.')),
			],
		},
		{
			id: '1.2',
			title: s12.h.replace(/^1\.2 /, ''),
			prose: [
				mark(md(s12.p(0)), [
					['<code>arguments: [path]</code> gives the first word after the command a name', '1.2a'],
					['wherever <code>$path</code> appears in the body, Claude Code swaps in that word', '1.2c'],
					['<code>argument-hint</code> is the reminder you see while typing the command', '1.2b'],
				]),
			],
			files: [sk12],
			callouts: [
				co('1.2a', s12, sk12, at(sk12, 'arguments: [path]')),
				co('1.2b', s12, sk12, at(sk12, 'argument-hint')),
				co('1.2c', s12, sk12, at(sk12, 'Tidy the imports in $path.')),
			],
		},
		{
			id: '1.3',
			title: s13.h.replace(/^1\.3 /, ''),
			prose: [md(s13.p(0))],
			files: [app13, sk13, run13],
			callouts: [
				co('1.3a', s13, sk13, at(sk13, 'Tidy the imports in $path.')),
				co('1.3b', s13, app13, at(app13, 'const app = express();')),
			],
			output: { label: 'src/app.ts before the run', text: s13.f(1) },
		},
	],
	exercise: {
		title: e1.h,
		prompt: [md(e1.p(0))],
		answer: [{ prose: answerPara(e1.p(1)) }, { code: e1.f(0), lang: e1.flang(0) }, { prose: md(e1.p(2)) }],
	},
};

// ================= Level 2 =================
const L2 = levelHead(2);
const o2 = sec(2, 'Where Level 1 Left It');
if (o2.f(0) !== sk12text) throw new Error('level 2 opening differs from 1.2');
const s21 = sec(2, '2.1');
caption(s21, 1, '`.claude/skills/tidy-imports/scripts/sort-imports.sh` after step 2.1:');
caption(s21, 3, '`.claude/skills/tidy-imports/SKILL.md` after step 2.1:');
const sc21text = s21.f(0);
const sc21 = fv(SCRIPT, 'bash', sc21text, { added: every(sc21text) });
const sk21text = s21.f(1);
const sortLines = linesOf(sk12text).slice(at(sk12text, 'Sort the import statements at the top of the file') - 1, at(sk12text, 'the imports exactly as it was.'));
if (sortLines.length !== 3) throw new Error('expected three sorting lines');
const sk21 = fv(SKILL, 'markdown', sk21text, {
	added: range(at(sk21text, 'Run the script on the file'), at(sk21text, 'report its message and stop.')),
	removed: sortLines.map((text) => ({ before: at(sk21text, 'Run the script on the file'), text })),
});
const s22 = sec(2, '2.2');
caption(s22, 2, '`.claude/skills/tidy-imports/SKILL.md` after step 2.2:');
const sk22 = fv(SKILL, 'markdown', s22.f(0), { added: [at(s22.f(0), '^allowed-tools:')] });
const s23 = sec(2, '2.3');
caption(s23, 1, "The script's two new lines, in context:");
caption(s23, 3, '`.claude/tidy-imports.log` after two runs:');
caption(s23, 4, '`.claude/skills/tidy-imports/SKILL.md` after step 2.3:');
// the draft shows the script's two new lines in context; rebuild the whole file
const excerpt = linesOf(s23.f(0));
const ledgerLine = excerpt[2]!;
const printfLine = excerpt[5]!;
if (!ledgerLine.startsWith('ledger=') || !printfLine.startsWith('printf')) throw new Error('2.3 excerpt shape');
if (excerpt[1] !== 'file="$1"' || excerpt[4] !== 'mv "$file.tmp" "$file"' || excerpt[6] !== 'echo "sorted $count imports in $file"') throw new Error('2.3 excerpt context');
const sc23lines = linesOf(sc21text).flatMap((l) => (l === excerpt[1] ? [l, ledgerLine] : l === excerpt[4] ? [l, printfLine] : [l]));
const sc23text = sc23lines.join('\n');
const sc23 = fv(SCRIPT, 'bash', sc23text, { added: [at(sc23text, 'ledger='), at(sc23text, 'printf')] });
const sk23text = s23.f(2);
const sk23 = fv(SKILL, 'markdown', sk23text, {
	added: [
		at(sk23text, 'Read .claude/tidy-imports.log'),
		at(sk23text, 'already listed there'),
		at(sk23text, 'The script also writes the ledger line'),
		at(sk23text, '.claude/tidy-imports.log yourself.'),
	],
});
const r2 = sec(2, 'The Real Thing');
const real2 = fv('skills/project-tag_version/SKILL.md', 'markdown', r2.f(0));
const e2 = sec(2, 'Try it');

const level2 = {
	n: 2,
	title: L2.title,
	intro: L2.intro,
	opening: { title: o2.h, prose: [md(o2.p(0))], files: [fv(SKILL, 'markdown', o2.f(0))] },
	steps: [
		{
			id: '2.1',
			title: s21.h.replace(/^2\.1 /, ''),
			prose: [mark(md(s21.p(0)), [['call the script as <code>${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh</code>', '2.1a']])],
			files: [sk21, sc21],
			callouts: [
				co('2.1a', s21, sk21, at(sk21, '${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh')),
				co('2.1b', s21, sk21, at(sk21, 'Do not reorder any'), at(sk21, 'script exits non-zero')),
			],
		},
		{
			id: '2.2',
			title: s22.h.replace(/^2\.2 /, ''),
			prose: [mark(md(s22.p(0)), [['<code>allowed-tools</code> approves the calls it names', '2.2a']]), md(s22.p(1))],
			files: [sk22],
			callouts: [co('2.2a', s22, sk22, at(sk22, '^allowed-tools:'))],
		},
		{
			id: '2.3',
			title: s23.h.replace(/^2\.3 /, ''),
			prose: [
				mark(md(s23.p(0)), [
					['a later run can tell what an earlier one touched', '2.3a'],
					['The script appends one line per file', '2.3b'],
				]),
			],
			files: [sk23, sc23],
			callouts: [
				co('2.3a', s23, sk23, at(sk23, 'Read .claude/tidy-imports.log'), at(sk23, 'already listed there')),
				co('2.3b', s23, sk23, at(sk23, 'The script also writes the ledger line'), at(sk23, '.claude/tidy-imports.log yourself.')),
			],
			output: { label: '.claude/tidy-imports.log after two runs', text: s23.f(1) },
		},
	],
	realThing: {
		name: 'project-tag_version',
		intro: mark(md(r2.p(0)), [['the first is something <code>tidy-imports</code> gets in level 3', 'R.a']]),
		files: [real2],
		callouts: [
			co('R.a', r2, real2, at(real2, 'disable-model-invocation: true')),
			co('R.b', r2, real2, at(real2, '^allowed-tools:')),
			co('R.c', r2, real2, at(real2, 'TAG=')),
		],
	},
	exercise: {
		title: e2.h,
		prompt: [md(e2.p(0))],
		answer: [{ prose: answerPara(e2.p(1)) }, { code: e2.f(0), lang: e2.flang(0) }, { prose: md(e2.p(2)) }],
	},
};

// ================= Level 3 =================
const L3 = levelHead(3);
/** Fold the fenced script call: from the blank after "Run the script on the file" to the blank after the closing fence. */
function foldScriptCall(text: string): [number, number] {
	const run = at(text, 'Run the script on the file');
	const lines = linesOf(text);
	if (lines[run] !== '' || lines[run + 1] !== '```bash' || lines[run + 3] !== '```' || lines[run + 4] !== '') throw new Error('script call shape');
	return [run + 1, run + 5];
}
const o3 = sec(3, 'Where Level 2 Left It');
if (o3.f(0) !== sk23text) throw new Error('level 3 opening differs from 2.3');
const s31 = sec(3, '3.1');
caption(s31, 1, '`.claude/skills/tidy-imports/SKILL.md` after step 3.1:');
const sk31text = s31.f(0);
const sk31 = fv(SKILL, 'markdown', sk31text, {
	added: [at(sk31text, 'when_to_use:'), at(sk31text, 'disable-model-invocation:')],
	fold: [foldScriptCall(sk31text)],
});
const s32 = sec(3, '3.2');
caption(s32, 1, '`.claude/skills/tidy-imports/SKILL.md` after step 3.2:');
const sk32text = s32.f(0);
const sk32 = fv(SKILL, 'markdown', sk32text, {
	added: [at(sk32text, 'model: sonnet'), at(sk32text, 'effort: low')],
	fold: [foldScriptCall(sk32text)],
});
const s33 = sec(3, '3.3');
caption(s33, 1, '`.claude/skills/tidy-imports/SKILL.md` after step 3.3:');
const sk33text = s33.f(0);
const sk33 = fv(SKILL, 'markdown', sk33text, {
	added: [at(sk33text, 'disallowed-tools:')],
	fold: [foldScriptCall(sk33text)],
});
const r3 = sec(3, 'The Real Thing');
const real3 = fv('skills/pr-update/SKILL.md', 'markdown', r3.f(0));
const e3 = sec(3, 'Try it');

const level3 = {
	n: 3,
	title: L3.title,
	intro: L3.intro,
	opening: { title: o3.h, prose: [md(o3.p(0))], files: [fv(SKILL, 'markdown', o3.f(0))] },
	steps: [
		{
			id: '3.1',
			title: s31.h.replace(/^3\.1 /, ''),
			prose: [
				mark(md(s31.p(0)), [
					['write the line out anyway', '3.1b'],
					['with a comment saying why', '3.1c'],
					['add <code>when_to_use</code> to tell Claude when to reach for it', '3.1a'],
				]),
			],
			files: [sk31],
			callouts: [
				co('3.1a', s31, sk31, at(sk31, 'when_to_use:')),
				co('3.1b', s31, sk31, at(sk31, 'disable-model-invocation:')),
				co('3.1c', s31, sk31, at(sk31, 'disable-model-invocation:')),
				co('3.1d', s31, sk31, at(sk31, 'disable-model-invocation:')),
			],
		},
		{
			id: '3.2',
			title: s32.h.replace(/^3\.2 /, ''),
			prose: [
				mark(md(s32.p(0)), [
					['<code>model</code> and <code>effort</code> override the session for the rest of the turn the skill runs in', '3.2c'],
				]),
			],
			files: [sk32],
			callouts: [
				co('3.2a', s32, sk32, at(sk32, 'model: sonnet')),
				co('3.2b', s32, sk32, at(sk32, 'effort: low')),
				co('3.2c', s32, sk32, at(sk32, 'model: sonnet'), at(sk32, 'effort: low')),
			],
		},
		{
			id: '3.3',
			title: s33.h.replace(/^3\.3 /, ''),
			prose: [
				mark(md(s33.p(0)), [
					['<code>disallowed-tools</code> enforces that', '3.3a'],
					['Keep the sentence in the body too, because the removal only lasts until your next message', '3.3c'],
				]),
			],
			files: [sk33],
			callouts: [
				co('3.3a', s33, sk33, at(sk33, 'disallowed-tools:')),
				co('3.3b', s33, sk33, at(sk33, 'disallowed-tools:')),
				co('3.3c', s33, sk33, at(sk33, 'Do not reorder any'), at(sk33, 'lines yourself')),
				co('3.3d', s33, sk33, at(sk33, 'disallowed-tools:')),
			],
		},
	],
	realThing: {
		name: 'pr-update',
		intro: mark(md(r3.p(0)), [['a comment in its frontmatter names the gate that makes that safe', 'R.c']]),
		files: [real3],
		callouts: [
			co('R.a', r3, real3, at(real3, 'when_to_use:')),
			co('R.b', r3, real3, at(real3, 'model: sonnet'), at(real3, 'effort: medium')),
			co('R.c', r3, real3, at(real3, 'disable-model-invocation: false')),
			co('R.d', r3, real3, at(real3, '**Wait for my approval.**')),
		],
		after: [md(r3.p(1))],
	},
	exercise: {
		title: e3.h,
		prompt: [md(e3.p(0))],
		answer: [{ prose: answerPara(e3.p(1)) }, { code: e3.f(0), lang: e3.flang(0) }, { prose: md(e3.p(2)) }],
	},
};

// ================= Level 4 =================
const L4 = levelHead(4);
const o4 = sec(4, 'Where Level 3 Left It');
if (o4.f(0) !== sk33text) throw new Error('level 4 opening differs from 3.3');
const s41 = sec(4, '4.1');
caption(s41, 1, '`.claude/skills/tidy-imports-check/scripts/check-imports.sh` after step 4.1:');
caption(s41, 3, '`.claude/skills/tidy-imports-check/SKILL.md` after step 4.1:');
caption(s41, 5, 'On `src/app.ts` from 1.3, before tidying, the script prints:');
const cs41 = fv(CHECK_SCRIPT, 'bash', s41.f(0), { added: every(s41.f(0)) });
const ck41 = fv(CHECK_SKILL, 'markdown', s41.f(1), { added: every(s41.f(1)) });
const s42 = sec(4, '4.2');
caption(s42, 1, '`.claude/skills/tidy-imports/SKILL.md` after step 4.2:');
const sk42text = s42.f(0);
const sk42 = fv(SKILL, 'markdown', sk42text, {
	added: range(at(sk42text, 'Load the tidy-imports-check skill'), at(sk42text, 'cannot run, say why and stop.')),
	fold: [[at(sk42text, 'Run the script on the file') + 1, linesOf(sk42text).length]],
});
const s43 = sec(4, '4.3');
caption(s43, 1, '`.claude/skills/tidy-imports/SKILL.md` after step 4.3:');
const sk43text = s43.f(0);
const sk43 = fv(SKILL, 'markdown', sk43text, {
	added: [
		at(sk43text, 'disable-model-invocation:'),
		at(sk43text, '^allowed-tools:'),
		...range(at(sk43text, 'Run `git status'), at(sk43text, 'user replies yes.')),
	],
	fold: [
		[at(sk43text, 'Read .claude/tidy-imports.log'), at(sk43text, 'cannot run, say why and stop.')],
		[at(sk43text, 'Run the script on the file') + 1, linesOf(sk43text).length],
	],
});
const r4 = sec(4, 'The Real Thing');
caption(r4, 1, '`skills/pr-review-dry_run/SKILL.md`:');
caption(r4, 2, '`skills/pr-review/SKILL.md`:');
caption(r4, 3, '`skills/branch-qa_review/SKILL.md`:');
const dry = fv('skills/pr-review-dry_run/SKILL.md', 'markdown', r4.f(0));
const prr = fv('skills/pr-review/SKILL.md', 'markdown', r4.f(1));
const bqa = fv('skills/branch-qa_review/SKILL.md', 'markdown', r4.f(2));
const e4 = sec(4, 'Try it');

const level4 = {
	n: 4,
	title: L4.title,
	intro: L4.intro,
	opening: { title: o4.h, prose: [md(o4.p(0))], files: [fv(SKILL, 'markdown', o4.f(0), { fold: [foldScriptCall(o4.f(0))] })] },
	steps: [
		{
			id: '4.1',
			title: s41.h.replace(/^4\.1 /, ''),
			prose: [mark(md(s41.p(0)), [['its own script that reports and changes nothing', '4.1a']])],
			files: [cs41, ck41],
			callouts: [
				co('4.1a', s41, cs41, at(cs41, 'sort -c')),
				co('4.1b', s41, cs41, at(cs41, 'export LC_ALL=C')),
				co('4.1c', s41, ck41, at(ck41, 'disable-model-invocation:')),
				co('4.1d', s41, ck41, at(ck41, 'disallowed-tools:')),
			],
			output: { label: 'On src/app.ts from 1.3, before tidying, the script prints', text: s41.f(2) },
		},
		{
			id: '4.2',
			title: s42.h.replace(/^4\.2 /, ''),
			prose: [
				mark(md(s42.p(0)), [
					['the body just tells Claude to load it by name', '4.2a'],
					["That tool refuses a skill marked <code>disable-model-invocation: true</code> unless your own message names that skill's command", '4.2b'],
				]),
			],
			files: [sk42],
			callouts: [
				co('4.2a', s42, sk42, at(sk42, 'Load the tidy-imports-check skill')),
				co('4.2b', s42, sk42, at(sk42, 'the imports already sorted, say so and stop. If the check'), at(sk42, 'cannot run, say why and stop.')),
				co('4.2c', s42, sk42, at(sk42, 'model: sonnet'), at(sk42, 'effort: low')),
			],
		},
		{
			id: '4.3',
			title: s43.h.replace(/^4\.3 /, ''),
			prose: [md(s43.p(0))],
			files: [sk43],
			callouts: [
				co('4.3a', s43, sk43, at(sk43, 'Run `git status --porcelain')),
				co('4.3b', s43, sk43, at(sk43, "the rewrite cannot be undone from git. Show the check's"), at(sk43, 'report, say this and stop.')),
				co('4.3c', s43, sk43, at(sk43, 'user replies yes.')),
				co('4.3d', s43, sk43, at(sk43, 'disable-model-invocation:')),
			],
		},
	],
	realThing: {
		name: 'pr-review-dry_run, pr-review and branch-qa_review',
		intro: md(r4.p(0)),
		files: [dry, prr, bqa],
		callouts: [
			co('R.a', r4, dry, at(dry, 'disable-model-invocation: false # required so pr-review can call it')),
			co('R.b', r4, prr, at(prr, 'disable-model-invocation: false')),
			co('R.c', r4, prr, at(prr, 'Load the pr-review-dry_run skill')),
			co('R.d', r4, bqa, at(bqa, 'disable-model-invocation: true')),
		],
		after: [md(r4.p(4))],
	},
	exercise: {
		title: e4.h,
		prompt: [md(e4.p(0))],
		answer: [{ prose: answerPara(e4.p(1)) }],
	},
};

// ================= Level 5 =================
const L5 = levelHead(5);
const o5 = sec(5, 'Where Level 4 Left It');
caption(o5, 1, '`.claude/skills/tidy-imports/SKILL.md`:');
caption(o5, 2, '`.claude/skills/tidy-imports-check/SKILL.md`:');
if (o5.f(0) !== sk43text) throw new Error('level 5 opening differs from 4.3');
if (o5.f(1) !== s41.f(1)) throw new Error('level 5 opening check differs from 4.1');
const s51 = sec(5, '5.1');
caption(s51, 1, 'The plugin folder after step 5.1:');
caption(s51, 2, '`tidy/.claude-plugin/plugin.json` after step 5.1:');
caption(s51, 3, 'New in 5.1: every line, and the folder itself.');
const tree51 = fv('tidy', 'text', s51.f(0), { added: every(s51.f(0)) });
const pj51 = fv('tidy/.claude-plugin/plugin.json', 'json', s51.f(1), { added: every(s51.f(1)) });
const s52 = sec(5, '5.2');
caption(s52, 1, '`tidy/skills/tidy-imports/SKILL.md` after step 5.2:');
caption(s52, 3, '`tidy/skills/tidy-imports-check/SKILL.md` after step 5.2:');
const CHANGED_CHECK = 'Changed in 5.2: `tidy:tidy-imports` in `when_to_use` and the comment. ';
if (!s52.p(4).startsWith(CHANGED_CHECK)) throw new Error('5.2 changed line');
const bothScripts = s52.p(4).slice(CHANGED_CHECK.length);
const sk52text = s52.f(0);
const sk52 = fv('tidy/skills/tidy-imports/SKILL.md', 'markdown', sk52text, {
	added: range(at(sk52text, 'Load the tidy:tidy-imports-check skill'), at(sk52text, 'check cannot run, say why and stop.')),
	fold: [
		[at(sk52text, 'check cannot run, say why and stop.') + 1, at(sk52text, 'Run the script on the file') + 1],
		[at(sk52text, 'It sorts the import block') - 1, linesOf(sk52text).length],
	],
});
const ck52 = fv('tidy/skills/tidy-imports-check/SKILL.md', 'markdown', s52.f(1), {
	added: [at(s52.f(1), 'when_to_use:'), at(s52.f(1), 'disable-model-invocation:')],
});
const s53 = sec(5, '5.3');
caption(s53, 1, '`noor-tools/.claude-plugin/marketplace.json`:');
caption(s53, 2, 'New in 5.3: every line.');
const mk53 = fv('noor-tools/.claude-plugin/marketplace.json', 'json', s53.f(0), { added: every(s53.f(0)) });
const leadIn = (i: number): string => {
	const p = s53.p(i);
	if (!p.endsWith(':')) throw new Error('lead-in ' + p);
	return p.slice(0, -1);
};
const session53 = fv(leadIn(3), s53.flang(1), s53.f(1));
const shell53 = fv(leadIn(4), s53.flang(2), s53.f(2));
const project53 = fv(leadIn(5), s53.flang(3), s53.f(3));
const r5 = sec(5, 'The Real Thing');
caption(r5, 1, '`marketplace/goblin-scout/.claude-plugin/plugin.json`:');
caption(r5, 2, '`marketplace/goblin-scout/skills/start-roadbook/SKILL.md`:');
caption(r5, 3, '`.claude-plugin/marketplace.json` at the repository root:');
const gsManifest = fv('marketplace/goblin-scout/.claude-plugin/plugin.json', 'json', r5.f(0));
const gsSkill = fv('marketplace/goblin-scout/skills/start-roadbook/SKILL.md', 'markdown', r5.f(1));
const gsMarket = fv('.claude-plugin/marketplace.json', 'json', r5.f(2));
const e5 = sec(5, 'Try it');

const level5 = {
	n: 5,
	title: L5.title,
	intro: L5.intro,
	opening: { title: o5.h, prose: [md(o5.p(0))], files: [fv(SKILL, 'markdown', o5.f(0), { fold: sk43.fold }), fv(CHECK_SKILL, 'markdown', o5.f(1))] },
	steps: [
		{
			id: '5.1',
			title: s51.h.replace(/^5\.1 /, ''),
			prose: [
				mark(md(s51.p(0)), [
					['a manifest at <code>.claude-plugin/plugin.json</code> and its parts beside it', '5.1c'],
					['Call the plugin <code>tidy</code>', '5.1a'],
				]),
				md(s51.p(4)),
			],
			files: [pj51, tree51],
			callouts: [
				co('5.1a', s51, pj51, at(pj51, '"name": "tidy"')),
				co('5.1b', s51, pj51, at(pj51, '"version"')),
				co('5.1c', s51, tree51, at(tree51, '.claude-plugin/'), at(tree51, '\tskills/')),
			],
		},
		{
			id: '5.2',
			title: s52.h.replace(/^5\.2 /, ''),
			prose: [
				mark(md(s52.p(0)), [
					['<code>${CLAUDE_SKILL_DIR}</code> already avoids that', '5.2a'],
					['the call to the check, which now uses its plugin name', '5.2b'],
				]),
				md(bothScripts),
			],
			files: [sk52, ck52],
			callouts: [
				co('5.2a', s52, sk52, at(sk52, '^allowed-tools:')),
				co('5.2b', s52, sk52, at(sk52, 'Load the tidy:tidy-imports-check skill')),
				co('5.2c', s52, sk52, at(sk52, 'Read .claude/tidy-imports.log')),
			],
		},
		{
			id: '5.3',
			title: s53.h.replace(/^5\.3 /, ''),
			prose: [md(s53.p(0)), md(s53.p(6))],
			files: [mk53, session53, shell53, project53],
			callouts: [
				co('5.3a', s53, mk53, at(mk53, '"name": "tidy"')),
				co('5.3b', s53, mk53, at(mk53, '"source"')),
				co('5.3c', s53, session53, at(session53, 'tidy@noor-tools')),
				co('5.3d', s53, session53, at(session53, '/plugin marketplace add')),
			],
		},
	],
	realThing: {
		name: 'goblin-scout',
		intro: md(r5.p(0)),
		files: [gsManifest, gsSkill, gsMarket],
		callouts: [
			co('R.a', r5, gsManifest, at(gsManifest, '"name": "goblin-scout"')),
			co('R.b', r5, gsSkill, at(gsSkill, 'use goblin-scout:rebind-roadbook instead')),
			co('R.c', r5, gsSkill, at(gsSkill, '${CLAUDE_PLUGIN_ROOT}/references/')),
			co('R.d', r5, gsMarket, at(gsMarket, '"name": "goblin-scout"')),
		],
		after: [md(r5.p(4))],
	},
	exercise: {
		title: e5.h,
		prompt: [md(e5.p(0))],
		answer: [{ prose: answerPara(e5.p(1)) }],
	},
};

// ---------- sanity: every para in each section is accounted for ----------
// (the checker does the real coverage test; this only catches index slips)
const p53 = s53.paras.length;
if (p53 !== 7) throw new Error('5.3 paras ' + p53);

// ---------- emit ----------
const sq = (s: string): string => `'${s.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
const tl = (s: string): string => '`' + s.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$\{/g, '\\${') + '`';
const CODE_KEYS = new Set(['text', 'code']);

function emit(v: unknown, indent: number, key?: string): string {
	const pad = '\t'.repeat(indent);
	const inner = '\t'.repeat(indent + 1);
	if (typeof v === 'string') return key && CODE_KEYS.has(key) && v.includes('\n') ? tl(v) : sq(v);
	if (typeof v === 'number') return String(v);
	if (Array.isArray(v)) {
		if (v.length === 0) return '[]';
		if (v.every((x) => typeof x === 'number')) return `[${v.join(', ')}]`;
		if (v.every((x) => Array.isArray(x) && x.every((y) => typeof y === 'number'))) {
			return `[${v.map((x) => `[${(x as number[]).join(', ')}]`).join(', ')}]`;
		}
		return `[\n${v.map((x) => inner + emit(x, indent + 1, key === 'removed' ? undefined : key) + ',').join('\n')}\n${pad}]`;
	}
	if (v && typeof v === 'object') {
		const entries = Object.entries(v).filter(([, x]) => x !== undefined);
		return `{\n${entries.map(([k, x]) => `${inner}${k}: ${emit(x, indent + 1, k)},`).join('\n')}\n${pad}}`;
	}
	throw new Error('cannot emit ' + String(v));
}

const header = `// "Some Assembly Required", the five-level skills tutorial, one Level per page
// at /skills/tutorial/<n>/. Converted from site/design/content/tutorial-draft.md;
// every sentence of prose is the approved copy, word for word. The only
// additions are <mark data-c> wraps that tie a phrase to its callout.
//
// Level 5's Real Thing quotes goblin-scout from origin/feat/goblin-scout-rename
// at 82719bd, which has not merged. Recheck those three excerpts against main
// after the final rebase (site/design/pre-pr-checks.md).

import type { Level } from '#lib/content/tutorial.types.ts';
`;

const body = `export const TUTORIAL: Level[] = ${emit([level1, level2, level3, level4, level5], 0)};\n`;
writeFileSync(OUT, header + '\n' + body);
console.log('wrote', OUT);
