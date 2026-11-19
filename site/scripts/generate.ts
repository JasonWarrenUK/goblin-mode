#!/usr/bin/env bun
// generate.ts: everything the site states about the repository, read from the
// repository at build time so no count on a page is typed by hand.
//
//   bun scripts/generate.ts            (run from site/, before vite build)
//
// Writes, under src/lib/generated/ (gitignored):
//   facts.json  marketplace entries, versions, counts and the build commit
//   theme.css   the goblin theme's tokens, emitted by library/scripts/theme/emit.ts
//
// Mods are found through .claude-plugin/marketplace.json, so a renamed plugin is
// picked up from its new entry. Each mod is matched to the site's own key by
// its current name or the name it had before the November 2026 renames.

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { MOD_NAMES, type CommandFact, type Facts, type ModFacts, type ModKey, type OptionFact } from '../src/lib/mod-names';

const SITE = fileURLToPath(new URL('..', import.meta.url));
const REPO = resolve(SITE, '..');
const OUT = join(SITE, 'src/lib/generated');

interface MarketplaceEntry {
	name: string;
	source: string;
}

const REPOSITORY = 'JasonWarrenUK/goblin-mode';

const readJson = <T>(path: string): T => JSON.parse(readFileSync(path, 'utf8')) as T;

const git = (...args: string[]): string | null => {
	try {
		return execFileSync('git', args, { cwd: REPO, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
	} catch {
		return null;
	}
};

const walk = (dir: string): string[] =>
	readdirSync(dir).flatMap((entry) => {
		const path = join(dir, entry);
		if (entry === 'node_modules') return [];
		return statSync(path).isDirectory() ? walk(path) : [path];
	});

/** Lines of shipped TypeScript: .ts and .tsx, excluding tests and generated type stubs. */
export const typescriptLines = (pluginDir: string): number =>
	walk(pluginDir)
		.filter((path) => /\.tsx?$/.test(path) && !/\.test\.tsx?$/.test(path) && !path.includes('/types/'))
		.reduce((total, path) => total + readFileSync(path, 'utf8').split('\n').length - 1, 0);

const skillCount = (pluginDir: string): number => {
	const skills = join(pluginDir, 'skills');
	if (!existsSync(skills)) return 0;
	return readdirSync(skills).filter((entry) => existsSync(join(skills, entry, 'SKILL.md'))).length;
};

/** A frontmatter field's value from a SKILL.md, unquoted. */
const frontmatterField = (markdown: string, field: string): string => {
	const head = /^---\n([\s\S]*?)\n---/.exec(markdown)?.[1] ?? '';
	const raw = new RegExp(`^${field}:\\s*(.*)$`, 'm').exec(head)?.[1]?.trim() ?? '';
	return raw.replace(/^(["'])([\s\S]*)\1$/, '$2');
};

/** Slash commands a mod registers in hooks/register.tsx: `$.command.register({ name, description })`. */
export const registeredCommands = (source: string): CommandFact[] =>
	[...source.matchAll(/\$\.command\.register\(\{\s*name:\s*'([^']+)',\s*description:\s*'((?:[^'\\]|\\.)*)'/g)].map(
		(match) => ({ invocation: `/${match[1]}`, description: (match[2] ?? '').replace(/\\'/g, "'") }),
	);

/** The mod's commands, then its skills as /<plugin>:<skill>, each described by its own file. */
const commandsOf = (pluginDir: string, pluginName: string): CommandFact[] => {
	const register = join(pluginDir, 'hooks/register.tsx');
	const commands = existsSync(register) ? registeredCommands(readFileSync(register, 'utf8')) : [];
	const skillsDir = join(pluginDir, 'skills');
	const skills = existsSync(skillsDir)
		? readdirSync(skillsDir)
				.filter((entry) => existsSync(join(skillsDir, entry, 'SKILL.md')))
				.sort()
				.map((entry) => ({
					invocation: `/${pluginName}:${entry}`,
					description: frontmatterField(readFileSync(join(skillsDir, entry, 'SKILL.md'), 'utf8'), 'description'),
				}))
		: [];
	return [...commands, ...skills];
};

/** The plugin's userConfig as a table of options. */
const optionsOf = (manifestPath: string): OptionFact[] => {
	const manifest = readJson<{ userConfig?: Record<string, Record<string, unknown>> }>(manifestPath);
	return Object.entries(manifest.userConfig ?? {}).map(([key, option]) => ({
		key,
		title: String(option.title ?? key),
		type: String(option.type ?? ''),
		default: option.default === undefined ? '' : String(option.default),
		description: String(option.description ?? ''),
	}));
};

/** The "Do not" list in a README: every bullet that opens with a bold "Do not". */
export const doNotRules = (readme: string): number =>
	readme.split('\n').filter((line) => /^- \*\*Do not\b/.test(line)).length;

const fail = (message: string): never => {
	console.error(`generate: ${message}`);
	process.exit(1);
};

export const collect = async (): Promise<Facts> => {
	const marketplace = readJson<{ name: string; plugins: MarketplaceEntry[] }>(join(REPO, '.claude-plugin/marketplace.json'));
	const mods = {} as Record<ModKey, ModFacts>;
	const dirs = {} as Record<ModKey, string | null>;

	for (const key of Object.keys(MOD_NAMES) as ModKey[]) {
		const entry = marketplace.plugins.find((plugin) => MOD_NAMES[key].includes(plugin.name)) ?? null;
		const dir = entry ? resolve(REPO, entry.source) : null;
		dirs[key] = dir;
		const manifest = dir ? join(dir, '.claude-plugin/plugin.json') : null;
		mods[key] = {
			key,
			name: entry?.name ?? null,
			installable: entry !== null,
			version: manifest && existsSync(manifest) ? (readJson<{ version?: string }>(manifest).version ?? null) : null,
			installCommand: entry ? `claude plugin install ${entry.name}@${marketplace.name}` : null,
			skills: dir ? skillCount(dir) : 0,
			typescriptLines: dir ? typescriptLines(dir) : 0,
			commands: dir && entry ? commandsOf(dir, entry.name) : [],
			options: manifest && existsSync(manifest) ? optionsOf(manifest) : [],
		};
	}

	const jesterDir = dirs.jester ?? fail('the jester is not in marketplace.json');
	const day = (await import(join(jesterDir, 'hooks/day.ts'))) as { LADDER?: readonly string[] };
	const jesterDayStates = day.LADDER?.length ?? fail('hooks/day.ts no longer exports LADDER');

	const seneschalDir = dirs.seneschal ?? fail('the seneschal is not in marketplace.json');
	const seneschalManifest = readJson<{ userConfig?: Record<string, { default?: unknown }> }>(
		join(seneschalDir, '.claude-plugin/plugin.json'),
	);
	const heartbeat = seneschalManifest.userConfig?.heartbeat_seconds?.default;
	if (typeof heartbeat !== 'number') fail('the seneschal has no numeric heartbeat_seconds default');

	const warbandDir = dirs.warband ?? fail('the warband is not in marketplace.json');
	const warbandRules = doNotRules(readFileSync(join(warbandDir, 'README.md'), 'utf8'));
	if (warbandRules === 0) fail("the warband README has no '- **Do not' rules");

	const shipped = Object.values(mods).filter((mod) => mod.installable).length;

	return {
		marketplace: {
			name: marketplace.name,
			repository: REPOSITORY,
			addCommand: `claude plugin marketplace add ${REPOSITORY}`,
		},
		mods,
		counts: {
			modsTotal: Object.keys(mods).length,
			modsShipped: shipped,
			modsProposed: Object.keys(mods).length - shipped,
			jesterDayStates,
			seneschalHeartbeatSeconds: heartbeat as number,
			warbandRules,
		},
		build: {
			commit: git('rev-parse', '--short', 'HEAD') ?? 'unknown',
			date: new Date().toISOString().slice(0, 10),
			rootVersion: git('describe', '--tags', '--match', 'v[0-9]*', '--abbrev=0'),
		},
	};
};

const emitTheme = (): string => {
	const emitted = execFileSync(
		'bun',
		[join(REPO, 'library/scripts/theme/emit.ts'), join(REPO, '.claude/themes/goblin-html.json')],
		{ encoding: 'utf8' },
	);
	const css = emitted.replace(/^[\s\S]*?<style>\n?/, '').replace(/<\/style>\s*$/, '');
	return `/* Generated by site/scripts/generate.ts from .claude/themes/goblin-html.json. Do not edit. */\n${css}`;
};

if (import.meta.main) {
	mkdirSync(OUT, { recursive: true });
	const facts = await collect();
	writeFileSync(join(OUT, 'facts.json'), `${JSON.stringify(facts, null, '\t')}\n`);
	writeFileSync(join(OUT, 'theme.css'), emitTheme());
	console.log(
		`generate: ${facts.counts.modsShipped} shipped, ${facts.counts.modsProposed} proposed, commit ${facts.build.commit}`,
	);
}
