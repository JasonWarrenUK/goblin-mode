// The state contract for the roadmap plugin's pane mod: the pane draws from a
// snapshot the CLI produced, the row the person picked and the task that is
// waiting for an assignee.

export type Candidate = {
	id: string
	description: string
	milestone: string
	milestoneName: string
	milestoneDonePct: number
	tier: number
	tierLabel: string
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
	tier: number
	tierLabel: string
	state: string
}

/** The name the pane is waiting for: whose task, and whether the answer claims it or only assigns it. */
export type Asking = {
	id: string
	mode: 'claim' | 'assign'
}

/** Why the pane has no roadmap to draw: none above the directory, the old single-file format, or a CLI that refused or could not run. */
export type Problem = 'none' | 'missing' | 'legacy' | 'broken'

export type Snapshot = {
	ok: boolean
	problem: Problem
	reason: string
	phase: string
	donePct: number
	doneCount: number
	inScope: number
	milestones: Milestone[]
	candidates: Candidate[]
	claimed: Claimed[]
	at: number
}

declare module 'claude-code' {
	interface PluginState {
		'roadmap': {
			snapshot: Snapshot | null
			selected: string | null
			asking: Asking | null
		}
	}
}
