// The tutorial's data keeps the rules the pinned stage relies on: callouts point at
// lines that exist and show, folds never hide a changed or pointed-at line, every
// mark names a callout and every level is there in order.

import { describe, expect, it } from 'vitest';
import { TUTORIAL } from '../src/lib/content/tutorial';
import { checkLevel, matchLines, shownLines, stageView, statesOf, tabLabels, toneMarks } from '../src/lib/content/tutorial-view';

describe('the tutorial', () => {
	it('has five levels, numbered 1 to 5 in order', () => {
		expect(TUTORIAL.map((level) => level.n)).toEqual([1, 2, 3, 4, 5]);
	});
});

describe.each(TUTORIAL.map((level) => [level.n, level] as const))('level %i', (_, level) => {
	it('keeps every rule the stage relies on', () => {
		expect(checkLevel(level)).toEqual([]);
	});

	it('opens on its opening when it has one, and on its first step otherwise', () => {
		expect(statesOf(level)[0]!.id).toBe(level.opening ? null : level.steps[0]!.id);
		if (level.n === 1) expect(level.opening).toBeUndefined();
	});

	it('carries earlier callouts only onto the lines they first pointed at', () => {
		const states = statesOf(level);
		const view = stageView(level);
		view.callouts.forEach((shown, index) => {
			const state = states[index]!;
			for (const callout of shown.filter((c) => c.past)) {
				const file = state.files.find((f) => f.path === callout.file)!;
				const original = level.steps.flatMap((s) => s.callouts.map((c) => ({ c, s }))).find(({ c }) => c.label === callout.label)!;
				const was = original.s.files.find((f) => f.path === callout.file)!.text.split('\n')[original.c.line - 1];
				expect(file.text.split('\n')[callout.line - 1], `${callout.label} in state ${index}`).toBe(was);
			}
		});
	});

	it('draws every pointed-at line in the live stage', () => {
		const view = stageView(level);
		statesOf(level).forEach((state, index) => {
			for (const file of state.files) {
				const drawn = new Set(shownLines(file, view.tones[index]!.get(file.path), true).flatMap((line) => (line.kind === 'line' ? [line.n] : [])));
				for (const callout of view.callouts[index]!.filter((c) => c.file === file.path)) {
					for (let n = callout.line; n <= (callout.to ?? callout.line); n++) expect(drawn.has(n), `${callout.label} line ${n}`).toBe(true);
				}
			}
		});
	});
});

describe('the stage helpers', () => {
	it('matches unchanged lines across versions', () => {
		expect(matchLines(['a', 'b', 'c'], ['a', 'x', 'b', 'c'])).toEqual([0, -1, 1, 2]);
	});

	it('folds a range to one line and strikes removed lines only when live', () => {
		const file = { path: 'f', lang: 'text', text: 'one\ntwo\nthree\nfour', fold: [[2, 3]] as [number, number][], removed: [{ before: 4, text: 'gone' }] };
		expect(shownLines(file, undefined, true).map((line) => line.kind)).toEqual(['line', 'fold', 'removed', 'line']);
		expect(shownLines(file, undefined, false).map((line) => line.kind)).toEqual(['line', 'fold', 'line']);
	});

	it('colours a mark by its step and labels only the state\'s own', () => {
		const level = TUTORIAL[1]!;
		const first = level.steps[0]!.callouts[0]!.label;
		const second = level.steps[1]!.callouts[0]!.label;
		expect(toneMarks(`<mark data-c="${second}">x</mark>`, level, [second])).toBe(`<mark data-c="${second}" class="t2">x</mark> <span class="ref">${second}</span>`);
		expect(toneMarks(`<mark data-c="${first}">x</mark>`, level, [second])).toBe(`<mark data-c="${first}" class="t1">x</mark>`);
	});

	it('finds a callout that points at a line that is not there', () => {
		const level = structuredClone(TUTORIAL[1]!);
		const callout = level.steps[0]!.callouts[0]!;
		callout.line = 999;
		expect(checkLevel(level).join('\n')).toContain(`${callout.label} points at 999`);
	});

	it('tells same-named files apart on their tabs', () => {
		expect(tabLabels(['a/SKILL.md', 'b/SKILL.md', 'Terminal', 'tidy/'])).toEqual(['a/SKILL.md', 'b/SKILL.md', 'Terminal', 'tidy']);
		expect(tabLabels(['x/y/plugin.json', 'tidy'])).toEqual(['plugin.json', 'tidy']);
	});
});
