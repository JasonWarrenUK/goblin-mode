// The skills wing: the tutorial and the Metadata page, each with its own route.
// The other three explainers were withdrawn on 2026-11-20 (scope S2 and S4).

export type SkillSlug = 'tutorial' | 'metadata';

export interface SkillPage {
	slug: SkillSlug;
	title: string;
}

export const SKILL_PAGES: readonly SkillPage[] = [
	{ slug: 'metadata', title: 'Metadata Is Whatever I Say It Is' },
	{ slug: 'tutorial', title: 'Some Assembly Required' },
];
