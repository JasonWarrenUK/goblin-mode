import { expect, test } from 'claude-code/testing'

const START = { cwd: '/code/lantern', surface: 'terminal', isInteractive: true } as const

// What answers session.start beneath the plugin. The mod adds nothing in this
// slice, so the start comes back exactly as the layer beneath answered it.
const beneath = async (_$: unknown, e: { cwd: string }) => ({ cwd: e.cwd })

test('a session starts with the mod loaded and nothing registered', async ($, on) => {
	on('session.start', beneath)
	expect(await $.session.start(START)).toEqual({ cwd: '/code/lantern' })
})

test('enabled false registers nothing', { options: { enabled: false } }, async ($, on) => {
	on('session.start', beneath)
	expect(await $.session.start(START)).toEqual({ cwd: '/code/lantern' })
})
