// The shape of each mod's page content (src/lib/content/mod-files.ts).
//
// Strings may hold inline <code>…</code> and nothing else in the way of markup;
// they are rendered as HTML. A count of anything in the repository is never
// written as a number or a word: it is a placeholder the page fills from the
// generated facts when it renders.
//
//   {seneschalHeartbeatSeconds}  the seneschal's heartbeat default, in seconds
//   {jesterDayStates}            the jester's day states ("nine moods")
//   {jesterLines}                lines of shipped TypeScript in the jester
//   {scoutSkills}                skills in goblin-scout
//   {warbandRules}               the warband README's "Do not" rules
//
// Written lower-case they render as words up to twenty ("fifteen"), digits
// above ("1,281"). Capitalise the first letter ({ScoutSkills}) to start a
// sentence ("Twelve").

import type { ModKey } from '#lib/mod-names.ts';

export interface Situation {
	/** "III.2" */
	num: string;
	/** Fragment id: "iii-2" */
	id: string;
	title: string;
	/** When it applies: "When choosing the next waypoint on a shared project" */
	hint: string;
	scene: string;
	/** The goblin's "How Human Suffer Before" list. */
	before: string[];
	/** "With goblin-scout" */
	withHeading: string;
	/** The plain instruction slip: what the mod does about it. */
	with: string[];
	/** The goblin's ruling. */
	ruling: string;
	/** True when nothing in the scene is built yet: its spec exists, its code does not. The summary carries a stamp. */
	planned?: boolean;
}

export interface RosterRow {
	/** True when a situation on the page shows this capability. */
	shown: boolean;
	text: string;
	/** The situation's num ("III.2"), or null when no situation shows it. */
	where: string | null;
	/** True when the capability is specified but not built yet. */
	planned?: boolean;
}

export interface HowTo {
	/** Paragraphs after the generated install commands: requirements, first run, how to tell it works. */
	firstRun: string[];
	/** Paragraphs before the generated options table: what can be set and where. */
	configure: string[];
	/** Paragraphs: the off switch, uninstalling and what stays behind. */
	remove: string[];
}

export interface ModFile {
	key: ModKey;
	/** The mod's README opener, quoted on the front page; null until one is settled. */
	persona: string | null;
	situations: Situation[];
	roster: RosterRow[];
	/** Null for a mod that cannot be installed yet. */
	howTo: HowTo | null;
	/**
	 * Commands the copy names that the mod's spec holds but its code does not register yet. Each is
	 * stamped where it appears outside a planned scene, and the content test fails once one ships.
	 */
	plannedCommands?: string[];
}
