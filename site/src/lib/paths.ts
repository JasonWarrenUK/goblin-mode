import { resolve } from '$app/paths';

// Every page URL ends in a slash (trailingSlash: 'always'), so GitHub Pages
// serves each page's index.html directly instead of redirecting to it.

export const home = (): string => resolve('/');
export const modPage = (slug: string): string => `${resolve('/mods/[mod]', { mod: slug })}/`;
export const skillsIndex = (): string => `${resolve('/skills')}/`;
export const skillPage = (slug: string): string => `${resolve('/skills/[page]', { page: slug })}/`;
export const tutorialIndex = (): string => `${resolve('/skills/tutorial')}/`;
export const tutorialLevel = (n: number): string => `${resolve('/skills/tutorial/[level]', { level: String(n) })}/`;
/** Where a skills-wing entry lives: the tutorial has its own pages, the rest share one route. */
export const skillHref = (page: { slug: string; tutorial?: boolean }): string => (page.tutorial ? tutorialIndex() : skillPage(page.slug));
