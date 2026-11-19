import { countWord, CountWord, type Facts } from '#lib/facts.ts';

/** Every placeholder the copy may use, and the generated count behind it. */
const COUNTS = (facts: Facts): Record<string, number> => ({
	seneschalHeartbeatSeconds: facts.counts.seneschalHeartbeatSeconds,
	jesterDayStates: facts.counts.jesterDayStates,
	jesterLines: facts.mods.jester.typescriptLines,
	scoutSkills: facts.mods.scout.skills,
	warbandRules: facts.counts.warbandRules,
});

const PLACEHOLDER = /\{([a-zA-Z]+)\}/g;

/**
 * Fill the count placeholders in a piece of copy: {scoutSkills} becomes
 * "twelve", {ScoutSkills} becomes "Twelve". An unknown placeholder throws, so
 * a typo fails the build instead of reaching the page.
 */
export const fill = (text: string, facts: Facts): string => {
	const counts = COUNTS(facts);
	return text.replace(PLACEHOLDER, (whole, name: string) => {
		const key = name.charAt(0).toLowerCase() + name.slice(1);
		const count = counts[key];
		if (count === undefined) throw new Error(`Unknown count placeholder ${whole}`);
		return name === key ? countWord(count) : CountWord(count);
	});
};

export const PLACEHOLDER_NAMES = (facts: Facts): string[] => Object.keys(COUNTS(facts));
