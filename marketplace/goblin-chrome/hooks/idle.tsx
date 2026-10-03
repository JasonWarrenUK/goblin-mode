// The idle goblin (28): a Client surface module that animates in the band.
// It paces while nothing happens, sits after five minutes, sleeps after ten,
// startles when a prompt goes in, watches while Claude works, and can be
// poked with the pointer. No `$` here: the hooks module hands it props and
// reads its posts.
//
// Every change of state happens on the frame clock or on a pointer event,
// never while drawing: a draw that wrote state would schedule another draw
// that wrote again, and the engine unmounts a module that does that.

import type { ClientModule } from 'claude-code'

export type IdleProps = {
	mode: 'idle' | 'working'
	idleMs: number
	pace: 'lie' | 'sway' | 'slow' | 'normal' | 'sit' | 'fast' | 'grin' | 'lively' | 'feral'
	startleAt: number
	colour: string
	dim: string
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

const SPRITES = {
	right: 'ᕕ( ᐛ )ᕗ',
	left: 'ᕗ( ᐛ )ᕕ',
	sit: ' (´ᐛ ) ',
	sleep: ['(-ᴗ-) z ', '(-ᴗ-) zZ', '(-ᴗ-)zZz'],
	startle: '(⊙ᐛ⊙)! ',
	watch: ['( ᐛ )  ', '( ᐖ )  '],
	poked: '(ಠ_ಠ)  ',
	lie: '_(ᐛ_)_ ',
	sway: ['ᕕ( ᐛ )ᕗ', ' ᕕ(ᐛ )ᕗ', 'ᕕ( ᐛ)ᕗ '],
} as const

const WIDTH = 8

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
		const room = Math.max(0, columns - WIDTH)
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
	const sprite =
		pose === 'sit'
			? SPRITES.sit
			: pose === 'sleep'
				? SPRITES.sleep[beat % SPRITES.sleep.length] ?? SPRITES.sleep[0]
				: pose === 'startle'
					? SPRITES.startle
					: pose === 'watch'
						? SPRITES.watch[beat % SPRITES.watch.length] ?? SPRITES.watch[0]
						: pose === 'poked'
							? SPRITES.poked
							: pose === 'lie'
								? SPRITES.lie
								: props.pace === 'sway'
									? SPRITES.sway[beat % SPRITES.sway.length] ?? SPRITES.sway[0]
									: state.dir === 1
										? SPRITES.right
										: SPRITES.left
	const room = Math.max(0, surface.columns - WIDTH)
	const left = pose === 'pace' ? Math.min(state.x, room) : pose === 'watch' ? room : 0
	return (
		<Box flexDirection="row" width={surface.columns || WIDTH}>
			{left > 0 && <Text>{' '.repeat(left)}</Text>}
			<Text color={pose === 'sleep' || pose === 'lie' ? props.dim : props.colour} bold={pose === 'startle' || pose === 'poked'}>
				{sprite}
			</Text>
		</Box>
	)
}

export default Goblin
