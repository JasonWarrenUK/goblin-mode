import { describe, expect, test } from 'claude-code/testing'

import { dayAt, DEFAULT_SCHEDULE, LADDER, offset, parseSchedule, shift, slotAt, STYLE } from './day'

const at = (y: number, m: number, d: number, h: number, min = 0): Date => new Date(y, m - 1, d, h, min)

describe('schedule', () => {
	test('the default parses to nine slots in clock order', async () => {
		const slots = parseSchedule(DEFAULT_SCHEDULE)
		expect(slots).toHaveLength(9)
		expect(slots[0]).toEqual({ minute: 60, state: 'feral' })
		expect(slots[8]).toEqual({ minute: 22 * 60, state: 'prime' })
	})

	test('a malformed schedule falls back to the default whole', async () => {
		expect(parseSchedule('09=grumpy,25=prime')).toEqual(parseSchedule(DEFAULT_SCHEDULE))
		expect(parseSchedule('09=sleepy')).toEqual(parseSchedule(DEFAULT_SCHEDULE))
	})

	test('minutes are accepted and the latest slot wins', async () => {
		const slots = parseSchedule('08:30=grumpy,12=functional')
		expect(slotAt(slots, 8 * 60 + 29).now.state).toBe('functional')
		expect(slotAt(slots, 8 * 60 + 30).now.state).toBe('grumpy')
		expect(slotAt(slots, 12 * 60).now.state).toBe('functional')
	})

	test('before the first slot the day wraps to the last', async () => {
		const slots = parseSchedule(DEFAULT_SCHEDULE)
		const { now, since } = slotAt(slots, 0)
		expect(now.state).toBe('prime')
		expect(since).toBe(120)
	})
})

describe('offsets', () => {
	test('a Wednesday afternoon in a fresh session shifts nothing', async () => {
		expect(offset(at(2026, 10, 7, 15), 0)).toBe(0)
	})

	test('Friday from four shifts one towards lively, Sunday one towards tired', async () => {
		expect(offset(at(2026, 10, 9, 16), 0)).toBe(1)
		expect(offset(at(2026, 10, 9, 15), 0)).toBe(0)
		expect(offset(at(2026, 10, 11, 12), 0)).toBe(-1)
	})

	test('a session past four hours shifts one towards tired and the ladder clamps', async () => {
		expect(offset(at(2026, 10, 7, 15), 5 * 3_600_000)).toBe(-1)
		expect(shift('bed', -1)).toBe('bed')
		expect(shift('feral', 1)).toBe('feral')
		expect(shift('functional', 1)).toBe('second')
		expect(LADDER).toHaveLength(9)
	})
})

describe('dayAt', () => {
	const slots = parseSchedule(DEFAULT_SCHEDULE)

	test('states follow the clock', async () => {
		expect(dayAt(slots, at(2026, 10, 7, 9), 0)).toMatchObject({ state: 'grumpy' })
		expect(dayAt(slots, at(2026, 10, 7, 23), 0)).toMatchObject({ state: 'prime' })
		expect(dayAt(slots, at(2026, 10, 7, 2), 0)).toMatchObject({ state: 'feral' })
	})

	test('the fade runs over ten minutes from the previous state', async () => {
		expect(dayAt(slots, at(2026, 10, 7, 14, 0), 0)).toMatchObject({ state: 'slump', from: 'functional', blend: 0 })
		expect(dayAt(slots, at(2026, 10, 7, 14, 5), 0)).toMatchObject({ blend: 0.5 })
		expect(dayAt(slots, at(2026, 10, 7, 14, 30), 0)).toMatchObject({ blend: 1 })
	})

	test('a Sunday evening prime reads as perking', async () => {
		expect(dayAt(slots, at(2026, 10, 11, 23), 0).state).toBe('perking')
	})

	test('every state has a style', async () => {
		for (const state of LADDER) expect(STYLE[state].hints.length).toBeGreaterThan(0)
	})
})
