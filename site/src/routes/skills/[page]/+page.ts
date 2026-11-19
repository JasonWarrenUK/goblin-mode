import { error } from '@sveltejs/kit';
import { SKILL_PAGES } from '#lib/content/skills.ts';
import type { EntryGenerator, PageLoad } from './$types';

/** Every explainer but the tutorial, which has its own pages under /skills/tutorial/. */
const SHARED = SKILL_PAGES.filter((page) => !page.tutorial);

export const entries: EntryGenerator = () => SHARED.map((page) => ({ page: page.slug }));

export const load: PageLoad = ({ params }) => {
	const page = SHARED.find((candidate) => candidate.slug === params.page);
	if (!page) error(404, `No page called ${params.page}`);
	return { page };
};
