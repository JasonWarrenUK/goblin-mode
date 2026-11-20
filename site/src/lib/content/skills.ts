// The skills wing: one page per explainer. Titles are the current ones; each
// changes as its page is reworked with Jason (scope S2 to S4).

export interface SkillPage {
	slug: string;
	title: string;
	/** The tutorial lives at /skills/tutorial/ with a page per level, not on the shared route. */
	tutorial?: boolean;
	/** A page with its own route at /skills/<slug>/, built on the tutorial's stage; the shared route skips it. */
	staged?: boolean;
}

export const SKILL_PAGES: readonly SkillPage[] = [
	{ slug: 'metadata', title: 'Metadata Is Whatever I Say It Is', staged: true },
	{ slug: 'tutorial', title: 'Some Assembly Required', tutorial: true },
	{ slug: 'dossier', title: 'Everyone Gets a File' },
];
