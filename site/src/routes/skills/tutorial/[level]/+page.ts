import { error } from '@sveltejs/kit';
import { TUTORIAL } from '#lib/content/tutorial.ts';
import type { EntryGenerator, PageLoad } from './$types';

/** One page per level, 1 to 5. */
export const entries: EntryGenerator = () => TUTORIAL.map((level) => ({ level: String(level.n) }));

export const load: PageLoad = ({ params }) => {
	const level = TUTORIAL.find((candidate) => String(candidate.n) === params.level);
	if (!level) error(404, `No level ${params.level}`);
	return { level, levels: TUTORIAL.map(({ n, title }) => ({ n, title })) };
};
