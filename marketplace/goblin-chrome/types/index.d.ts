// The state contract for goblin-chrome: every value the module keeps in
// `$.state`, declared so `claude plugin validate` can hold the module to it
// and a plugin that lists goblin-chrome under `dependencies` can read the
// frame and palette it publishes.

export type Tier = 'top' | 'mid' | 'small'

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
	pill: string | null
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
	context: number
	limit: number
	limitKind: string
	tools: number
	errors: number
	turnMs: number
	bounces: number
}

export type Idle = {
	lastPromptAt: number
	lastTurnEndAt: number
	sessionStartAt: number
	isWorking: boolean
	draftSince: number
}

declare module 'claude-code' {
	interface PluginState {
		'goblin-chrome': {
			palette: Palette
			day: Day
			frame: Frame
			vitals: Vitals
			idle: Idle
		}
	}
}
