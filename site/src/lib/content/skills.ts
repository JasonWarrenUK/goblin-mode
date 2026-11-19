// The skills wing: one page per explainer. Titles are the current ones; each
// changes as its page is reworked with Jason (scope S2 to S4).

export interface SkillPage {
	slug: string;
	title: string;
	/** The tutorial lives at /skills/tutorial/ with a page per level, not on the shared route. */
	tutorial?: boolean;
}

export const SKILL_PAGES: readonly SkillPage[] = [
	{ slug: 'frontmatter', title: 'A Skill Is One Goblin' },
	{ slug: 'metadata', title: 'Metadata Is Whatever I Say It Is' },
	{ slug: 'tutorial', title: 'Some Assembly Required', tutorial: true },
	{ slug: 'dossier', title: 'Everyone Gets a File' },
	{ slug: 'red', title: 'The Red Family' },
];
