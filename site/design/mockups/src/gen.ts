// Generates site/design/mockups/tutorial-directions.body.html
import { writeFileSync, readFileSync } from 'node:fs';

const OUT = '/Users/jasonwarren/.claude/.claude/worktrees/site-pages-site/site/design/mockups/tutorial-directions.body.html';
const DIR = '/private/tmp/claude-501/-Users-jasonwarren--claude--claude-worktrees-site-pages-site/a26c18da-b687-4248-9e1d-c49e512256b9/scratchpad/';

const esc = (s: string): string => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// step keys: '1' = level 1, 'L1' = level 1 only (removed in 2.1), '2.1' .. '2.3'
type Step = '1' | 'L1' | '2.1' | '2.2' | '2.3';
interface Line { t: string; s: Step; mark?: string; cut?: boolean }
const order: Record<Step, number> = { '1': 0, 'L1': -1, '2.1': 1, '2.2': 2, '2.3': 3 };

const skill: Line[] = [
	{ t: '---', s: '1' },
	{ t: 'name: tidy-imports', s: '1' },
	{ t: 'description: Sort the import statements at the top of a file', s: '1' },
	{ t: 'arguments: [path]', s: '1' },
	{ t: 'allowed-tools: Bash(.claude/skills/tidy-imports/scripts/sort-imports.sh:*)', s: '2.2', mark: '①' },
	{ t: '---', s: '1' },
	{ t: '', s: '1' },
	{ t: 'Tidy the imports in $path.', s: '1' },
	{ t: '', s: '1' },
	{ t: 'Sort the import statements at the top of the file', s: 'L1' },
	{ t: 'alphabetically, one per line. Leave everything below', s: 'L1' },
	{ t: 'the imports exactly as it was.', s: 'L1' },
	{ t: 'Read .claude/tidy-imports.log if it exists. If $path is', s: '2.3' },
	{ t: 'already listed there, say so before going on.', s: '2.3' },
	{ t: '', s: '2.3' },
	{ t: 'Run the script on the file, by exactly this path:', s: '2.1' },
	{ t: '', s: '2.1' },
	{ t: '```bash', s: '2.1' },
	{ t: '.claude/skills/tidy-imports/scripts/sort-imports.sh "$path"', s: '2.1', mark: '②' },
	{ t: '```', s: '2.1' },
	{ t: '', s: '2.1' },
	{ t: 'It sorts the import block in place. Do not reorder any', s: '2.1' },
	{ t: 'lines yourself or edit the file after it runs. If the', s: '2.1' },
	{ t: 'script exits non-zero, report its message and stop.', s: '2.1' },
	{ t: '', s: '2.3' },
	{ t: 'The script also writes the ledger line. Never write to', s: '2.3' },
	{ t: '.claude/tidy-imports.log yourself.', s: '2.3' },
];

const script: Line[] = [
	{ t: '#!/usr/bin/env bash', s: '2.1' },
	{ t: '# Sort the import lines at the top of a file, in place.', s: '2.1' },
	{ t: 'set -euo pipefail', s: '2.1' },
	{ t: '', s: '2.1' },
	{ t: 'file="$1"', s: '2.1' },
	{ t: 'ledger=".claude/tidy-imports.log"', s: '2.3' },
	{ t: '', s: '2.1' },
	{ t: '# How many lines from the top start with "import "?', s: '2.1' },
	{ t: `count=$(awk '/^import /{n++; next} {exit} END{print n+0}' "$file")`, s: '2.1' },
	{ t: 'if [ "$count" -eq 0 ]; then', s: '2.1' },
	{ t: '\techo "no imports at the top of $file"', s: '2.1' },
	{ t: '\texit 0', s: '2.1' },
	{ t: 'fi', s: '2.1' },
	{ t: '', s: '2.1' },
	{ t: `{ head -n "$count" "$file" | sort; tail -n +"$((count + 1))" "$file"; } > "$file.tmp"`, s: '2.1' },
	{ t: 'mv "$file.tmp" "$file"', s: '2.1' },
	{ t: `printf '%s\\t%s\\n' "$file" "$count" >> "$ledger"`, s: '2.3' },
	{ t: 'echo "sorted $count imports in $file"', s: '2.1' },
];

const real: Line[] = [
	{ t: '---', s: '1' },
	{ t: 'name: "Project: Tag Version"', s: '1' },
	{ t: 'description: "Tag the release after a merge to main, computing the next semver tag with svu"', s: '1' },
	{ t: '...', s: '1', cut: true },
	{ t: 'disable-model-invocation: true', s: '1', mark: '③' },
	{ t: 'allowed-tools: ["Bash(svu:*)", "Bash(git:*)", "Bash(~/.claude/library/scripts/safe-version-next.sh:*)"]', s: '1', mark: '①' },
	{ t: '...', s: '1', cut: true },
	{ t: '---', s: '1' },
	{ t: '', s: '1' },
	{ t: '# Tag the release with `svu`', s: '1' },
	{ t: '', s: '1' },
	{ t: '...', s: '1', cut: true },
	{ t: '', s: '1' },
	{ t: '```bash', s: '1' },
	{ t: 'TAG="$("$HOME"/.claude/library/scripts/safe-version-next.sh)" && git tag "$TAG" && git push origin "$TAG"', s: '1', mark: '②' },
	{ t: '```', s: '1' },
	{ t: '...', s: '1', cut: true },
];

const ledgerSample: Line[] = [
	{ t: 'src/app.ts\t6', s: '1' },
	{ t: 'src/routes/home.ts\t3', s: '1' },
];

const answerLines: Line[] = [
	{ t: `printf '%s\\t%s\\t%s\\n' "$(date +%F)" "$file" "$count" >> "$ledger"`, s: '2.3' },
];

const PATHS = {
	skill: '.claude/skills/tidy-imports/SKILL.md',
	script: '.claude/skills/tidy-imports/scripts/sort-imports.sh',
	ledger: '.claude/tidy-imports.log',
	real: 'skills/project-tag_version/SKILL.md',
};

interface CodeOpts {
	upto?: number; // show lines up to this step order (default: all level-2 lines)
	add?: Step | 'all-new'; // which lines get the + mark
	tagged?: boolean; // gutter shows the step number
	marks?: boolean; // gutter shows ①②③
	spec?: boolean; // specimen colour classes by step
	pinned?: boolean; // emit data-o / data-hl for the scroll script
	label?: string;
	cls?: string;
}
const specClass: Record<string, string> = { '2.1': 'm1', '2.2': 'm2', '2.3': 'm3' };
const specBadge: Record<number, string> = {};

function code(lines: Line[], o: CodeOpts = {}): string {
	const upto = o.upto ?? 3;
	const spans = lines
		.filter((l) => o.pinned || (l.s === 'L1' ? upto === 0 : order[l.s] <= upto))
		.map((l, i) => {
			const c = ['ln'];
			const attrs: string[] = [];
			const isAdd = o.add === 'all-new' ? order[l.s] >= 1 : o.add !== undefined && l.s === o.add;
			if (isAdd && !o.pinned) c.push('add');
			if (o.tagged && order[l.s] >= 1) attrs.push(`data-step="${l.s}"`);
			if (l.cut) c.push('cut');
			if (o.marks && l.mark) { c.push('mk'); attrs.push(`data-mark="${l.mark}"`); }
			if (o.spec && specClass[l.s]) c.push(specClass[l.s]);
			if (o.spec && specBadge[i] && false) attrs.push('');
			if (o.pinned) {
				attrs.push(`data-o="${order[l.s]}"`);
				attrs.push(`data-hl="${l.mark && !['2.1', '2.2', '2.3'].includes(l.s) ? l.mark : l.s}"`);
				if (l.s === 'L1') attrs.push('hidden');
			}
			return `<span class="${c.join(' ')}"${attrs.length ? ' ' + attrs.join(' ') : ''}>${esc(l.t)}</span>`;
		})
		.join('');
	const label = o.label ? `<p class="fname">${esc(o.label)}</p>` : '';
	return `<div class="file${o.cls ? ' ' + o.cls : ''}">${label}<pre class="code${o.tagged ? ' tagged' : ''}${o.marks ? ' marked' : ''}"><code>${spans}</code></pre></div>`;
}

// ---------- shared copy ----------
const TITLE = 'Give It a Script and a Ledger';
const lede = `At level 1, <code>tidy-imports</code> was one file that asked Claude to sort a file's imports by hand. This level gives the sorting to a script, lets that one script run without a prompt and keeps a ledger of every file it touches.`;

const steps = {
	'2.1': {
		title: 'Give It a Script',
		body: `<p>At level 1, Claude sorted the imports itself, and a model asked to reorder lines will now and then reflow one it was told to leave alone. A script does the same thing every time and costs no tokens, so the sorting moves into <code>scripts/sort-imports.sh</code> in the skill's folder.</p>
<p>Make the script executable once with <code>chmod +x</code>, then replace the three sorting lines in SKILL.md with an instruction to run it.</p>`,
	},
	'2.2': {
		title: 'Scope the Tool',
		body: `<p>Running a script is a Bash call, and Claude asks before each one unless the skill approves it. <code>allowed-tools</code> approves calls for as long as the skill runs; naming the script's full path, with <code>:*</code> for whatever arguments follow, approves that one script and no other command.</p>
<p>The rule matches the start of the command, so the body calls the script by exactly that path, with no <code>bash</code> or <code>./</code> in front.</p>`,
	},
	'2.3': {
		title: 'Keep a Ledger',
		body: `<p>A ledger lets a later run say what an earlier one touched. The script appends one line per file to <code>.claude/tidy-imports.log</code>, the path and how many imports it sorted, so writing the ledger needs no extra permission.</p>
<p>SKILL.md tells Claude to read the ledger first and to leave the writing to the script.</p>`,
	},
} as const;

const realIntro = `<p><code>project-tag_version</code> lives in this repository and tags a release after a merge to main. It makes two of this level's three moves: a script does the part that must come out the same every time, and <code>allowed-tools</code> names that script by its path. Its third marked line is one <code>tidy-imports</code> does not have yet.</p>`;
const realNotes: [string, string][] = [
	['①', `<code>allowed-tools</code> names <code>safe-version-next.sh</code> by its full path, the move from step 2.2, beside <code>svu</code> and <code>git</code> for reading history and pushing one tag.`],
	['②', `The body never asks Claude to work out the next version: it runs the script and tags whatever the script prints.`],
	['③', `<code>disable-model-invocation: true</code> stops Claude starting the skill on its own; a person types its slash command once a merge has landed, because a pushed tag is hard to take back.`],
];
const realList = (cls = ''): string => `<ol class="marks${cls ? ' ' + cls : ''}">${realNotes.map(([g, t]) => `<li><span class="glyph" aria-hidden="true">${g}</span><span class="vh">Marker ${g}: </span>${t}</li>`).join('')}</ol>`;

const ledgerSlip = (): string => `<div class="logslip">${code(ledgerSample, { label: PATHS.ledger + ' after two runs', cls: 'small' })}</div>`;

function exercise(prefix: string): string {
	return `<aside class="slip torn exercise" aria-labelledby="${prefix}-ex">
	<h3 id="${prefix}-ex">Try it: make the ledger line include the date</h3>
	<p>Change the script so each ledger line starts with the day it was written. Then change the ledger paragraph in SKILL.md so Claude says when a file was last tidied.</p>
	<details>
		<summary>Show the answer</summary>
		<p>In <code>sort-imports.sh</code>, put the date in front of the path:</p>
		${code(answerLines, { add: '2.3' })}
		<p><code>date +%F</code> prints the date as <code>2026-11-19</code>, which sorts in date order as plain text. In SKILL.md, the second ledger line becomes: <q>already listed there, say on which date it was last tidied.</q></p>
	</details>
</aside>`;
}

const levelNames = ['One File, One Job', TITLE, 'Split the Instructions', 'Let It Ask First', 'Ship It as a Plugin'];

// ---------- 1. ledger ----------
function mockLedger(): string {
	const stepArticles = (['2.1', '2.2', '2.3'] as const).map((k) => {
		let extra = '';
		if (k === '2.1') extra = `<p class="also">The new script, whole:</p>${code(script, { upto: 1, add: 'all-new', label: PATHS.script })}`;
		if (k === '2.3') extra = `<p class="also">The script after this step, with the two ledger lines marked:</p>${code(script, { upto: 3, add: '2.3', label: PATHS.script })}${ledgerSlip()}`;
		return `<article class="sheet step" data-step="${k}" aria-labelledby="l-s${k.replace('.', '')}">
	<h3 id="l-s${k.replace('.', '')}"><span class="snum">${k}</span> ${steps[k].title}</h3>
	${steps[k].body}
	<p class="pointer">Its lines in SKILL.md are marked <span class="tag">+ ${k}</span> on the file sheet.</p>
	${extra}
</article>`;
	}).join('\n');

	return `<section class="mockup" id="ledger" aria-labelledby="ledger-cap">
<p class="caption" id="ledger-cap"><b>1 · Workshop ledger.</b> Steps beside a sticky file sheet, the code column pattern from Stripe's API reference.</p>
<div class="levelbar">
	<p class="lvl-count">Level 2 of 5</p>
	<ol class="ltabs" aria-label="Levels">
		${levelNames.map((n, i) => i === 1 ? `<li><a href="#ledger" aria-current="step" title="${n}">${i + 1}</a></li>` : `<li><a href="#ledger" title="${n}">${i + 1}</a></li>`).join('')}
	</ol>
</div>
<header class="sheet lvl-head">
	<p class="kicker">Some Assembly Required</p>
	<h2>Level 2: ${TITLE}</h2>
	<p class="lede">${lede}</p>
	<nav class="prevnext" aria-label="Neighbouring levels"><a href="#ledger">← Level 1: ${levelNames[0]}</a><a href="#ledger">Level 3: ${levelNames[2]} →</a></nav>
</header>
<div class="spread">
	<div class="steps">
${stepArticles}
	</div>
	<aside class="filesheet" aria-labelledby="l-file" tabindex="0">
		<h3 id="l-file">SKILL.md, as of Level 2</h3>
		<p class="legend">A line marked <span class="tag">+ 2.1</span> arrived in step 2.1. Hover over a step to light up its lines.</p>
		${code(skill, { upto: 3, add: 'all-new', tagged: true, label: PATHS.skill })}
	</aside>
</div>
<section class="real" data-show="ours" aria-labelledby="l-real">
	<h3 id="l-real" class="sec">The Real Thing</h3>
	${realIntro}
	<div class="realtabs" role="group" aria-label="Which file to show">
		<button type="button" data-show="yours" aria-pressed="false">tidy-imports</button>
		<button type="button" data-show="ours" aria-pressed="true">project-tag_version</button>
	</div>
	<div class="pair">
		<div class="sheet alt panel yours">
			<h4>Invented: <code>tidy-imports</code></h4>
			${code(skill, { upto: 3, marks: true, label: PATHS.skill })}
			<p class="note">Markers ① and ② sit on the same two moves as the real file.</p>
		</div>
		<div class="sheet panel ours">
			<h4>Real: <code>project-tag_version</code></h4>
			${code(real, { marks: true, label: PATHS.real })}
			${realList()}
		</div>
	</div>
</section>
${exercise('l')}
</section>`;
}

// ---------- 2. scroll ----------
interface Beat { file: 'skill' | 'script' | 'real'; upto: number; hl: string; h: string; body: string; after?: string }
function mockScroll(): string {
	const beats: Beat[] = [
		{ file: 'skill', upto: 0, hl: 'none', h: 'Where Level 1 Left It', body: `<p>${lede}</p><p>Here is the whole of level 1: three lines of frontmatter and a body that does the sorting in prose.</p>`, after: code(skill, { upto: 0, label: PATHS.skill }) },
		{ file: 'script', upto: 1, hl: '2.1', h: '<span class="snum">2.1</span> Give It a Script', body: steps['2.1'].body.split('</p>')[0] + '</p>' },
		{ file: 'skill', upto: 1, hl: '2.1', h: '<span class="snum">2.1</span> Point SKILL.md at It', body: steps['2.1'].body.split('</p>').slice(1).join('</p>'), after: code(script, { upto: 1, add: 'all-new', label: PATHS.script }) + code(skill, { upto: 1, add: '2.1', label: PATHS.skill }) },
		{ file: 'skill', upto: 2, hl: '2.2', h: '<span class="snum">2.2</span> Scope the Tool', body: steps['2.2'].body, after: code(skill, { upto: 2, add: '2.2', label: PATHS.skill }) },
		{ file: 'script', upto: 3, hl: '2.3', h: '<span class="snum">2.3</span> Keep a Ledger', body: steps['2.3'].body.split('</p>')[0] + '</p>' + ledgerSlip() },
		{ file: 'skill', upto: 3, hl: '2.3', h: '<span class="snum">2.3</span> Read the Ledger First', body: steps['2.3'].body.split('</p>').slice(1).join('</p>'), after: code(script, { upto: 3, add: '2.3', label: PATHS.script }) + code(skill, { upto: 3, add: '2.3', label: PATHS.skill }) },
		{ file: 'real', upto: 3, hl: '①', h: '<span class="snum">①</span> The Real Thing', body: realIntro + `<p>${realNotes[0][1]}</p>` },
		{ file: 'real', upto: 3, hl: '②', h: '<span class="snum">②</span> The Script Call', body: `<p>${realNotes[1][1]}</p>` },
		{ file: 'real', upto: 3, hl: '③', h: '<span class="snum">③</span> Started by Hand', body: `<p>${realNotes[2][1]}</p>`, after: code(real, { marks: true, label: PATHS.real }) },
	];
	const beatHtml = beats.map((b, i) => `<article class="sheet beat${i % 2 ? ' alt' : ''}" data-file="${b.file}" data-upto="${b.upto}" data-hl="${b.hl}" aria-labelledby="s-b${i}">
	<h3 id="s-b${i}">${b.h}</h3>
	${b.body}
	<button type="button" class="show" aria-pressed="false" aria-describedby="s-b${i}">Show in the file</button>
</article>${b.after ? `\n<div class="after-step">${b.after}</div>` : ''}`).join('\n');

	return `<section class="mockup" id="scroll" aria-labelledby="scroll-cap">
<p class="caption" id="scroll-cap"><b>2 · Scroll story.</b> The file stays pinned and changes as each step scrolls past, after Code Hike's scrollycoding.</p>
<header class="sheet lvl-head">
	<p class="kicker">Some Assembly Required · Level 2 of 5</p>
	<h2>${TITLE}</h2>
</header>
<div class="story">
	<div class="beats">
${beatHtml}
	</div>
	<aside class="pinned" aria-label="The file as it stands at the highlighted step" data-file="skill">
		<div class="pf" data-file="skill">${code(skill, { pinned: true, label: PATHS.skill })}</div>
		<div class="pf" data-file="script" hidden>${code(script, { pinned: true, label: PATHS.script })}</div>
		<div class="pf" data-file="real" hidden>${code(real, { pinned: true, marks: true, label: PATHS.real })}</div>
	</aside>
</div>
${exercise('s')}
</section>`;
}

// ---------- 3. specimen ----------
function mockSpecimen(): string {
	// callouts: at = line index in the level-2 file
	const idx = (pred: (l: Line) => boolean): number => skill.filter((l) => l.s !== 'L1').findIndex(pred);
	const callouts = [
		{ n: 1, side: 'left', at: idx((l) => l.t.startsWith('allowed-tools')), m: 'm2', html: `<b>2.2 Scope the tool.</b> <mark class="m2">allowed-tools</mark> approves Bash calls to this one script for as long as the skill runs, so Claude stops asking. The <code>:*</code> covers whatever arguments follow.` },
		{ n: 2, side: 'right', at: idx((l) => l.t.startsWith('Read .claude')), m: 'm3', html: `<b>2.3 Keep a ledger.</b> Claude <mark class="m3">reads the ledger first</mark>, so a later run can say which files an earlier one touched.` },
		{ n: 3, side: 'left', at: idx((l) => l.t.startsWith('.claude/skills')), m: 'm1', html: `<b>2.1 Give it a script.</b> <mark class="m1">The script call</mark> replaces the three lines that told Claude how to sort. It uses exactly the path in callout 1, because the rule matches the start of the command.` },
		{ n: 4, side: 'right', at: idx((l) => l.t.startsWith('The script also')), m: 'm3', html: `<b>2.3, continued.</b> The script <mark class="m3">writes the ledger line</mark> itself, so writing it needs no extra permission and comes out the same every time.` },
	];
	const specCode = (() => {
		const lines = skill.filter((l) => l.s !== 'L1');
		const spans = lines.map((l, i) => {
			const c = ['ln'];
			if (specClass[l.s]) c.push(specClass[l.s]);
			const co = callouts.find((x) => x.at === i);
			return `<span class="${c.join(' ')}"${co ? ` data-n="${co.n}"` : ''}>${esc(l.t)}</span>`;
		}).join('');
		return `<div class="file"><p class="fname">${PATHS.skill}</p><pre class="code spec"><code>${spans}</code></pre></div>`;
	})();
	const scriptSpec = (() => {
		const spans = script.map((l) => `<span class="ln ${specClass[l.s] ?? ''}"${l.t.startsWith('printf') ? ' data-n="6"' : ''}${l.t.startsWith('#!') ? ' data-n="5"' : ''}>${esc(l.t)}</span>`).join('');
		return `<div class="file"><p class="fname">${PATHS.script}</p><pre class="code spec"><code>${spans}</code></pre></div>`;
	})();

	return `<section class="mockup" id="specimen" aria-labelledby="specimen-cap">
<p class="caption" id="specimen-cap"><b>3 · Specimen sheets.</b> One annotated exhibit with colour-matched notes, after Bartosz Ciechanowski's explainers and Tailwind's code callouts.</p>
<article class="sheet specimen" aria-labelledby="p-title">
	<header class="spec-head">
		<p class="kicker">Some Assembly Required · Specimen 2 of 5</p>
		<h2 id="p-title">${TITLE}</h2>
		<p class="lede">${lede}</p>
		<p class="key">Colour key: <mark class="m1">2.1 Give It a Script</mark> <mark class="m2">2.2 Scope the Tool</mark> <mark class="m3">2.3 Keep a Ledger</mark></p>
	</header>
	<div class="stage">
		${specCode}
		<ol class="callouts">
			${callouts.map((c) => `<li class="co ${c.side} ${c.m}" style="--at:${c.at}"><span class="badge ${c.m}" aria-hidden="true">${c.n}</span><span class="vh">Note ${c.n}: </span>${c.html}</li>`).join('\n\t\t\t')}
		</ol>
	</div>
	<div class="stage2">
		${scriptSpec}
		<ol class="callouts flat" start="5">
			<li class="co"><span class="badge m1" aria-hidden="true">5</span><span class="vh">Note 5: </span><b>2.1.</b> <mark class="m1">The whole script is new.</mark> It counts the <code>import</code> lines at the top, sorts just those and leaves the rest of the file alone. Make it executable once with <code>chmod +x</code>.</li>
			<li class="co"><span class="badge m3" aria-hidden="true">6</span><span class="vh">Note 6: </span><b>2.3.</b> Two lines give the script <mark class="m3">its ledger</mark>: where it lives, then one line per file tidied, the path and the count.</li>
		</ol>
		${ledgerSlip()}
	</div>
</article>
<article class="sheet alt specimen small-sheet" aria-labelledby="p-real">
	<h3 id="p-real" class="sec">The Real Thing</h3>
	${realIntro}
	<div class="realgrid">
		${code(real, { marks: true, label: PATHS.real })}
		${realList()}
	</div>
</article>
${exercise('p')}
</section>`;
}

// ---------- 4. zine ----------
const svg = `<svg class="zine-svg" viewBox="0 0 600 640" role="img" aria-labelledby="z-svg-title z-svg-desc">
	<title id="z-svg-title">Level 2: give it a helper and a memory</title>
	<desc id="z-svg-desc">A sketched skill file with a small script taped to its side and a ledger page clipped behind it.</desc>
	<defs>
		<filter id="z-rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7"/><feDisplacementMap in="SourceGraphic" scale="3.5"/></filter>
	</defs>
	<g transform="rotate(-8 170 210)">
		<path class="z-ledger z-edge" filter="url(#z-rough)" d="M64 78 C120 74 210 72 282 70 C286 160 290 260 292 352 C220 356 140 358 70 362 C68 270 66 170 64 78 Z"/>
		<path class="z-rule" d="M84 130 H272 M84 162 H272 M84 194 H272 M84 226 H272 M84 258 H272 M84 290 H272 M84 322 H272"/>
		<path class="z-scrawl" d="M90 124 c10 -6 20 4 30 -2 s20 4 30 -1 M176 124 h18 M90 156 c12 -5 22 4 34 -2 s18 3 26 0 M176 156 h12 M90 188 c10 -4 20 3 28 -1 M176 188 h16"/>
		<path class="z-clip z-edge" d="M146 52 h66 l-4 34 h-58 z"/>
		<path class="z-wire" d="M160 58 c0 -22 38 -22 38 0"/>
		<text class="z-letter z-small" x="84" y="344">ledger</text>
	</g>
	<g transform="rotate(2.5 310 220)">
		<path class="z-skill z-edge" filter="url(#z-rough)" d="M196 44 C260 42 330 40 392 40 L426 74 C428 170 430 280 432 384 C360 388 270 390 200 392 C198 290 196 160 196 44 Z"/>
		<path class="z-fold z-edge" d="M392 40 C393 52 394 64 394 76 C406 76 416 75 426 74"/>
		<text class="z-letter z-title" x="222" y="98">SKILL.md</text>
		<path class="z-front" d="M222 122 h40 M222 146 h120 M222 170 h150 M222 194 h96 M222 218 h40"/>
		<path class="z-body" d="M222 256 c20 -4 40 4 60 0 s40 4 60 -1 s30 3 50 0 M222 284 c18 -4 38 4 58 0 s42 3 60 -1 M222 312 c20 -3 40 4 60 0 s30 3 46 0 M222 340 c16 -3 30 3 48 0"/>
	</g>
	<g transform="rotate(9 480 250)">
		<rect class="z-script z-edge2" x="408" y="196" width="160" height="112" rx="6"/>
		<text class="z-code" x="424" y="232">#!/bin/sh</text>
		<text class="z-code" x="424" y="260">sort | tee</text>
		<text class="z-code" x="424" y="288">&gt;&gt; log</text>
		<rect class="z-tape" x="388" y="182" width="58" height="22" transform="rotate(-32 417 193)"/>
		<rect class="z-tape" x="390" y="298" width="56" height="22" transform="rotate(28 418 309)"/>
	</g>
	<path class="z-arrow" d="M540 120 C548 140 540 160 520 182 M508 172 L520 184 L532 170"/>
	<text class="z-letter z-tag" x="440" y="104">helper</text>
	<path class="z-arrow" d="M58 404 C46 380 50 352 62 330 M50 342 L62 328 L74 340"/>
	<text class="z-letter z-tag" x="12" y="446">memory</text>
	<text class="z-letter z-cap" x="300" y="510" text-anchor="middle">level 2:</text>
	<text class="z-letter z-cap" x="300" y="568" text-anchor="middle">give it a helper</text>
	<text class="z-letter z-cap" x="300" y="626" text-anchor="middle">and a memory</text>
</svg>`;

function mockZine(): string {
	const page = (n: number, inner: string, cls = ''): string => `<article class="sheet zpage${n % 2 ? ' alt' : ''}${cls ? ' ' + cls : ''}">${inner}<p class="folio" aria-hidden="true">p. ${n}</p></article>`;
	return `<section class="mockup" id="zine" aria-labelledby="zine-cap">
<p class="caption" id="zine-cap"><b>4 · Zine pages.</b> One drawn panel opens the level and plain pages follow, after Julia Evans's zines.</p>
<div class="zine">
<figure class="sheet panel-fig">
	${svg}
</figure>
<details class="slip transcript">
	<summary>Read the transcript</summary>
	<p>A sketched page labelled SKILL.md stands slightly askew, frontmatter at the top and a few lines of instructions below. A small dark slip of code, starting with a hash-bang, is taped to its right edge; an arrow labelled “helper” points at it. Behind the page, held by a bulldog clip, is a ruled sheet labelled “ledger” with a few lines written on it; an arrow labelled “memory” points at it. Lettered underneath: level 2: give it a helper and a memory.</p>
</details>
${page(1, `<p class="kicker">Some Assembly Required · Level 2 of 5</p><h2>${TITLE}</h2><p class="lede">${lede}</p><p>Where level 1 left it:</p>${code(skill, { upto: 0, label: PATHS.skill })}`)}
${page(2, `<h3><span class="snum">2.1</span> ${steps['2.1'].title}</h3>${steps['2.1'].body}${code(script, { upto: 1, add: 'all-new', label: PATHS.script })}${code(skill, { upto: 1, add: '2.1', label: PATHS.skill })}`)}
${page(3, `<h3><span class="snum">2.2</span> ${steps['2.2'].title}</h3>${steps['2.2'].body}${code(skill, { upto: 2, add: '2.2', label: PATHS.skill })}`)}
${page(4, `<h3><span class="snum">2.3</span> ${steps['2.3'].title}</h3>${steps['2.3'].body}${code(script, { upto: 3, add: '2.3', label: PATHS.script })}${code(skill, { upto: 3, add: '2.3', label: PATHS.skill })}${ledgerSlip()}`)}
${page(5, `<h3 class="sec">The Real Thing</h3>${realIntro}${code(real, { marks: true, label: PATHS.real })}${realList()}`)}
${exercise('z')}
</div>
</section>`;
}

const css = readFileSync(DIR + 'style.css', 'utf8');
const js = readFileSync(DIR + 'script.js', 'utf8');

const html = `<style>
${css.trim()}
</style>

<nav class="switcher" aria-label="Mockups">
	<h1>Tutorial directions</h1>
	<div class="switch-buttons">
		<button type="button" data-target="ledger" aria-pressed="true" aria-controls="ledger"><span aria-hidden="true">1</span> Ledger</button>
		<button type="button" data-target="scroll" aria-pressed="false" aria-controls="scroll"><span aria-hidden="true">2</span> Scroll</button>
		<button type="button" data-target="specimen" aria-pressed="false" aria-controls="specimen"><span aria-hidden="true">3</span> Specimen</button>
		<button type="button" data-target="zine" aria-pressed="false" aria-controls="zine"><span aria-hidden="true">4</span> Zine</button>
	</div>
</nav>

<main class="desk">
${mockLedger()}

${mockScroll()}

${mockSpecimen()}

${mockZine()}
</main>

<script>
${js.trim()}
</script>
`;
writeFileSync(OUT, html);
console.log('wrote', OUT, html.length);
