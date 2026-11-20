// What the tutorial stage shows, worked out from the data in tutorial.ts, and the
// rules that data must keep for the stage to work. No DOM here: the components
// and the tests both use it.

import type { Callout, FileView, Level, StagePage, Step } from './tutorial.types.ts';

/** A colour per step, in order; the Real Thing has its own. */
export type Tone = 't1' | 't2' | 't3' | 't4' | 't5' | 'tr';
const STEP_TONES: readonly Tone[] = ['t1', 't2', 't3', 't4', 't5'];

/** One state of the stage: the opening (where the last level left off) or a step. */
export interface StageState {
	/** The step id ("2.1"), or null for the opening. */
	id: string | null;
	title: string;
	prose: string[];
	files: FileView[];
	callouts: Callout[];
	output?: Step['output'];
	tone: Tone | null;
}

export const stepTone = (index: number): Tone => STEP_TONES[index % STEP_TONES.length]!;

export const statesOf = (level: StagePage): StageState[] => [
	...(level.opening ? [{ id: null, title: level.opening.title, prose: level.opening.prose, files: level.opening.files, callouts: [], tone: null }] : []),
	...level.steps.map((step, index) => ({
		id: step.id,
		title: step.title,
		prose: step.prose,
		files: step.files,
		callouts: step.callouts,
		output: step.output,
		tone: stepTone(index),
	})),
];

/** The tone of a callout label: its step's tone, or the Real Thing's. */
export const toneOfLabel = (level: StagePage, label: string): Tone | null => {
	if (label.startsWith('R.')) return 'tr';
	const index = level.steps.findIndex((step) => step.callouts.some((callout) => callout.label === label));
	return index < 0 ? null : stepTone(index);
};

export const linesOf = (file: FileView): string[] => file.text.split('\n');

/** Each path's tab label: its last segment, or as many trailing segments as tell it apart from the others. */
export const tabLabels = (paths: readonly string[]): string[] => {
	const parts = paths.map((path) => path.replace(/\/+$/, '').split('/'));
	return parts.map((segments, index) => {
		for (let k = 1; k <= segments.length; k++) {
			const label = segments.slice(-k).join('/');
			if (parts.every((other, j) => j === index || other.slice(-k).join('/') !== label)) return label;
		}
		return paths[index]!;
	});
};

/** True when 1-based line n sits inside one of the file's folds. */
export const isFolded = (file: FileView, n: number): boolean => (file.fold ?? []).some(([from, to]) => n >= from && n <= to);

// ---------- matching one version of a file to the next ----------

/** For each line of `next`, the index of the same line in `previous` (longest common subsequence), or -1. */
export const matchLines = (previous: string[], next: string[]): number[] => {
	const rows = previous.length;
	const cols = next.length;
	const table: number[][] = Array.from({ length: rows + 1 }, () => new Array<number>(cols + 1).fill(0));
	for (let i = rows - 1; i >= 0; i--) {
		for (let j = cols - 1; j >= 0; j--) {
			table[i]![j] = previous[i] === next[j] ? table[i + 1]![j + 1]! + 1 : Math.max(table[i + 1]![j]!, table[i]![j + 1]!);
		}
	}
	const map = new Array<number>(cols).fill(-1);
	let i = 0;
	let j = 0;
	while (i < rows && j < cols) {
		if (previous[i] === next[j]) {
			map[j] = i;
			i++;
			j++;
		} else if (table[i + 1]![j]! >= table[i]![j + 1]!) i++;
		else j++;
	}
	return map;
};

/** A callout carried into a later state: its line numbers moved to where its lines now stand. */
export interface ShownCallout extends Callout {
	/** True for a callout from an earlier step, shown dimmed. */
	past: boolean;
	tone: Tone | null;
}

export interface StageView {
	/** Per state, per path: the tone of each line (index 0 is line 1). */
	tones: Map<string, (Tone | null)[]>[];
	/** Per state: its own callouts, then earlier steps' callouts still on show. */
	callouts: ShownCallout[][];
}

/**
 * Follows every file through the level: which step each line came from (so a line keeps its
 * step's colour), and where each earlier callout's lines stand in later versions (so it stays
 * pinned, dimmed). A carried callout drops out once any of its lines is changed, removed or folded.
 */
export const stageView = (level: StagePage): StageView => {
	const states = statesOf(level);
	const versions = new Map<string, { lines: string[]; tones: (Tone | null)[] }>();
	const carried: { callout: Callout; tone: Tone | null; lines: number[] }[] = [];
	const tones: Map<string, (Tone | null)[]>[] = [];
	const callouts: ShownCallout[][] = [];

	states.forEach((state) => {
		const toneMap = new Map<string, (Tone | null)[]>();
		for (const file of state.files) {
			const next = linesOf(file);
			const before = versions.get(file.path);
			const map = before ? matchLines(before.lines, next) : new Array<number>(next.length).fill(-1);
			const added = new Set(file.added ?? []);
			const lineTones = next.map((_, j) => (added.has(j + 1) ? state.tone : map[j]! >= 0 ? before!.tones[map[j]!]! : null));
			// move earlier callouts on this file to their new line numbers
			if (before) {
				const where = new Map<number, number>();
				map.forEach((old, j) => { if (old >= 0) where.set(old + 1, j + 1); });
				for (const entry of carried) {
					if (entry.callout.file !== file.path || entry.lines.length === 0) continue;
					const moved = entry.lines.map((n) => where.get(n) ?? -1);
					entry.lines = moved.every((n) => n > 0 && !added.has(n)) ? moved : [];
				}
			}
			versions.set(file.path, { lines: next, tones: lineTones });
			toneMap.set(file.path, lineTones);
		}
		tones.push(toneMap);

		const shownFiles = new Map(state.files.map((file) => [file.path, file]));
		const past: ShownCallout[] = carried
			.filter((entry) => entry.lines.length > 0 && shownFiles.has(entry.callout.file))
			.filter((entry) => entry.lines.every((n) => !isFolded(shownFiles.get(entry.callout.file)!, n)))
			.map((entry) => ({ ...entry.callout, line: entry.lines[0]!, to: entry.lines.length > 1 ? entry.lines[entry.lines.length - 1] : undefined, past: true, tone: entry.tone }));
		const own: ShownCallout[] = state.callouts.map((callout) => ({ ...callout, past: false, tone: state.tone }));
		callouts.push([...own, ...past]);

		for (const callout of state.callouts) {
			const last = callout.to ?? callout.line;
			carried.push({ callout, tone: state.tone, lines: Array.from({ length: last - callout.line + 1 }, (_, k) => callout.line + k) });
		}
	});
	return { tones, callouts };
};

// ---------- the lines a code panel draws ----------

export type ShownLine =
	| { kind: 'line'; n: number; text: string; added: boolean; tone: Tone | null }
	| { kind: 'fold'; from: number; to: number }
	| { kind: 'removed'; text: string };

/** A file's lines as drawn: folds as one "..." line, and (live stage only) removed lines struck through above where they were. */
export const shownLines = (file: FileView, tones: (Tone | null)[] | undefined, live: boolean): ShownLine[] => {
	const lines = linesOf(file);
	const added = new Set(file.added ?? []);
	const removedBefore = new Map<number, string[]>();
	if (live) for (const removed of file.removed ?? []) removedBefore.set(removed.before, [...(removedBefore.get(removed.before) ?? []), removed.text]);
	const out: ShownLine[] = [];
	for (let n = 1; n <= lines.length + 1; n++) {
		for (const text of removedBefore.get(n) ?? []) out.push({ kind: 'removed', text });
		if (n > lines.length) break;
		const fold = (file.fold ?? []).find(([from]) => from === n);
		if (fold) {
			out.push({ kind: 'fold', from: fold[0], to: fold[1] });
			n = Math.max(n, fold[1]);
			continue;
		}
		out.push({ kind: 'line', n, text: lines[n - 1]!, added: added.has(n), tone: tones?.[n - 1] ?? null });
	}
	return out;
};

// ---------- prose: colour-matched marks ----------

const MARK = /<mark data-c="([^"]+)">/g;

/** The labels a piece of prose marks. */
export const markLabels = (html: string): string[] => [...html.matchAll(MARK)].map((match) => match[1]!);

/**
 * Gives each mark its callout's tone, and after a mark for one of `own` (the state's own
 * callouts) adds the label, so the phrase and its callout carry the same number.
 */
export const toneMarks = (html: string, level: StagePage, own: readonly string[] = []): string =>
	html.replace(/<mark data-c="([^"]+)">([\s\S]*?)<\/mark>/g, (_, label: string, inner: string) => {
		const tone = toneOfLabel(level, label) ?? '';
		const ref = own.includes(label) ? ` <span class="ref">${label}</span>` : '';
		return `<mark data-c="${label}" class="${tone}">${inner}</mark>${ref}`;
	});

// ---------- the rules the stage relies on ----------

const ALLOWED_TAGS = /<\/?(?!code\b|mark\b)[a-z][^>]*>/i;

/** Every way a level breaks what the stage needs; empty when it is sound. Its steps are numbered "2.1", "2.2" and so on. */
export const checkLevel = (level: Level): string[] => [
	...(level.n === 1 && level.opening ? [`level 1, opening: level 1 has no opening`] : []),
	...(level.n === 1 && level.realThing ? [`level 1, real thing: level 1 has none`] : []),
	...checkStage(level, `level ${level.n}`, `${level.n}.`),
];

/**
 * Every way a stage page breaks what the stage needs; empty when it is sound. `prefix` goes before
 * each step's number: "2." for a tutorial level's "2.1", empty for a page whose steps are "1" to "4".
 */
export const checkStage = (level: StagePage, name: string, prefix: string): string[] => {
	const problems: string[] = [];
	const at = (where: string, problem: string): void => { problems.push(`${name}, ${where}: ${problem}`); };

	const labels = new Set<string>();
	const html: { where: string; text: string }[] = [{ where: 'intro', text: level.intro }];

	const checkFile = (where: string, file: FileView, targeted: Set<number>): void => {
		const count = linesOf(file).length;
		const folds = [...(file.fold ?? [])].sort((a, b) => a[0] - b[0]);
		folds.forEach(([from, to], index) => {
			if (from < 1 || to > count || from > to) at(where, `fold ${from}-${to} is outside the file's ${count} lines`);
			const previous = folds[index - 1];
			if (previous && from <= previous[1]) at(where, `fold ${from}-${to} overlaps fold ${previous[0]}-${previous[1]}`);
		});
		for (const n of file.added ?? []) {
			if (n < 1 || n > count) at(where, `added line ${n} is outside the file's ${count} lines`);
			if (isFolded(file, n)) at(where, `added line ${n} is folded away`);
		}
		for (const removed of file.removed ?? []) if (removed.before < 1 || removed.before > count + 1) at(where, `a removed line sits before line ${removed.before}, outside the file`);
		for (const n of targeted) if (isFolded(file, n)) at(where, `line ${n} has a callout but is folded away`);
	};

	const checkCallouts = (where: string, files: FileView[], callouts: Callout[], pattern: RegExp): void => {
		const byPath = new Map(files.map((file) => [file.path, file]));
		const targeted = new Map<string, Set<number>>();
		callouts.forEach((callout, index) => {
			if (!pattern.test(callout.label)) at(where, `callout ${callout.label} should match ${pattern}`);
			if (labels.has(callout.label)) at(where, `callout ${callout.label} appears twice`);
			labels.add(callout.label);
			const expected = String.fromCharCode(97 + index);
			if (!callout.label.endsWith(expected)) at(where, `callout ${callout.label} is out of order: callout ${index + 1} should end in "${expected}"`);
			const file = byPath.get(callout.file);
			if (!file) { at(where, `callout ${callout.label} points into ${callout.file}, which the step does not show`); return; }
			const count = linesOf(file).length;
			const last = callout.to ?? callout.line;
			if (callout.line < 1 || last > count || last < callout.line) at(where, `callout ${callout.label} points at ${callout.line}-${last}, outside ${callout.file}'s ${count} lines`);
			const set = targeted.get(callout.file) ?? new Set<number>();
			for (let n = callout.line; n <= last; n++) set.add(n);
			targeted.set(callout.file, set);
			html.push({ where: `${where} callout ${callout.label}`, text: callout.html });
		});
		for (const file of files) checkFile(`${where} ${file.path}`, file, targeted.get(file.path) ?? new Set());
	};

	// the opening is optional: without one the stage opens on the first step
	if (level.opening) {
		if (level.opening.files.length === 0) at('opening', 'shows no file');
		for (const file of level.opening.files) checkFile(`opening ${file.path}`, file, new Set());
		level.opening.prose.forEach((text, index) => html.push({ where: `opening paragraph ${index + 1}`, text }));
	}
	if (level.steps.length === 0) at('steps', 'there are none');
	const ids = new Set<string>();
	level.steps.forEach((step, index) => {
		const where = `step ${step.id}`;
		if (step.id !== `${prefix}${index + 1}`) at(where, `should be numbered ${prefix}${index + 1}`);
		if (ids.has(step.id)) at(where, 'id appears twice');
		ids.add(step.id);
		if (step.files.length === 0) at(where, 'shows no file');
		const paths = step.files.map((file) => file.path);
		if (new Set(paths).size !== paths.length) at(where, 'shows the same file twice');
		checkCallouts(where, step.files, step.callouts, new RegExp(`^${step.id.replace('.', '\\.')}[a-z]$`));
		step.prose.forEach((text, index2) => html.push({ where: `${where} paragraph ${index2 + 1}`, text }));
	});
	if (level.realThing) {
		checkCallouts('the real thing', level.realThing.files, level.realThing.callouts, /^R\.[a-z]$/);
		html.push({ where: 'the real thing intro', text: level.realThing.intro });
		(level.realThing.after ?? []).forEach((text, index) => html.push({ where: `the real thing paragraph ${index + 1}`, text }));
	}
	level.exercise.prompt.forEach((text, index) => html.push({ where: `exercise paragraph ${index + 1}`, text }));
	level.exercise.answer.forEach((part, index) => {
		if ('prose' in part) html.push({ where: `answer part ${index + 1}`, text: part.prose });
		if ('table' in part) [...part.table.head, ...part.table.rows.flat()].forEach((text) => html.push({ where: `answer part ${index + 1} table`, text }));
	});

	for (const { where, text } of html) {
		if (ALLOWED_TAGS.test(text)) at(where, `holds a tag other than <code> or <mark>: ${text.match(ALLOWED_TAGS)![0]}`);
		for (const label of markLabels(text)) if (!labels.has(label)) at(where, `marks ${label}, which no callout carries`);
		if (/<mark(?! data-c=")/.test(text)) at(where, 'has a <mark> without data-c');
	}
	return problems;
};
