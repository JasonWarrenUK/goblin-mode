// The idle goblin (28): a Client surface module that animates in the band.
// It paces while nothing happens, sits after five minutes, sleeps after ten,
// startles when a prompt goes in, watches while Claude works, and can be
// poked with the pointer. No `$` here: the hooks module hands it props and
// reads its posts.

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
	started: boolean
}

const SIT_AFTER = 5 * 60_000
const SLEEP_AFTER = 10 * 60_000
const TICK_MS = 120

/** Milliseconds per step of the walk, by the day's pace. */
const STEP: Record<IdleProps['pace'], number> = {
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
	left: 'ᕕ( ᐛ )ᕗ',
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

const Goblin: ClientModule<IdleProps, State> = (props, surface) => {
	const { Box, Text } = surface.elements
	const state: State = surface.state ?? {
		tick: 0,
		x: 0,
		dir: 1,
		seenStartle: props.startleAt,
		pokedUntil: 0,
		startledUntil: 0,
		started: false,
	}
	const now = state.tick * TICK_MS

	if (!state.started) {
		state.started = true
		surface.every(TICK_MS, () => {
			const s = surface.state ?? state
			surface.setState({ ...s, tick: s.tick + 1 })
		})
		surface.onPointer(e => {
			if (e.type !== 'down') return
			const s = surface.state ?? state
			surface.setState({ ...s, pokedUntil: s.tick * TICK_MS + 1_500 })
			surface.post({ poke: true })
		})
	}

	let startledUntil = state.startledUntil
	let seenStartle = state.seenStartle
	if (props.startleAt > state.seenStartle) {
		seenStartle = props.startleAt
		startledUntil = now + 1_200
	}

	const pose = poseFor(props, { ...state, startledUntil }, now)
	const room = Math.max(0, surface.columns - WIDTH)
	let { x, dir } = state
	if (pose === 'pace' && now % STEP[props.pace] < TICK_MS) {
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
	if (x !== state.x || dir !== state.dir || seenStartle !== state.seenStartle || startledUntil !== state.startledUntil) {
		surface.setState({ ...state, x, dir, seenStartle, startledUntil })
	}

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
									: dir === 1
										? SPRITES.right
										: SPRITES.left

	const left = pose === 'pace' ? x : pose === 'watch' ? room : 0
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
