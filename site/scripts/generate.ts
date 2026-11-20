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

/** The value of `key:` nested under a SKILL.md's top-level `metadata:` block, read as text the way skill-lint.py does. */
export const metadataKey = (markdown: string, key: string): string | null => {
	const head = /^---\r?\n([\s\S]*?)\r?\n---/.exec(markdown)?.[1];
	if (head === undefined) return null;
	const lines = head.split(/\r?\n/);
	const start = lines.findIndex((line) => /^metadata:\s*(#.*)?$/.test(line));
	if (start < 0) return null;
	for (const line of lines.slice(start + 1)) {
		if (/^\S/.test(line)) break;
		const hit = new RegExp(`^\\s+${key}:[ \\t]*(.*)$`).exec(line);
		if (hit) return hit[1]!.replace(/\s+#.*$/, '').trim().replace(/^(["'])(.*)\1$/, '$2') || null;
	}
	return null;
};

/** Every SKILL.md in the repository: the loose skills under skills/ and every plugin's under marketplace/. */
export const repositorySkillFiles = (repo: string): string[] => {
	const inside = (dir: string): string[] =>
		existsSync(dir) ? readdirSync(dir).map((entry) => join(dir, entry, 'SKILL.md')).filter((path) => existsSync(path)) : [];
	const plugins = existsSync(join(repo, 'marketplace')) ? readdirSync(join(repo, 'marketplace')).map((entry) => join(repo, 'marketplace', entry, 'skills')) : [];
	return [...inside(join(repo, 'skills')), ...plugins.flatMap(inside)];
};

/** The Metadata page's counts: skills, how many carry each of the repository's own keys, and the distinct families. */
export const metadataCounts = (files: readonly string[]): { skills: number; withFamily: number; families: number; glyphs: number; spinners: number } => {
	const texts = files.map((path) => readFileSync(path, 'utf8'));
	const families = texts.map((text) => metadataKey(text, 'family')).filter((value): value is string => value !== null);
	return {
		skills: texts.length,
		withFamily: families.length,
		families: new Set(families).size,
		glyphs: texts.filter((text) => metadataKey(text, 'glyph') !== null).length,
		spinners: texts.filter((text) => metadataKey(text, 'goblin-spinner') !== null).length,
	};
};

/** Slash commands a mod registers in hooks/register.tsx: `$.command.register({ name, description })`. */
export const registeredCommands = (source: string): CommandFact[] => {
	const found = new Map<string, string>();
	const add = (name: string | undefined, description: string | undefined): void => {
		if (name && !found.has(name)) found.set(name, (description ?? '').replace(/\\'/g, "'"));
	};
	// `$.command.register({ name: 'x', description: '…' })`, and a table of `{ name: 'x', verb: '…', description: '…' }`
	// entries that a loop registers (the warband's COMMANDS)
	for (const match of source.matchAll(/\{\s*name:\s*'([a-z][a-z-]*)',\s*(?:verb:\s*'[^']*',\s*)?description:\s*'((?:[^'\\]|\\.)*)'/g)) add(match[1], match[2]);
	// a name held in a constant: `const COMMAND = 'x'` then `$.command.register({ name: COMMAND, description: '…' })`
	for (const match of source.matchAll(/\$\.command\.register\(\{\s*name:\s*([A-Z_]+),\s*description:\s*'((?:[^'\\]|\\.)*)'/g)) {
		add(new RegExp(`const ${match[1]} = '([a-z][a-z-]*)'`).exec(source)?.[1], match[2]);
	}
	return [...found].map(([name, description]) => ({ invocation: `/${name}`, description }));
};

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
	const metadata = metadataCounts(repositorySkillFiles(REPO));
	if (metadata.skills === 0) fail('no SKILL.md found under skills/ or marketplace/');

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
			metadataSkills: metadata.skills,
			metadataSkillsWithFamily: metadata.withFamily,
			metadataFamilies: metadata.families,
			metadataGlyphs: metadata.glyphs,
			metadataSpinners: metadata.spinners,
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
