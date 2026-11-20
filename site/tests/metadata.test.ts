// "Metadata Is Whatever I Say It Is": the page keeps the stage's rules, its files
// match the specimen the script was run on, the script still prints what the
// page says it prints, and every count and Real Thing excerpt is true of the
// repository the site is built from.

import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { metadataCounts, metadataKey, repositorySkillFiles } from '../scripts/generate';
import { fill, PLACEHOLDER_NAMES } from '../src/lib/content/fill';
import { METADATA } from '../src/lib/content/metadata';
import { checkStage } from '../src/lib/content/tutorial-view';
import { facts } from '../src/lib/facts';

const SITE = fileURLToPath(new URL('..', import.meta.url));
const REPO = join(SITE, '..');
const SPECIMEN = join(SITE, 'design/content/metadata-specimen/step4');

const lastStep = METADATA.steps.at(-1)!;
const shown = (path: string): string => lastStep.files.find((file) => file.path === path)!.text;

describe('the Metadata page', () => {
	it('keeps every rule the stage relies on, with steps numbered 1 to 4', () => {
		expect(checkStage(METADATA, 'metadata', '')).toEqual([]);
		expect(METADATA.steps.map((step) => step.id)).toEqual(['1', '2', '3', '4']);
	});

	it('shows the step 4 files exactly as the specimen holds them', () => {
		for (const path of ['.claude/skills/roast-branch/SKILL.md', 'scripts/roast-menu.py']) {
			expect(shown(path)).toBe(readFileSync(join(SPECIMEN, path), 'utf8').trimEnd());
		}
	});

	it("prints what step 4's output panel says, and exits 1", () => {
		let status = 0;
		let out = '';
		try {
			out = execFileSync('python3', ['-I', 'scripts/roast-menu.py'], { cwd: SPECIMEN, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
		} catch (error) {
			const failed = error as { status: number; stdout: string; stderr: string };
			status = failed.status;
			out = failed.stdout + failed.stderr;
		}
		expect(status).toBe(1);
		expect(out.trimEnd()).toBe(lastStep.output!.text);
	});

	it('uses only count placeholders the build fills', () => {
		const names = new Set(PLACEHOLDER_NAMES(facts));
		// the copy only: the files on the stage hold Python's own {braces}
		const copy = [
			METADATA.intro,
			...METADATA.steps.flatMap((step) => [...step.prose, ...step.callouts.map((callout) => callout.html)]),
			METADATA.realThing!.intro,
			...METADATA.realThing!.callouts.map((callout) => callout.html),
			...METADATA.exercise.prompt,
		].join('\n');
		const used = [...copy.matchAll(/\{([a-zA-Z]+)\}/g)].map((match) => match[1]!);
		expect(used.length).toBeGreaterThan(0);
		for (const name of used) expect(names.has(name), name).toBe(true);
		expect(() => fill(METADATA.realThing!.intro, facts)).not.toThrow();
	});
});

describe('the counts the Real Thing states', () => {
	const counts = metadataCounts(repositorySkillFiles(REPO));

	it('match what the build generated', () => {
		expect(facts.counts.metadataSkills).toBe(counts.skills);
		expect(facts.counts.metadataFamilies).toBe(counts.families);
		expect(facts.counts.metadataGlyphs).toBe(counts.glyphs);
		expect(facts.counts.metadataSpinners).toBe(counts.spinners);
	});

	it('back the claim that every skill carries family', () => {
		expect(counts.withFamily).toBe(counts.skills);
	});

	it('read a nested key the way skill-lint.py does', () => {
		const skill = '---\nname: x\nmetadata:\n  family: roast # a comment\n  glyph: "ᛊ"\nmodel: sonnet\n---\nbody';
		expect(metadataKey(skill, 'family')).toBe('roast');
		expect(metadataKey(skill, 'glyph')).toBe('ᛊ');
		expect(metadataKey(skill, 'model')).toBeNull();
	});
});

describe('the Real Thing excerpts', () => {
	// The excerpts quote main after the November 2026 renames (skill-lint.py's docstring names
	// goblin-jester there), so they are checked once the rebase brings goblin-jester onto this branch.
	const renamed = existsSync(join(REPO, 'marketplace/goblin-jester'));
	for (const file of METADATA.realThing!.files) {
		const source = join(REPO, file.path);
		it.skipIf(!renamed)(`quote ${file.path} line for line`, () => {
			const lines = new Set(readFileSync(source, 'utf8').split('\n').map((line) => line.trimEnd()));
			const missing = file.text.split('\n').filter((line: string) => !/^\s*\.\.\.$/.test(line) && !lines.has(line));
			expect(missing).toEqual([]);
		});
	}
});
