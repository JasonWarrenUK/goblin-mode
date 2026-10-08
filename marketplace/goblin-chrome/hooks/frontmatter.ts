// The frontmatter a skill or agent file carries, read as text: the mod has
// no YAML parser and needs five keys. Top-level scalars (`model`,
// `goblin-minion`) and the scalars nested under `metadata:` (`family`,
// `goblin-spinner`). Comments after a space-hash are dropped, quotes stripped.

export type SkillFrontmatter = {
	/** The `model:` line, or null when absent or `inherit`. */
	model: string | null
	/** `metadata.family`, the skill's family prefix. */
	family: string | null
	/** `metadata.goblin-spinner`, split on `|` and trimmed. */
	spinner: readonly string[]
}

/** The text between the opening and closing `---` rules, or null when the file has none. */
export const frontmatterBlock = (markdown: string): string | null => {
	const fm = /^---\r?\n([\s\S]*?)\r?\n---/.exec(markdown)
	return fm?.[1] ?? null
}

/** A YAML plain or quoted scalar without its trailing comment or quotes; an empty value is null. */
const scalar = (raw: string): string | null => {
	const noComment = raw.replace(/\s+#.*$/, '').trim()
	const unquoted = /^(["'])(.*)\1$/.exec(noComment)?.[2] ?? noComment
	return unquoted === '' ? null : unquoted
}

/** The value of a top-level `key:` line in a frontmatter block. */
export const topLevel = (block: string, key: string): string | null => {
	const line = new RegExp(`^${key}:[ \\t]*(.*)$`, 'm').exec(block)
	return line?.[1] === undefined ? null : scalar(line[1])
}

/** The lines indented under a top-level `metadata:` key, up to the next unindented line. */
const metadataLines = (block: string): string[] => {
	const lines = block.split(/\r?\n/)
	const start = lines.findIndex(l => /^metadata:\s*(#.*)?$/.test(l))
	if (start === -1) return []
	const out: string[] = []
	for (const line of lines.slice(start + 1)) {
		if (/^\S/.test(line)) break
		out.push(line)
	}
	return out
}

/** The value of a `key:` line nested under `metadata:`. */
export const metadataKey = (block: string, key: string): string | null => {
	const re = new RegExp(`^\\s+${key}:[ \\t]*(.*)$`)
	for (const line of metadataLines(block)) {
		const hit = re.exec(line)
		if (hit?.[1] !== undefined) return scalar(hit[1])
	}
	return null
}

/** A `|`-separated list, trimmed, empties dropped. */
export const splitBar = (value: string | null): readonly string[] =>
	value === null
		? []
		: value
				.split('|')
				.map(s => s.trim())
				.filter(s => s.length > 0)

/** Everything the mod reads from a SKILL.md. A file without frontmatter reads as nothing set. */
export const readSkill = (markdown: string): SkillFrontmatter => {
	const block = frontmatterBlock(markdown)
	if (block === null) return { model: null, family: null, spinner: [] }
	const model = topLevel(block, 'model')
	return {
		model: model === 'inherit' ? null : model,
		family: metadataKey(block, 'family'),
		spinner: splitBar(metadataKey(block, 'goblin-spinner')),
	}
}

/** Widest a minion's face may be, in cells. */
export const MINION_MAX_WIDTH = 5

/**
 * The `goblin-minion:` face of an agent file, or null when absent or unusable.
 * A face is one to five cells of single-width BMP text, so the band's
 * arithmetic holds; anything else (an emoji, a blank) is refused.
 */
export const readMinionFace = (markdown: string): string | null => {
	const block = frontmatterBlock(markdown)
	if (block === null) return null
	const face = topLevel(block, 'goblin-minion')
	if (face === null) return null
	const chars = Array.from(face)
	if (chars.length > MINION_MAX_WIDTH) return null
	if (chars.some(ch => (ch.codePointAt(0) ?? 0) > 0xffff || /\s/.test(ch))) return null
	return face
}
