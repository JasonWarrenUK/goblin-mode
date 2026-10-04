// Borders by tier (36): the frame every mod-drawn box takes from the model
// that served the current request, and the rune of the tier a skill pinned.

import type { Frame, Palette, Tier } from '../types'

/** The runic glyph convention from clod-config-skill_conventions: fehu for Fable, othala for Opus. */
export const RUNE: Record<Tier, string> = { top: 'ᛟ', mid: 'ᛊ', small: 'ᚺ', fable: 'ᚠ' }

/** Which tier a model id or alias belongs to; unknown ids count as the middle. */
export const tierOf = (model: string): Tier => {
	const m = model.toLowerCase()
	if (/haiku/.test(m)) return 'small'
	if (/sonnet/.test(m)) return 'mid'
	if (/fable/.test(m)) return 'fable'
	if (/opus|mythos/.test(m)) return 'top'
	return 'mid'
}

/** The `model:` line of a skill's frontmatter, or null when it has none. */
export const pinnedModel = (skillMarkdown: string): string | null => {
	const fm = /^---\r?\n([\s\S]*?)\r?\n---/.exec(skillMarkdown)
	if (!fm || fm[1] === undefined) return null
	const line = /^model:\s*["']?([^\s#"']+)/m.exec(fm[1])
	const model = line?.[1] ?? null
	return model === null || model === 'inherit' ? null : model
}

const STYLE: Record<Tier, { borderStyle: string; dim: boolean }> = {
	top: { borderStyle: 'bold', dim: false },
	fable: { borderStyle: 'double', dim: false },
	mid: { borderStyle: 'round', dim: false },
	small: { borderStyle: 'classic', dim: true },
}

/** Which palette colour each tier's frame takes: the theme's two accents, then its info and ok hues. `warn` is kept for the mismatch frame and `danger` for errors. */
const TIER_COLOUR: Record<Tier, 'accent' | 'accent2' | 'info' | 'ok'> = {
	fable: 'accent',
	top: 'accent2',
	mid: 'info',
	small: 'ok',
}

export const frameFor = (served: Tier, pinned: Tier | null, palette: Palette): Frame => {
	const mismatch = pinned !== null && pinned !== served
	const style = STYLE[served]
	return {
		borderStyle: mismatch ? 'singleDouble' : style.borderStyle,
		borderColor: mismatch ? palette.warn : palette[TIER_COLOUR[served]],
		borderDimColor: style.dim,
		rune: mismatch ? `${RUNE[pinned]}→${RUNE[served]}` : RUNE[served],
		served,
		pinned,
	}
}

export const DEFAULT_TIER: Tier = 'top'

/** The box-drawing set of each border style the frames use, with the tees where a divider meets the rules. */
export type Glyphs = {
	topLeft: string
	topRight: string
	bottomLeft: string
	bottomRight: string
	horizontal: string
	vertical: string
	teeDown: string
	teeUp: string
}

export const GLYPHS: Record<string, Glyphs> = {
	double: { topLeft: '╔', topRight: '╗', bottomLeft: '╚', bottomRight: '╝', horizontal: '═', vertical: '║', teeDown: '╦', teeUp: '╩' },
	bold: { topLeft: '┏', topRight: '┓', bottomLeft: '┗', bottomRight: '┛', horizontal: '━', vertical: '┃', teeDown: '┳', teeUp: '┻' },
	round: { topLeft: '╭', topRight: '╮', bottomLeft: '╰', bottomRight: '╯', horizontal: '─', vertical: '│', teeDown: '┬', teeUp: '┴' },
	// Haiku: plus corners and tees, dotted runs, dotted bars.
	classic: { topLeft: '+', topRight: '+', bottomLeft: '+', bottomRight: '+', horizontal: '┈', vertical: '┊', teeDown: '+', teeUp: '+' },
	singleDouble: { topLeft: '╓', topRight: '╖', bottomLeft: '╙', bottomRight: '╜', horizontal: '─', vertical: '║', teeDown: '╥', teeUp: '╨' },
}

/** The glyphs for a frame's border style; an unknown style draws as Haiku's plain frame. */
export const glyphsFor = (borderStyle: string): Glyphs => GLYPHS[borderStyle] ?? GLYPHS.classic!

/** The top or bottom rule of a band split into ranges of `widths` cells: a tee wherever a divider meets it. */
export const bandRule = (borderStyle: string, edge: 'top' | 'bottom', widths: readonly number[]): string => {
	const g = glyphsFor(borderStyle)
	const [left, right, tee] = edge === 'top' ? [g.topLeft, g.topRight, g.teeDown] : [g.bottomLeft, g.bottomRight, g.teeUp]
	return left + widths.map(w => g.horizontal.repeat(w)).join(tee) + right
}
