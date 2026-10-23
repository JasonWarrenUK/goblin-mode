// The state contract for the mission-control mod: the board draws from a
// snapshot the CLI produced (`mc.py status --json`), the row the person picked
// and the input the pane is waiting on.

export type Coordinator = {
	session_id: string
	name: string
	socket: string | null
}

export type CrewPlan = {
	task: string
	branch: string
	worktree: string | null
	brief: string
	migration: string | null
}

export type Assumption = {
	n: number
	text: string
	changed_at: number | null
}

export type Need = {
	id: string
	n: number
	session_id: string
	task: string
	why: string
	command: string
	cwd: string
	status: string
}

export type Run = {
	name: string
	started_at: number
	coordinator: Coordinator
	base: { branch: string; commit: string }
	crew: CrewPlan[]
	assumptions: Assumption[]
}

export type SessionRow = {
	session_id: string
	name: string
	task: string
	branch: string
	worktree: string
	state: string
	summary: string
	pr: number | null
	live: boolean
	live_status: string
	updated_at: number
}

export type Slot = {
	resource: string
	holder: string
	holder_task: string
	holder_name: string
	granted_at: number
	until: number
	what: string
	overdue: boolean
}

export type SlotRequest = {
	resource: string
	session_id: string
	task: string
	name: string
	minutes: number | null
	what: string
	at: number
}

export type Probe = {
	resource: string
	busy: boolean
	checks: { kind: string; detail: string; busy?: boolean }[]
}

/** Why the pane has no run to draw: no project config, no active run, or a CLI that refused or could not run. */
export type Problem = 'none' | 'no-config' | 'no-run' | 'broken'

export type Snapshot = {
	ok: boolean
	problem: Problem
	reason: string
	configPath: string
	ledgerDir: string
	mainCheckout: string
	run: Run | null
	sessions: SessionRow[]
	slots: Slot[]
	requests: SlotRequest[]
	needs: Need[]
	probes: Probe[]
	at: number
}

/** This session as the run sees it, held in state so a hot reload keeps it. */
export type Self = {
	sessionId: string
	isCoordinator: boolean
	isCrew: boolean
}

/** What the pane is waiting on: a grant's minutes for a request, or a note for a release. */
export type Asking = {
	kind: 'grant' | 'release' | 'done'
	resource: string
	sessionId: string
	ref: string
}

declare module 'claude-code' {
	interface PluginState {
		'mission-control': {
			snapshot: Snapshot | null
			self: Self
			selected: string | null
			asking: Asking | null
		}
	}
}
