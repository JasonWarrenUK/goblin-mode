// Dressed for the project (38): the palette every drawing takes its colours
// from. Resolution follows library/references/theme-conventions.md: a family
// named in the options, else the only core in the project's .claude/themes,
// else the global clod family, else the clod values baked in here.

import type { Palette } from '../types'

/** The clod family's dark variant, so the chrome draws before any file is read. */
export const CLOD: Palette = {
	family: 'clod',
	ink: '#EDE7DA',
	inkMuted: '#A39C8E',
	surface: '#14181F',
	surfaceRaised: '#1D232C',
	line: '#2E3640',
	accent: '#D9A441',
	accentInk: '#1A1408',
	accent2: '#4FB3A8',
	ok: '#6FBF73',
	warn: '#E0A83A',
	danger: '#E06C5B',
	info: '#6FA8DC',
}

const SWATCHES: Record<Exclude<keyof Palette, 'family'>, string> = {
	ink: 'ink',
	inkMuted: 'ink-muted',
	surface: 'surface',
	surfaceRaised: 'surface-raised',
	line: 'line',
	accent: 'accent',
	accentInk: 'accent-ink',
	accent2: 'accent-2',
	ok: 'ok',
	warn: 'warn',
	danger: 'danger',
	info: 'info',
}

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null

/** A core theme file's dark variant as a Palette, or null when the file is not a core. */
export const paletteFrom = (core: unknown): Palette | null => {
	if (!isRecord(core) || !isRecord(core.palette) || typeof core.family !== 'string') return null
	const palette = core.palette
	const out: Record<string, string> = { family: core.family }
	for (const [key, swatch] of Object.entries(SWATCHES)) {
		const entry = palette[swatch]
		const dark = isRecord(entry) ? entry.dark : undefined
		if (typeof dark !== 'string' || !/^#[0-9a-f]{6}$/i.test(dark)) return null
		out[key] = dark
	}
	return out as Palette
}

/** Core files in a themes directory: `<family>.json`, never a hyphenated target. */
export const coreNames = (entries: readonly { name: string; kind: string }[]): string[] =>
	entries
		.filter(e => e.kind === 'file' && /^[a-z0-9]+\.json$/.test(e.name))
		.map(e => e.name.slice(0, -5))
		.sort()

type Reader = {
	list: (path: string) => Promise<readonly { name: string; kind: string }[]>
	read: (path: string) => Promise<string>
	home: () => Promise<string | undefined>
}

/**
 * Resolve the palette for this session. `wanted` is the family the options
 * name, '' for none. Every failure falls through to the next source and the
 * last source is the baked-in clod, so this never throws.
 */
export const loadPalette = async (reader: Reader, wanted: string): Promise<Palette> => {
	const tryRead = async (path: string): Promise<Palette | null> => {
		try {
			return paletteFrom(JSON.parse(await reader.read(path)))
		} catch {
			return null
		}
	}
	try {
		const families = coreNames(await reader.list('.claude/themes'))
		const family = wanted ? (families.includes(wanted) ? wanted : null) : families.length === 1 ? families[0] : null
		if (family) {
			const found = await tryRead(`.claude/themes/${family}.json`)
			if (found) return found
		}
	} catch {
		// no project themes directory
	}
	const home = await reader.home().catch(() => undefined)
	if (home) {
		const global = await tryRead(`${home}/.claude/library/themes/${wanted || 'clod'}.json`)
		if (global) return global
	}
	return CLOD
}
