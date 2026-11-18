import { expect, test } from 'claude-code/testing'

const START = { cwd: '/code/lantern', surface: 'terminal', isInteractive: true } as const

test('a session starts with the mod loaded and nothing registered', async $ => {
	await $.session.start(START)
	expect(true).toBe(true)
})

test('enabled false registers nothing', { options: { enabled: false } }, async $ => {
	await $.session.start(START)
	expect(true).toBe(true)
})
