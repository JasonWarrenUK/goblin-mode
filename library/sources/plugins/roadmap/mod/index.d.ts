// The state contract for the roadmap plugin's mod: the pane draws from a
// snapshot the CLI produced, the row the person picked and the task that is
// waiting for an assignee.

export type Candidate = {
	id: string
	description: string
	milestone: string
	milestoneName: string
	milestoneDonePct: number
	transitiveUnblocks: number
	isMilestoneSink: boolean
	assignee: string
}

export type Claimed = {
	id: string
	description: string
	assignee: string
	started: string
}

export type Milestone = {
	id: string
	name: string
	donePct: number
}

export type Snapshot = {
	ok: boolean
	reason: string
	phase: string
	donePct: number
	milestones: Milestone[]
	candidates: Candidate[]
	claimed: Claimed[]
	at: number
}

declare module 'claude-code' {
	interface PluginState {
		roadmap: {
			snapshot: Snapshot | null
			selected: string | null
			asking: string | null
		}
	}
}
