// What the front page says about each mod. Copy from the Goblin Mode Notice
// artifact (read 2026-11-18), under the November 2026 names; every count comes
// from the generated facts, never from this file.

import { MOD_FILES } from '#lib/content/mod-files.ts';
import { countWord, CountWord, MOD_NAMES, type Facts, type ModKey } from '#lib/facts.ts';

export type Schedule = 'snacks' | 'feasts';

export interface ModSummary {
	key: ModKey;
	/** The mod's name as the site writes it: the newest name it has gone by. */
	name: string;
	slug: string;
	numeral: string;
	schedule: Schedule;
	tagline: string;
	deficiency: string;
	remedy: string;
	goblin: string;
	/** The mod's README opener, quoted in its drawer; null until one is settled. */
	persona: string | null;
	shipped: boolean;
	installCommand: string | null;
}

interface Copy {
	numeral: string;
	schedule: Schedule;
	tagline: string;
	deficiency: string;
	remedy: (facts: Facts) => string;
	goblin: (facts: Facts) => string;
}

const COPY: Record<ModKey, Copy> = {
	seneschal: {
		numeral: 'I',
		schedule: 'snacks',
		tagline: 'Logs your complaints about Claude Code and keeps watch on your other sessions.',
		deficiency: 'When the tool annoys you, you are expected to get over it.',
		remedy: (f) =>
			`Grievances are filed to a JSON log with the branch attached, and every session broadcasts a heartbeat every ${countWord(f.counts.seneschalHeartbeatSeconds)} seconds. Readouts inform you of things you had been trusted to know for yourself.`,
		goblin: () =>
			'Readout tell human what human cannot be trusted to know: which worktree human is standing in, what changelog say, if comma has lapsed, who is in the files and what human did one hour ago.',
	},
	jester: {
		numeral: 'II',
		schedule: 'snacks',
		tagline: "A goblin drawn into Claude Code's interface. It changes nothing Claude does.",
		deficiency: 'The interface ships without a goblin and nobody has been held accountable.',
		remedy: (f) =>
			`A goblin with ${countWord(f.counts.jesterDayStates)} moods, a sleep schedule and props, drawn by hand in box characters. It affects nothing.`,
		goblin: (f) =>
			`Claude Code have NO goblin in it. Goblin check twice. So goblin put goblin in. Is ${f.mods.jester.typescriptLines.toLocaleString('en-GB')} line of TypeScript. It change nothing Claude does. Is COOL.`,
	},
	scout: {
		numeral: 'III',
		schedule: 'feasts',
		tagline: 'Keeps your project plan as a dependency graph that skills update for you.',
		deficiency: 'Your plan is a text file, which you are simply trusted to edit.',
		remedy: (f) =>
			`Your plan is a roadbook: a JSON dependency graph you are forbidden to edit by hand. ${CountWord(f.mods.scout.skills)} skills, a command line and a pane edit it for you.`,
		goblin: () =>
			'Plan was just list. Human edit list with own hand. ANYONE could. Goblin put stop to this. If human tick box by hand, graph untick it at next recompute. Graph always win.',
	},
	warband: {
		numeral: 'IV',
		schedule: 'feasts',
		tagline: 'Runs several Claude Code sessions on one repository without collisions.',
		deficiency: 'Any session may use the database without applying for a permit.',
		remedy: () =>
			'One session leads the others through a ledger of JSON files, timed dibs on the database and a numbered list of tribute for you to pay.',
		goblin: (f) =>
			`Four session on one repository and NOBODY in charge. Goblin fix. One session is chief. Each raider get own worktree, and dibs with time limit before it may touch database. There are ${countWord(f.counts.warbandRules)} rule. Goblin know all ${countWord(f.counts.warbandRules)}.`,
	},
	archivist: {
		numeral: 'V',
		schedule: 'feasts',
		tagline: 'Surveys your Obsidian vault and reports what is in it.',
		deficiency: 'Your notes sit in Obsidian, unread by Claude, as though they were private.',
		remedy: () =>
			'A script reads every note in your vault and files three reports on it, then Claude drafts a schema for your notes and asks you about every point.',
		goblin: () =>
			'Human vault and human code live APART. Never meet. Goblin will end this. First goblin sniff whole vault. Touch nothing. Rest of plan still in spec. Soon. Very soon.',
	},
};

export const modSummary = (facts: Facts, key: ModKey): ModSummary => {
	const copy = COPY[key];
	const name = MOD_NAMES[key][0] ?? key;
	return {
		key,
		name,
		slug: name,
		numeral: copy.numeral,
		schedule: copy.schedule,
		tagline: copy.tagline,
		deficiency: copy.deficiency,
		remedy: copy.remedy(facts),
		goblin: copy.goblin(facts),
		persona: MOD_FILES[key].persona,
		shipped: facts.mods[key].installable,
		installCommand: facts.mods[key].installCommand,
	};
};

const unbuilt = (mods: readonly ModSummary[]): string => {
	const count = mods.filter((mod) => !mod.shipped).length;
	if (count === 0) return '';
	return ` ${CountWord(count)} ${count === 1 ? 'has' : 'have'} not been built, which has not reduced ${count === 1 ? 'its' : 'their'} paperwork.`;
};

/** Each schedule's title and blurb; the counts come from the mods filed under it. */
export const SCHEDULES: Record<Schedule, { title: string; blurb: (mods: readonly ModSummary[]) => string }> = {
	snacks: {
		title: 'Snacks',
		blurb: (mods) =>
			`${CountWord(mods.length)} mods requiring almost no commitment. One files your complaints. The other is a goblin.${unbuilt(mods)}`,
	},
	feasts: {
		title: 'Feasts',
		blurb: (mods) =>
			`${CountWord(mods.length)} mods that each arrive with a config file, a protocol and a list of things you must never do.${unbuilt(mods)}`,
	},
};
