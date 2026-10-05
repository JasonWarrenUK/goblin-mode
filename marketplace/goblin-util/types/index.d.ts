// The state contract for goblin-util: what the fleet pane and the pain pane
// draw from, held by the host for the session.

export type LastError = {
	tool: string
	text: string
	at: number
}

export type Heartbeat = {
	id: string
	cwd: string
	repo: string
	branch: string
	isWorking: boolean
	lastTool: string
	lastToolAt: number
	startedAt: number
	at: number
}

/** This session as the fleet sees it, held in state so a hot reload keeps it. */
export type Self = {
	sessionId: string
	startedAt: number
	isWorking: boolean
	lastTool: string
	lastToolAt: number
	beatAt: number
}

declare module 'claude-code' {
	interface PluginState {
		'goblin-util': {
			selected: string | null
			lastError: LastError | null
			branch: string
			repoName: string
			self: Self
		}
	}
}
