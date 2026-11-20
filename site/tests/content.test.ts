// The mod pages' copy: every count comes from a known placeholder, every
// situation can be linked to, every roster row points at a situation that
// exists, and no old name survives in what a mod page says it does.

import { describe, expect, it } from 'vitest';
import { collect } from '../scripts/generate';
import { fill } from '../src/lib/content/fill';
import { MOD_FILES } from '../src/lib/content/mod-files';
import { MOD_NAMES, type ModKey } from '../src/lib/mod-names';

const facts = await collect();
const keys = Object.keys(MOD_NAMES) as ModKey[];

/** Every string a mod page renders from its file. */
const strings = (key: ModKey): string[] => {
	const file = MOD_FILES[key];
	return [
		...file.situations.flatMap((s) => [s.title, s.hint, s.scene, ...s.before, s.withHeading, ...s.with, s.ruling]),
		...file.roster.map((row) => row.text),
		...(file.howTo ? [...file.howTo.firstRun, ...file.howTo.configure, ...file.howTo.remove] : []),
	];
};

describe('fill', () => {
	it('writes small counts as words and capitalises on request', () => {
		expect(fill('every {seneschalHeartbeatSeconds} seconds', facts)).toBe(`every ${facts.counts.seneschalHeartbeatSeconds === 15 ? 'fifteen' : facts.counts.seneschalHeartbeatSeconds} seconds`);
		expect(fill('{ScoutSkills} skills', facts)).toMatch(/^[A-Z]/);
	});

	it('refuses a placeholder it does not know', () => {
		expect(() => fill('{madeUpCount}', facts)).toThrow(/Unknown count placeholder/);
	});
});

/** Claude Code's own commands, which the copy names when it says where a setting lives. */
const BUILT_IN = new Set(['/config', '/model', '/plugin', '/clear', '/compact', '/diff']);

describe.each(keys)('%s', (key) => {
	const file = MOD_FILES[key];

	it('is filed under its own key', () => {
		expect(file.key).toBe(key);
	});

	it('has situations with unique ids matching their numbers', () => {
		expect(file.situations.length).toBeGreaterThan(0);
		const ids = file.situations.map((s) => s.id);
		expect(new Set(ids).size).toBe(ids.length);
		for (const s of file.situations) expect(s.id).toBe(s.num.toLowerCase().replace('.', '-'));
	});

	it('points every shown roster row at a situation on the page', () => {
		const nums = new Set(file.situations.map((s) => s.num));
		for (const row of file.roster) {
			if (row.where !== null) expect(nums.has(row.where), `${row.text} -> ${row.where}`).toBe(true);
			if (!row.shown) expect(row.where).toBeNull();
		}
	});

	it('fills every placeholder in its copy', () => {
		for (const text of strings(key)) expect(() => fill(text, facts)).not.toThrow();
	});

	it('names the mod only by its new name', () => {
		const old = MOD_NAMES[key].slice(1);
		for (const text of strings(key)) {
			for (const name of old) expect(text, text).not.toMatch(new RegExp(`\\b${name}\\b`));
		}
	});

	// Runs once this mod's rename is on main (the site merges last): every command
	// or skill the copy names must be one the plugin actually registers.
	it.skipIf(facts.mods[key].name !== MOD_NAMES[key][0])('names only commands and skills the plugin registers', () => {
		const known = new Set(facts.mods[key].commands.map((command) => command.invocation));
		const named = new Set(
			strings(key).flatMap((text) => [...text.matchAll(/<code>(\/[a-z][a-z-]*(?::[a-z][a-z-]*)?)/g)].map((match) => match[1] ?? '')),
		);
		const planned = new Set(MOD_FILES[key].plannedCommands ?? []);
		const unknown = [...named].filter((invocation) => !known.has(invocation) && !planned.has(invocation) && !BUILT_IN.has(invocation));
		expect(unknown, `named in the copy but not registered by ${MOD_NAMES[key][0]}`).toEqual([]);
		// a planned command that has shipped must lose its "Not built yet" stamp
		const shipped = [...planned].filter((invocation) => known.has(invocation));
		expect(shipped, `registered by ${MOD_NAMES[key][0]} but still stamped as not built`).toEqual([]);
	});

	it('uses no em dash and no hand-typed digit counts of the repository', () => {
		for (const text of strings(key)) {
			expect(text).not.toContain('—');
			expect(text, text).not.toMatch(/\b1,281\b/);
		}
	});
});
