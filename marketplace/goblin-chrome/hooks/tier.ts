// Borders by tier (36): the frame every mod-drawn box takes from the model
// that served the current request, and the rune of the tier a skill pinned.

import type { Frame, Palette, Tier } from '../types'

/** The runic glyph convention from clod-config-skill_conventions. Fable has no rune of its own and wears othala. */
export const RUNE: Record<Tier, string> = { top: 'ᛟ', mid: 'ᛊ', small: 'ᚺ' }

/** Which tier a model id or alias belongs to; unknown ids count as the middle. */
export const tierOf = (model: string): Tier => {
	const m = model.toLowerCase()
	if (/haiku/.test(m)) return 'small'
	if (/sonnet/.test(m)) return 'mid'
	if (/opus|fable|mythos/.test(m)) return 'top'
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
	top: { borderStyle: 'double', dim: false },
	mid: { borderStyle: 'round', dim: false },
	small: { borderStyle: 'classic', dim: true },
}

export const frameFor = (served: Tier, pinned: Tier | null, palette: Palette): Frame => {
	const mismatch = pinned !== null && pinned !== served
	const style = STYLE[served]
	return {
		borderStyle: mismatch ? 'singleDouble' : style.borderStyle,
		borderColor: mismatch ? palette.warn : served === 'small' ? palette.line : palette.accent,
		borderDimColor: style.dim,
		rune: mismatch ? `${RUNE[pinned]}→${RUNE[served]}` : RUNE[served],
		served,
		pinned,
	}
}

export const DEFAULT_TIER: Tier = 'top'
