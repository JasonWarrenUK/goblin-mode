import generated from '$lib/generated/facts.json';
import type { Facts } from '$lib/mod-names';

export { MOD_NAMES, type Facts, type ModFacts, type ModKey } from '$lib/mod-names';
import type { ModKey } from '$lib/mod-names';

/** The order the notice files the mods in: I to V. */
export const MOD_ORDER: readonly ModKey[] = ['seneschal', 'jester', 'scout', 'warband', 'archivist'];

export const facts = generated as Facts;

const WORDS = [
	'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
	'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty',
] as const;

/** A count as the notice writes it: words up to twenty, grouped digits above. */
export const countWord = (count: number): string => WORDS[count] ?? count.toLocaleString('en-GB');

/** The same, capitalised for the start of a sentence. */
export const CountWord = (count: number): string => {
	const word = countWord(count);
	return word.charAt(0).toUpperCase() + word.slice(1);
};
