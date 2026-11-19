import { expect, test } from 'claude-code/testing'

const START = { cwd: '/code/lantern', surface: 'terminal', isInteractive: true } as const

// What answers session.start beneath the plugin. The mod registers nothing in
// this slice, switched on or off, so both tests can only show that loading it
// leaves a session start untouched; the switch gets a real test once the mod
// has a handler to switch off.
const beneath = async (_$: unknown, e: { cwd: string }) => ({ cwd: e.cwd })

test('switched on, the mod leaves a session start untouched', async ($, on) => {
	on('session.start', beneath)
	expect(await $.session.start(START)).toEqual({ cwd: '/code/lantern' })
})

test('switched off, the mod leaves a session start untouched', { options: { enabled: false } }, async ($, on) => {
	on('session.start', beneath)
	expect(await $.session.start(START)).toEqual({ cwd: '/code/lantern' })
})
