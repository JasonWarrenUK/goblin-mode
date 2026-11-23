// Shared by scripts/generate.ts (build time) and the pages (run time), so it
// imports nothing.

export type ModKey = 'seneschal' | 'jester' | 'scout' | 'warband' | 'archivist';

/** Site key to every marketplace name the mod has gone by, newest first. */
export const MOD_NAMES: Record<ModKey, readonly [string, ...string[]]> = {
	seneschal: ['goblin-seneschal', 'goblin-util'],
	jester: ['goblin-jester', 'goblin-chrome'],
	scout: ['goblin-scout', 'roadmap'],
	warband: ['goblin-warband', 'mission-control'],
	archivist: ['goblin-archivist', 'midden'],
};

export interface CommandFact {
	/** As typed: "/scout-waypoints" or "/goblin-scout:start-roadbook". */
	invocation: string;
	description: string;
}

export interface OptionFact {
	key: string;
	title: string;
	type: string;
	default: string;
	description: string;
}

export interface ModFacts {
	key: ModKey;
	/** The name in marketplace.json today; null when the mod is not in the marketplace. */
	name: string | null;
	installable: boolean;
	version: string | null;
	installCommand: string | null;
	skills: number;
	typescriptLines: number;
	/** Slash commands the mod registers, then its skills, each with the description its own file gives. */
	commands: CommandFact[];
	/** The plugin's userConfig, from plugin.json. */
	options: OptionFact[];
}

export interface Facts {
	marketplace: { name: string; repository: string; addCommand: string };
	mods: Record<ModKey, ModFacts>;
	counts: {
		modsTotal: number;
		modsShipped: number;
		modsProposed: number;
		jesterDayStates: number;
		seneschalHeartbeatSeconds: number;
		warbandRules: number;
		/** Every SKILL.md in the repository, plugin skills included, and how many carry each metadata key. */
		metadataSkills: number;
		metadataSkillsWithFamily: number;
		metadataFamilies: number;
		metadataGlyphs: number;
		metadataSpinners: number;
	};
	build: { commit: string; date: string };
}
