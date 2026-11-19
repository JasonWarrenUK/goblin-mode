// Generates site/design/mockups/tutorial-hybrid.body.html
// Specimen's look with Scroll story's gradual disclosure. Reads hybrid.css and hybrid.js beside it.
import { writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const SRC = import.meta.dir;
const OUT = join(SRC, '..', 'tutorial-hybrid.body.html');

const esc = (s: string): string => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// s: -1 = level 1 only (removed in 2.1), 0 = already there, 1..3 = added in step 2.1..2.3
type StepNumber = -1 | 0 | 1 | 2 | 3;
interface Line { t: string; s: StepNumber; cut?: boolean; tone?: Tone }
type Tone = 'm1' | 'm2' | 'm3' | 'mr';
const toneOf: Record<number, Tone | undefined> = { 1: 'm1', 2: 'm2', 3: 'm3' };

const skill: Line[] = [
	{ t: '---', s: 0 },
	{ t: 'name: tidy-imports', s: 0 },
	{ t: 'description: Sort the import statements at the top of a file', s: 0 },
	{ t: 'arguments: [path]', s: 0 },
	{ t: 'allowed-tools: Bash(.claude/skills/tidy-imports/scripts/sort-imports.sh:*)', s: 2 },
	{ t: '---', s: 0 },
	{ t: '', s: 0 },
	{ t: 'Tidy the imports in $path.', s: 0 },
	{ t: '', s: 0 },
	{ t: 'Sort the import statements at the top of the file', s: -1 },
	{ t: 'alphabetically, one per line. Leave everything below', s: -1 },
	{ t: 'the imports exactly as it was.', s: -1 },
	{ t: 'Read .claude/tidy-imports.log if it exists. If $path is', s: 3 },
	{ t: 'already listed there, say so before going on.', s: 3 },
	{ t: '', s: 3 },
	{ t: 'Run the script on the file, by exactly this path:', s: 1 },
	{ t: '', s: 1 },
	{ t: '```bash', s: 1 },
	{ t: '.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"', s: 1 },
	{ t: '```', s: 1 },
	{ t: '', s: 1 },
	{ t: 'It sorts the import block in place. Do not reorder any', s: 1 },
	{ t: 'lines yourself or edit the file after it runs. If the', s: 1 },
	{ t: 'script exits non-zero, report its message and stop.', s: 1 },
	{ t: '', s: 3 },
	{ t: 'The script also writes the ledger line. Never write to', s: 3 },
	{ t: '.claude/tidy-imports.log yourself.', s: 3 },
];

const script: Line[] = [
	{ t: '#!/usr/bin/env bash', s: 1 },
	{ t: '# Sort the import lines at the top of a file, in place.', s: 1 },
	{ t: 'set -euo pipefail', s: 1 },
	{ t: '', s: 1 },
	{ t: 'file="$1"', s: 1 },
	{ t: '', s: 1 },
	{ t: '# How many lines from the top start with "import "?', s: 1 },
	{ t: `count=$(awk '/^import /{n++; next} {exit} END{print n+0}' "$file")`, s: 1 },
	{ t: 'if [ "$count" -eq 0 ]; then', s: 1 },
	{ t: '\techo "no imports at the top of $file"', s: 1 },
	{ t: '\texit 0', s: 1 },
	{ t: 'fi', s: 1 },
	{ t: '', s: 1 },
	{ t: `{ head -n "$count" "$file" | sort; tail -n +"$((count + 1))" "$file"; } > "$file.tmp"`, s: 1 },
	{ t: 'mv "$file.tmp" "$file"', s: 1 },
	{ t: 'echo "sorted $count imports in $file"', s: 1 },
];

// the two lines step 2.3 adds to the script, in context
const scriptLedger: Line[] = [
	{ t: '...', s: 0, cut: true },
	{ t: 'file="$1"', s: 0 },
	{ t: 'ledger=".claude/tidy-imports.log"', s: 3 },
	{ t: '...', s: 0, cut: true },
	{ t: 'mv "$file.tmp" "$file"', s: 0 },
	{ t: `printf '%s\\t%s\\n' "$file" "$count" >> "$ledger"`, s: 3 },
	{ t: 'echo "sorted $count imports in $file"', s: 0 },
];

const real: Line[] = [
	{ t: '---', s: 0 },
	{ t: 'name: "Project: Tag Version"', s: 0 },
	{ t: 'description: "Tag the release after a merge to main, computing the next semver tag with svu"', s: 0 },
	{ t: '...', s: 0, cut: true },
	{ t: 'disable-model-invocation: true', s: 0, tone: 'mr' },
	{ t: 'allowed-tools: ["Bash(svu:*)", "Bash(git:*)", "Bash(~/.claude/library/scripts/safe-version-next.sh:*)"]', s: 0, tone: 'm2' },
	{ t: '...', s: 0, cut: true },
	{ t: '---', s: 0 },
	{ t: '', s: 0 },
	{ t: '# Tag the release with `svu`', s: 0 },
	{ t: '', s: 0 },
	{ t: '...', s: 0, cut: true },
	{ t: '', s: 0 },
	{ t: '```bash', s: 0 },
	{ t: 'TAG="$("$HOME"/.claude/library/scripts/safe-version-next.sh)" && git tag "$TAG" && git push origin "$TAG"', s: 0, tone: 'm1' },
	{ t: '```', s: 0 },
	{ t: '...', s: 0, cut: true },
];

const ledgerSample: Line[] = [
	{ t: 'src/app.ts\t6', s: 0 },
	{ t: 'src/routes/home.ts\t3', s: 0 },
];

const answerLines: Line[] = [
	{ t: `printf '%s\\t%s\\t%s\\n' "$(date +%F)" "$file" "$count" >> "$ledger"`, s: 3 },
];

const PATHS = {
	skill: '.claude/skills/tidy-imports/SKILL.md',
	// short enough that the file tab stays on one line in the reading column
	script: 'tidy-imports/scripts/sort-imports.sh',
	ledger: '.claude/tidy-imports.log',
	real: 'skills/project-tag_version/SKILL.md',
};

const at = (lines: Line[], start: string): number => {
	const i = lines.findIndex((l) => l.t.startsWith(start));
	if (i < 0) throw new Error('no line starts with ' + start);
	return i;
};

// ---------- callouts, numbered by step in the order they arrive ----------
interface Callout { label: string; step: 1 | 2 | 3 | 0; from: number; to: number; side: 'left' | 'right'; tone: Tone; html: string }
const callouts: Callout[] = [
	{ label: '2.1a', step: 1, from: at(skill, '.claude/skills'), to: at(skill, '.claude/skills'), side: 'left', tone: 'm1',
		html: `<mark>The script call</mark> takes the place of the three lines that told Claude how to sort.` },
	{ label: '2.1b', step: 1, from: at(skill, 'It sorts'), to: at(skill, 'script exits'), side: 'right', tone: 'm1',
		html: `<mark>Hands off the sorting.</mark> Claude reorders nothing itself and leaves the file alone after the script runs; a non-zero exit ends the run with the script's message.` },
	{ label: '2.2a', step: 2, from: at(skill, 'allowed-tools'), to: at(skill, 'allowed-tools'), side: 'left', tone: 'm2',
		html: `<mark><code>allowed-tools</code></mark> approves Bash calls that start with this path for as long as the skill runs. The <code>:*</code> covers whatever arguments follow.` },
	{ label: '2.3a', step: 3, from: at(skill, 'Read .claude'), to: at(skill, 'already listed'), side: 'right', tone: 'm3',
		html: `<mark>Read the ledger first</mark>, so a second run on the same file says so before it starts.` },
	{ label: '2.3b', step: 3, from: at(skill, 'The script also'), to: at(skill, '.claude/tidy-imports.log yourself'), side: 'left', tone: 'm3',
		html: `<mark>The script writes the ledger line</mark>, so it comes out the same every time and needs no permission beyond 2.2a.` },
];

const realCallouts: Callout[] = [
	{ label: 'R.a', step: 0, from: at(real, 'disable-model'), to: at(real, 'disable-model'), side: 'right', tone: 'mr',
		html: `<mark><code>disable-model-invocation</code></mark> stops Claude starting the skill on its own, so it runs only when a person types its slash command after a merge has landed, because a pushed tag is hard to take back.` },
	{ label: 'R.b', step: 0, from: at(real, 'allowed-tools'), to: at(real, 'allowed-tools'), side: 'right', tone: 'm2',
		html: `<mark><code>allowed-tools</code></mark> names <code>safe-version-next.sh</code> by its full path, the move from 2.2a, beside <code>svu</code> and <code>git</code> for reading history and pushing one tag.` },
	{ label: 'R.c', step: 0, from: at(real, 'TAG='), to: at(real, 'TAG='), side: 'right', tone: 'm1',
		html: `<mark>The body runs the script</mark> and tags whatever it prints, so Claude never works out the next version itself.` },
];

// ---------- code blocks ----------
interface LineView { show: boolean; cls: string[]; attrs: string[] }
function codeBlock(lines: Line[], label: string, view: (l: Line, i: number) => LineView, extra = ''): string {
	const spans = lines.map((l, i) => {
		const v = view(l, i);
		if (!v.show) return '';
		const cls = ['ln', ...v.cls];
		if (l.cut) cls.push('cut');
		return `<span class="${cls.join(' ')}"${v.attrs.length ? ' ' + v.attrs.join(' ') : ''}>${esc(l.t)}</span>`;
	}).join('');
	return `<div class="file${extra ? ' ' + extra : ''}"><p class="fname">${esc(label)}</p><pre class="code"><code>${spans}</code></pre></div>`;
}

// a file as it stands after step n: that step's lines marked new, its callouts' labels in the gutter
function snapshot(lines: Line[], label: string, n: number, notes: Callout[] = [], extra = '', strong = true): string {
	return codeBlock(lines, label, (l, i) => {
		const show = l.s === 0 || (l.s > 0 && l.s <= n) || (l.s === -1 && n === 0);
		const cls: string[] = [];
		const attrs: string[] = [];
		const tone = l.tone ?? toneOf[l.s];
		if (tone && show) cls.push(tone);
		if (l.s > 0 && l.s === n) cls.push(...(strong ? ['cur', 'new'] : ['new']));
		const note = notes.find((c) => c.from === i);
		if (note) attrs.push(`data-label="${note.label}"`);
		return { show, cls, attrs };
	}, extra);
}

const coItem = (c: Callout, live: boolean): string => {
	const data = live ? ` data-s="${c.step}" data-from="${c.from}" data-to="${c.to}" data-side="${c.side}" data-label="${c.label}"` : '';
	return `<li class="co ${c.tone}"${data}><p><span class="lab">${c.label}</span> ${c.html}</p></li>`;
};

// ---------- copy ----------
const TITLE = 'Give It a Script and a Ledger';
const lede = `At level 1, <code>tidy-imports</code> was one file that asked Claude to sort a file's imports by hand. This level gives the sorting to a script, lets that one script run without a prompt and keeps a ledger of every file it touches.`;

const ref = (label: string): string => `<span class="ref">${label}</span>`;

const steps: { n: 1 | 2 | 3; title: string; body: string }[] = [
	{
		n: 1,
		title: 'Give It a Script',
		body: `<p>At level 1, Claude sorted the imports itself, and a model asked to reorder lines will now and then reflow one it was told to leave alone. A script does the same thing every time and costs no tokens, so the sorting moves into <code>scripts/sort-imports.sh</code> in the skill's folder.</p>
		<p class="also">The new script, whole:</p>
		${snapshot(script, PATHS.script, 1, [], 'small', false)}
		<p>Make the script executable once with <code>chmod +x</code>. Then replace the three sorting lines in SKILL.md with <mark class="m1">the script call</mark> ${ref('2.1a')} and tell Claude to keep <mark class="m1">its hands off the sorting</mark> ${ref('2.1b')}.</p>`,
	},
	{
		n: 2,
		title: 'Scope the Tool',
		body: `<p>Running a script is a Bash call, and Claude asks before each one unless the skill approves it. <mark class="m2"><code>allowed-tools</code></mark> ${ref('2.2a')} approves calls for as long as the skill runs; naming the script's full path, with <code>:*</code> for whatever arguments follow, approves that one script and no other command.</p>
		<p>The rule matches the start of the command, so <mark class="m1">the script call</mark> from 2.1a uses exactly that path, with no <code>bash</code> or <code>./</code> in front.</p>`,
	},
	{
		n: 3,
		title: 'Keep a Ledger',
		body: `<p>A ledger lets a later run say what an earlier one touched. The script appends one line per file to <code>.claude/tidy-imports.log</code>, the path and how many imports it sorted, so writing the ledger needs no extra permission.</p>
		<p class="also">The script's two new lines:</p>
		${snapshot(scriptLedger, PATHS.script, 3, [], 'small')}
		<div class="logslip">${snapshot(ledgerSample, PATHS.ledger + ' after two runs', 0, [], 'small')}</div>
		<p>SKILL.md tells Claude to <mark class="m3">read the ledger first</mark> ${ref('2.3a')} and to <mark class="m3">leave the writing to the script</mark> ${ref('2.3b')}.</p>`,
	},
];

const stepHtml = steps.map((s) => {
	const notes = callouts.filter((c) => c.step === s.n);
	return `<article class="sheet step" id="step-2-${s.n}" data-n="${s.n}" data-title="${s.title}" aria-labelledby="step-2-${s.n}-h">
	<h2 class="step-h" id="step-2-${s.n}-h"><button type="button" class="step-btn" aria-controls="spec"><span class="snum">2.${s.n}</span> ${s.title}</button></h2>
	${s.body}
	<div class="after-step">
		<p class="snap-title">SKILL.md after step 2.${s.n}</p>
		${snapshot(skill, PATHS.skill, s.n, notes)}
		<ol class="co-list" aria-label="Notes for step 2.${s.n}">${notes.map((c) => coItem(c, false)).join('')}</ol>
	</div>
</article>`;
}).join('\n');

// the live specimen: every line present, the script decides which show
const liveCode = codeBlock(skill, PATHS.skill, (l, i) => {
	const cls: string[] = [];
	const tone = toneOf[l.s];
	if (tone) cls.push(tone);
	const attrs = [`data-i="${i}"`, `data-s="${l.s}"`];
	if (l.s > 0) attrs.push('hidden');
	return { show: true, cls, attrs };
});

const realCode = codeBlock(real, PATHS.real, (l, i) => {
	const cls: string[] = [];
	const attrs = [`data-i="${i}"`];
	if (l.tone) cls.push(l.tone, 'cur');
	const note = realCallouts.find((c) => c.from === i);
	if (note) attrs.push(`data-label="${note.label}"`);
	return { show: true, cls, attrs };
});

const realIntro = `<p><code>project-tag_version</code> lives in this repository and tags a release after a merge to main. Its first marked line, <mark class="mr"><code>disable-model-invocation</code></mark> ${ref('R.a')}, is a move <code>tidy-imports</code> does not have yet. The other two are this level's moves: <mark class="m2"><code>allowed-tools</code> names a script by its path</mark> ${ref('R.b')} and <mark class="m1">the body runs that script</mark> ${ref('R.c')} for the part that must come out the same every time.</p>`;

const exercise = `<aside class="slip torn exercise" aria-labelledby="ex-h">
	<h2 id="ex-h">Try it: make the ledger line include the date</h2>
	<p>Change the script so each ledger line starts with the day it was written. Then change the ledger paragraph in SKILL.md so Claude says when a file was last tidied.</p>
	<details>
		<summary>Show the answer</summary>
		<p>In <code>sort-imports.sh</code>, put the date in front of the path:</p>
		${snapshot(answerLines, PATHS.script, 3)}
		<p><code>date +%F</code> prints the date as <code>2026-11-19</code>, which sorts in date order as plain text. In SKILL.md, the second ledger line becomes: <q>already listed there, say on which date it was last tidied.</q></p>
	</details>
</aside>`;

const css = readFileSync(join(SRC, 'hybrid.css'), 'utf8');
const js = readFileSync(join(SRC, 'hybrid.js'), 'utf8');

const html = `<style>
${css.trim()}
</style>

<main class="desk">
<header class="sheet lvl-head">
	<p class="kicker">Some Assembly Required · Level 2 of 5</p>
	<h1>${TITLE}</h1>
	<p class="lede">${lede}</p>
	<p class="key">Colour key: <mark class="m1">2.1 Give It a Script</mark> <mark class="m2">2.2 Scope the Tool</mark> <mark class="m3">2.3 Keep a Ledger</mark></p>
	<p class="how">Scroll and the sheet builds SKILL.md one step at a time, pinning each step's notes. A step's heading, the arrow keys or j and k jump between steps.</p>
</header>

<section class="tut" id="tut" data-view="steps" data-step="0" aria-label="Steps 2.1 to 2.3">
	<div class="viewbar">
		<div class="switch" role="group" aria-label="Show">
			<button type="button" data-view="steps" aria-pressed="true">Steps</button>
			<button type="button" data-view="file" aria-pressed="false">File</button>
		</div>
		<p class="viewstate" aria-live="polite">Level 1 file</p>
	</div>
	<div class="spread">
		<div class="steps">
${stepHtml}
		</div>
		<aside class="sheet specimen" id="spec" aria-labelledby="spec-title">
			<div class="spec-top">
				<h2 class="spec-title" id="spec-title">Specimen: SKILL.md</h2>
				<p class="spec-state">Where level 1 left it</p>
			</div>
			<div class="stage">
				${liveCode}
				<ol class="callouts" aria-label="Notes on the file">${callouts.map((c) => coItem(c, true)).join('')}</ol>
				<svg class="leaders" aria-hidden="true" focusable="false"></svg>
			</div>
		</aside>
	</div>
</section>

<article class="sheet alt real" aria-labelledby="real-h">
	<h2 id="real-h">The Real Thing</h2>
	${realIntro}
	<div class="stage">
		${realCode}
		<ol class="callouts" aria-label="Notes on project-tag_version">${realCallouts.map((c) => coItem(c, true)).join('')}</ol>
		<svg class="leaders" aria-hidden="true" focusable="false"></svg>
	</div>
</article>

${exercise}
</main>

<script>
${js.trim()}
</script>
`;
writeFileSync(OUT, html);
console.log('wrote', OUT, html.length);
