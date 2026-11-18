import { error } from '@sveltejs/kit';
import { SKILL_PAGES } from '#lib/content/skills.ts';
import type { EntryGenerator, PageLoad } from './$types';

export const entries: EntryGenerator = () => SKILL_PAGES.map((page) => ({ page: page.slug }));

export const load: PageLoad = ({ params }) => {
	const page = SKILL_PAGES.find((candidate) => candidate.slug === params.page);
	if (!page) error(404, `No page called ${params.page}`);
	return { page };
};
