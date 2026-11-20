import { describe, expect, it } from 'vitest';
import { collect, doNotRules, registeredCommands } from '../scripts/generate';
import { countWord, CountWord } from '../src/lib/facts';
import { MOD_NAMES } from '../src/lib/mod-names';

describe('doNotRules', () => {
	it('counts only bullets that open with a bold Do not', () => {
		const readme = ['- **Do not run it.** Ever.', '- Do not count me', '- **Do nothing** either', '  - **Do not** nested', '- **Do not stop.**'].join('\n');
		expect(doNotRules(readme)).toBe(2);
	});
});

describe('registeredCommands', () => {
	it('finds a command registered by a literal, from a table a loop registers and through a constant', () => {
		const source = [
			"await $.command.register({ name: 'log-grievance', description: 'Log one, don\\'t argue' })",
			"export const COMMANDS = [",
			"\t{ name: 'read-slate', verb: 'status', description: 'The slate as text', argumentHint: '' },",
			"] as const",
			"for (const spec of [{ name: 'show-slate', description: 'Open the slate', argumentHint: '' }, ...COMMANDS]) {}",
			"const COMMAND = 'scout-waypoints'",
			"await $.command.register({\n\tname: COMMAND,\n\tdescription: 'The ready waypoints',\n})",
		].join('\n');
		expect(registeredCommands(source).map((command) => command.invocation).sort()).toEqual(['/log-grievance', '/read-slate', '/scout-waypoints', '/show-slate']);
		expect(registeredCommands(source).find((command) => command.invocation === '/log-grievance')?.description).toBe("Log one, don't argue");
	});
});

describe('countWord', () => {
	it('writes counts up to twenty as words and larger ones as grouped digits', () => {
		expect(countWord(15)).toBe('fifteen');
		expect(countWord(1281)).toBe('1,281');
		expect(CountWord(12)).toBe('Twelve');
	});
});

describe('collect', async () => {
	const facts = await collect();

	it('finds every shipped mod through marketplace.json under one of its names', () => {
		for (const mod of Object.values(facts.mods)) {
			if (!mod.installable) continue;
			expect(MOD_NAMES[mod.key]).toContain(mod.name);
			expect(mod.installCommand).toBe(`claude plugin install ${mod.name}@${facts.marketplace.name}`);
			expect(mod.version).toMatch(/^\d+\.\d+\.\d+/);
		}
	});

	it('counts shipped and proposed mods consistently', () => {
		expect(facts.counts.modsShipped + facts.counts.modsProposed).toBe(facts.counts.modsTotal);
		expect(facts.counts.modsShipped).toBeGreaterThan(0);
	});

	it('reads every count the copy states from the repository', () => {
		expect(facts.counts.jesterDayStates).toBeGreaterThan(0);
		expect(facts.counts.seneschalHeartbeatSeconds).toBeGreaterThan(0);
		expect(facts.counts.warbandRules).toBeGreaterThan(0);
		expect(facts.mods.jester.typescriptLines).toBeGreaterThan(0);
		expect(facts.mods.scout.skills).toBeGreaterThan(0);
	});

	it('records the commit it was built from', () => {
		expect(facts.build.commit).toMatch(/^[0-9a-f]{7,}$/);
	});
});
