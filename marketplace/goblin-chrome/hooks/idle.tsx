// The idle goblin (28): a Client surface module that animates in the band.
// It paces while nothing happens, sits after five minutes, sleeps after ten,
// startles when a prompt goes in, watches while Claude works, and can be
// poked with the pointer. While a skill runs it holds that family's prop,
// and each subagent out stands beside it as a minion. No `$` here: the hooks
// module hands it props and reads its posts.
//
// Every change of state happens on the frame clock or on a pointer event,
// never while drawing: a draw that wrote state would schedule another draw
// that wrote again, and the engine unmounts a module that does that.

import type { ClientModule } from 'claude-code'

import { cells } from './text'

export type IdleProps = {
	mode: 'idle' | 'working'
	idleMs: number
	pace: 'lie' | 'sway' | 'slow' | 'normal' | 'sit' | 'fast' | 'grin' | 'lively' | 'feral'
	startleAt: number
	colour: string
	dim: string
	/** The object held while a skill runs, by its family; empty for none. */
	prop: string
	/** The faces of the subagents out, oldest first. */
	minions: readonly string[]
	minionColour: string
}

type Pose = 'pace' | 'sit' | 'sleep' | 'startle' | 'watch' | 'poked' | 'lie'

type State = {
	tick: number
	x: number
	dir: 1 | -1
	seenStartle: number
	pokedUntil: number
	startledUntil: number
}

const SIT_AFTER = 5 * 60_000
const SLEEP_AFTER = 10 * 60_000
export const TICK_MS = 120

/** Milliseconds per step of the walk, by the day's pace. */
export const STEP: Record<IdleProps['pace'], number> = {
	lie: 2_000,
	sway: 900,
	slow: 700,
	normal: 420,
	sit: 600,
	fast: 280,
	grin: 320,
	lively: 220,
	feral: 140,
}

const FACE = '(ಠ_ಠ)'
const BLINK = '(-_-)'

const SPRITES = {
	sit: '(ಠ‿ಠ)  ',
	sleep: ['(-_-) z ', '(-_-) zZ', '(-_-)zZz'],
	startle: '(ಠoಠ)! ',
	poked: '(ಠ_ಠ)  ',
	lie: '_(-_-)_',
	sway: ['(ಠ_ಠ)~', '~(ಠ_ಠ)'],
} as const

/** The cells a sprite takes without a prop; every sprite above pads to it. */
const WIDTH = 8

/** How many minions stand in the band before the rest are a count. */
export const MINIONS_SHOWN = 3

const MIRROR: Record<string, string> = { '<': '>', '>': '<', '[': ']', ']': '[', '(': ')', ')': '(', '/': '\\', '\\': '/' }

/** A prop as held in the other hand: the glyphs reversed, the handed ones swapped. */
export const mirrorProp = (prop: string): string =>
	Array.from(prop)
		.reverse()
		.map(ch => MIRROR[ch] ?? ch)
		.join('')

/** The parade's text: up to `MINIONS_SHOWN` faces a space apart, then `+n` for the rest; empty when none are out. */
export const paradeText = (minions: readonly string[]): string => {
	if (minions.length === 0) return ''
	const shown = minions.slice(0, MINIONS_SHOWN).join(' ')
	const rest = minions.length - MINIONS_SHOWN
	return rest > 0 ? `${shown} +${rest}` : shown
}

/** The cells the goblin needs: its sprite width plus the prop, and the parade with its gap. */
export const footprint = (props: Pick<IdleProps, 'prop' | 'minions'>): { sprite: number; parade: number } => {
	const parade = paradeText(props.minions)
	return { sprite: WIDTH + cells(props.prop), parade: parade === '' ? 0 : cells(parade) + 1 }
}

const poseFor = (props: IdleProps, state: State, now: number): Pose => {
	if (state.pokedUntil > now) return 'poked'
	if (state.startledUntil > now) return 'startle'
	if (props.mode === 'working') return 'watch'
	if (props.pace === 'lie') return 'lie'
	if (props.idleMs >= SLEEP_AFTER) return 'sleep'
	if (props.idleMs >= SIT_AFTER || props.pace === 'sit') return 'sit'
	return 'pace'
}

/** Whether a step of `stepMs` falls in the tick that ends at `now`. */
export const stepsAt = (now: number, stepMs: number): boolean =>
	now > 0 && Math.floor(now / stepMs) !== Math.floor((now - TICK_MS) / stepMs)

/** The cells the goblin can pace across: the room less the parade and its own footprint. */
const roomFor = (props: Pick<IdleProps, 'prop' | 'minions'>, columns: number): number => {
	const f = footprint(props)
	return Math.max(0, columns - f.parade - f.sprite)
}

/** One tick of the clock: the next state from the last, the props as last drawn and the room. */
export const advance = (state: State, props: IdleProps, columns: number): State => {
	const tick = state.tick + 1
	const now = tick * TICK_MS
	let { seenStartle, startledUntil, x, dir } = state
	if (props.startleAt > seenStartle) {
		seenStartle = props.startleAt
		startledUntil = now + 1_200
	}
	const next: State = { ...state, tick, seenStartle, startledUntil }
	if (poseFor(props, next, now) === 'pace' && stepsAt(now, STEP[props.pace])) {
		const room = roomFor(props, columns)
		x += dir
		if (x >= room) {
			x = room
			dir = -1
		}
		if (x <= 0) {
			x = 0
			dir = 1
		}
	}
	return { ...next, x, dir }
}

/** The sprite for a pose: the face with its prop in the hand it walks with, or the pose's own drawing. */
export const spriteFor = (pose: Pose, props: Pick<IdleProps, 'pace' | 'prop'>, dir: 1 | -1, beat: number): string => {
	switch (pose) {
		case 'sit':
			return props.prop === '' ? SPRITES.sit : `(ಠ‿ಠ)${props.prop}`
		case 'sleep':
			return SPRITES.sleep[beat % SPRITES.sleep.length] ?? SPRITES.sleep[0]
		case 'startle':
			return SPRITES.startle
		case 'poked':
			return SPRITES.poked
		case 'lie':
			return SPRITES.lie
		case 'watch': {
			const face = beat % 3 === 2 ? BLINK : FACE
			return `${face}${props.prop}`
		}
		case 'pace':
			if (props.pace === 'sway') return SPRITES.sway[beat % SPRITES.sway.length] ?? SPRITES.sway[0]
			if (props.prop === '') return dir === 1 ? `${FACE}>` : `<${FACE}`
			return dir === 1 ? `${FACE}${props.prop}` : `${mirrorProp(props.prop)}${FACE}`
	}
}

// The props as last drawn, for the tick to read; a module variable is fine
// here, since a reload of the plugin drops this environment with its timer.
let latest: IdleProps | null = null

const Goblin: ClientModule<IdleProps, State> = (props, surface) => {
	latest = props
	const { Box, Text } = surface.elements
	let state = surface.state
	if (state === undefined) {
		const initial: State = { tick: 0, x: 0, dir: 1, seenStartle: props.startleAt, pokedUntil: 0, startledUntil: 0 }
		surface.every(TICK_MS, () => {
			surface.setState(advance(surface.state ?? initial, latest ?? props, surface.columns))
		})
		surface.onPointer(e => {
			if (e.type !== 'down') return
			const s = surface.state ?? initial
			surface.setState({ ...s, pokedUntil: s.tick * TICK_MS + 1_500 })
			surface.post({ poke: true })
		})
		// Persist at once, so a second draw before the first tick starts nothing twice.
		surface.setState(initial)
		state = initial
	}
	const now = state.tick * TICK_MS
	const pose = poseFor(props, state, now)
	const beat = Math.floor(now / 600)
	const sprite = spriteFor(pose, props, state.dir, beat)
	const parade = paradeText(props.minions)
	const room = roomFor(props, surface.columns)
	const left = pose === 'pace' ? Math.min(state.x, room) : pose === 'watch' ? room : 0
	return (
		<Box flexDirection="row" width={surface.columns || footprint(props).sprite}>
			{parade !== '' && <Text color={props.minionColour}>{`${parade} `}</Text>}
			{left > 0 && <Text>{' '.repeat(left)}</Text>}
			<Text color={pose === 'sleep' || pose === 'lie' ? props.dim : props.colour} bold={pose === 'startle' || pose === 'poked'}>
				{sprite}
			</Text>
		</Box>
	)
}

export default Goblin
