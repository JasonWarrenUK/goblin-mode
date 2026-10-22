// The state contract for the roadmap plugin's pane mod: the pane draws from a
// snapshot the CLI produced, the row the person picked, the task that is
// waiting for an assignee and how this person groups the ready set.

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

/** What the ready set is split by: the assignee, the milestone, the release tier, or nothing. */
export type GroupBy = 'dev' | 'milestone' | 'tier' | 'none'

/**
 * How this person likes the ready set split: the key it is grouped by and
 * which subgroups lead, in order. Kept in the plugin's store, so each dev's
 * own machine remembers it and Jaz's pane can lead with Jaz while Jason's
 * leads with Jason.
 */
export type Grouping = {
	by: GroupBy
	first: string[]
}

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
			grouping: Grouping | null
			ordering: boolean
		}
	}
}
