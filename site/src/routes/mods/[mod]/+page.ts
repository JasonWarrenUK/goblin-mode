import { error } from '@sveltejs/kit';
import { MOD_NAMES, MOD_ORDER, type ModKey } from '$lib/facts';
import type { EntryGenerator, PageLoad } from './$types';

/** One page per mod, at its newest name. */
export const entries: EntryGenerator = () => MOD_ORDER.map((key) => ({ mod: MOD_NAMES[key][0] }));

export const load: PageLoad = ({ params }) => {
	const key = MOD_ORDER.find((candidate) => MOD_NAMES[candidate][0] === params.mod);
	if (!key) error(404, `No mod called ${params.mod}`);
	return { key: key as ModKey };
};
