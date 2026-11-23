import { resolve } from '$app/paths';

// Every page URL ends in a slash (trailingSlash: 'always'), so GitHub Pages
// serves each page's index.html directly instead of redirecting to it.

export const home = (): string => resolve('/');
export const modPage = (slug: string): string => `${resolve('/mods/[mod]', { mod: slug })}/`;
export const skillsIndex = (): string => `${resolve('/skills')}/`;
export const metadataPage = (): string => `${resolve('/skills/metadata')}/`;
export const tutorialIndex = (): string => `${resolve('/skills/tutorial')}/`;
export const tutorialLevel = (n: number): string => `${resolve('/skills/tutorial/[level]', { level: String(n) })}/`;
/** Where a skills-wing entry lives: each page has its own route. */
export const skillHref = (page: { slug: 'tutorial' | 'metadata' }): string => (page.slug === 'tutorial' ? tutorialIndex() : metadataPage());
