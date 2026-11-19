// The frontmatter a skill or agent file carries, read as text: the mod has
// no YAML parser and needs five keys. Top-level scalars (`model`,
// `goblin-minion`) and the scalars nested under `metadata:` (`family`,
// `goblin-spinner`). Comments after a space-hash are dropped, quotes stripped.

import { cells } from './text'

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

/** Longest a spinner word may be, in code points: the longest in use is 23. */
export const SPINNER_WORD_MAX = 40

/**
 * A `|`-separated list, trimmed, empties dropped. Plugin authors write these
 * too, so each word loses its control and format characters (an escape would
 * reach the terminal; a bidi override would reorder the band) and its line
 * separators, and is cut to `SPINNER_WORD_MAX`.
 */
export const splitBar = (value: string | null): readonly string[] =>
	value === null
		? []
		: value
				.split('|')
				.map(s => Array.from(s.replace(/[\p{Cc}\p{Cf}\p{Zl}\p{Zp}]/gu, '').trim()).slice(0, SPINNER_WORD_MAX).join('').trim())
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

/**
 * Everything the mod reads, from the frontmatter the engine parsed itself and
 * hands to `skill.prompt`: the same three keys `readSkill` reads from text.
 */
export const fromEngine = (frontmatter: Readonly<Record<string, unknown>>): SkillFrontmatter => {
	const own = (record: Readonly<Record<string, unknown>>, key: string): string | null => {
		const value = Object.hasOwn(record, key) ? record[key] : undefined
		return typeof value === 'string' && value.trim() !== '' ? value.trim() : null
	}
	const metadata = Object.hasOwn(frontmatter, 'metadata') ? frontmatter.metadata : undefined
	const nested = typeof metadata === 'object' && metadata !== null && !Array.isArray(metadata) ? (metadata as Readonly<Record<string, unknown>>) : {}
	const model = own(frontmatter, 'model')
	return {
		model: model === 'inherit' ? null : model,
		family: own(nested, 'family'),
		spinner: splitBar(own(nested, 'goblin-spinner')),
	}
}

/** A plugin skill as the engine names it in `skill.prompt`: `<plugin>:<skill directory>`, never the frontmatter `name`. */
export type PluginSkill = { plugin: string; dir: string }

/** The plugin and skill directory of a plugin skill's name, or null for a personal or project skill. */
export const pluginSkill = (skill: string): PluginSkill | null => {
	const colon = skill.indexOf(':')
	if (colon <= 0 || colon === skill.length - 1) return null
	return { plugin: skill.slice(0, colon), dir: skill.slice(colon + 1) }
}

/** How Claude Code ranks install scopes: local overrides project, project overrides user. */
const SCOPE_RANK: Readonly<Record<string, number>> = { local: 0, project: 1 }

/** True when `dir` is `project` or lies beneath it, a trailing slash on either side aside. */
const within = (dir: string, project: string): boolean => {
	const base = project.replace(/\/+$/, '')
	return dir === base || dir.startsWith(`${base}/`)
}

/**
 * Where an installed plugin's skill may live, from the text of
 * `~/.claude/plugins/installed_plugins.json`: `<installPath>/skills/<dir>/SKILL.md`
 * for each install of a key named `<plugin>@<marketplace>`, best first. A
 * local or project install counts only when the session's project root lies
 * within its `projectPath`; local ranks before project, the most specific
 * path first, and user installs follow in the file's order. Anything
 * unreadable, of another shape or climbing out of the install names nowhere.
 */
export const pluginSkillPaths = (installedJson: string, skill: PluginSkill, root: string): readonly string[] => {
	if (skill.dir.includes('/') || skill.dir.includes('\\') || skill.dir === '.' || skill.dir === '..') return []
	let parsed: unknown
	try {
		parsed = JSON.parse(installedJson)
	} catch {
		return []
	}
	const plugins = (parsed as { plugins?: unknown } | null)?.plugins
	if (typeof plugins !== 'object' || plugins === null || Array.isArray(plugins)) return []
	const found: { path: string; rank: number; depth: number; order: number }[] = []
	for (const [key, installs] of Object.entries(plugins)) {
		if (key.split('@')[0] !== skill.plugin || !Array.isArray(installs)) continue
		for (const install of installs) {
			const { installPath, scope, projectPath } = (install ?? {}) as { installPath?: unknown; scope?: unknown; projectPath?: unknown }
			if (typeof installPath !== 'string' || installPath === '') continue
			const rank = typeof scope === 'string' && Object.hasOwn(SCOPE_RANK, scope) ? (SCOPE_RANK[scope] as number) : 2
			// any install bound to a project path (whatever its scope's name) applies only within that project
			if ((rank < 2 || (projectPath !== undefined && projectPath !== null)) && (typeof projectPath !== 'string' || projectPath === '' || !within(root, projectPath))) continue
			found.push({
				path: `${installPath}/skills/${skill.dir}/SKILL.md`,
				rank,
				depth: rank < 2 ? (projectPath as string).length : 0,
				order: found.length,
			})
		}
	}
	return found.sort((a, b) => a.rank - b.rank || b.depth - a.depth || a.order - b.order).map(f => f.path)
}

/** Widest a minion's face may be, in terminal cells. */
export const MINION_MAX_WIDTH = 5

/**
 * The `goblin-minion:` face of an agent file, or null when absent or unusable.
 * A face is one to five terminal cells of BMP text, a wide glyph counting
 * two, so the band's arithmetic holds; an emoji or a blank is refused.
 */
export const readMinionFace = (markdown: string): string | null => {
	const block = frontmatterBlock(markdown)
	if (block === null) return null
	const face = topLevel(block, 'goblin-minion')
	if (face === null) return null
	if (cells(face) > MINION_MAX_WIDTH) return null
	if (Array.from(face).some(ch => (ch.codePointAt(0) ?? 0) > 0xffff || /\s/.test(ch))) return null
	return face
}
