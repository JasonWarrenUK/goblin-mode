// The state contract for goblin-chrome: every value the module keeps in
// `$.state`, declared so `claude plugin validate` can hold the module to it
// and a plugin that lists goblin-chrome under `dependencies` can read the
// frame and palette it publishes.

export type Tier = 'top' | 'mid' | 'small' | 'fable'

export type DayState =
	| 'bed'
	| 'caught'
	| 'grumpy'
	| 'functional'
	| 'slump'
	| 'second'
	| 'perking'
	| 'prime'
	| 'feral'

export type Palette = {
	family: string
	ink: string
	inkMuted: string
	surface: string
	surfaceRaised: string
	line: string
	accent: string
	accentInk: string
	accent2: string
	ok: string
	warn: string
	danger: string
	info: string
}

export type Day = {
	state: DayState
	from: DayState
	blend: number
}

export type Frame = {
	borderStyle: string
	borderColor: string
	borderDimColor: boolean
	rune: string
	served: Tier
	pinned: Tier | null
}

export type Vitals = {
	tools: number
	errors: number
	turnMs: number
	turnTools: number
	turnErrors: number
	bounces: number
}

export type Idle = {
	lastPromptAt: number
	lastTurnEndAt: number
	sessionStartAt: number
	isWorking: boolean
	draftSince: number
	/** What the goblin last said, shown in the band's dialogue range until `sayingUntil`. */
	saying: string
	sayingUntil: number
}

/** The turn's run: the skill in flight and its frontmatter. Cleared when the main turn completes. */
export type Run = {
	/** The skill whose prompt was last expanded this turn, or null between runs. */
	skill: string | null
	/** The skill's `metadata.family`, which picks the prop the goblin holds. */
	family: string | null
	/** The skill's `metadata.goblin-spinner` words, shown in the spinner one per minute. */
	spinner: readonly string[]
}

declare module 'claude-code' {
	interface PluginState {
		'goblin-chrome': {
			palette: Palette
			day: Day
			frame: Frame
			vitals: Vitals
			idle: Idle
			run: Run
		}
	}
}
