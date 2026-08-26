// theme.ts: resolve a theme target file for a project, following the order
// in library/references/theme-conventions.md. Used by every asset script and
// runnable on its own:
//
//   bun theme.ts <target> [--project <dir>] [--family <name>]
//
// Prints the resolved file path (or exits 3 with a message naming the
// theme-factory invocation that would create one).

import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

const SCRIPT_DIR = new URL('.', import.meta.url).pathname;
export const GLOBAL_THEMES_DIR = resolve(SCRIPT_DIR, '../../themes');

export interface ResolvedTheme {
	path: string;
	family: string;
	target: string;
	scope: 'project' | 'global';
	block: Record<string, unknown>;
}

export function resolveTheme(target: string, projectDir: string, family: string | null): ResolvedTheme {
	const projectThemes = join(resolve(projectDir), '.claude', 'themes');
	const candidates: { path: string; scope: 'project' | 'global' }[] = [];

	if (existsSync(projectThemes)) {
		for (const file of readdirSync(projectThemes)) {
			if (!file.endsWith(`-${target}.json`)) continue;
			if (family && file !== `${family}-${target}.json`) continue;
			candidates.push({ path: join(projectThemes, file), scope: 'project' });
		}
	}

	if (candidates.length > 1) {
		const names = candidates.map((candidate) => candidate.path.split('/').pop()).join(', ');
		throw new Error(`Several ${target} themes in ${projectThemes} (${names}); name the family`);
	}

	if (candidates.length === 0) {
		if (family && family !== 'clod') {
			throw new Error(
				`No ${family}-${target}.json in ${projectThemes}. Create it with: /theme-factory "${target}" from ${family}`,
			);
		}
		const globalPath = join(GLOBAL_THEMES_DIR, `clod-${target}.json`);
		if (!existsSync(globalPath)) {
			throw new Error(`No ${target} theme anywhere. Create one with: /theme-factory "${target}"`);
		}
		candidates.push({ path: globalPath, scope: 'global' });
	}

	const chosen = candidates[0];
	const file = JSON.parse(readFileSync(chosen.path, 'utf8')) as Record<string, unknown>;
	return {
		path: chosen.path,
		family: file.family as string,
		target,
		scope: chosen.scope,
		block: file[target] as Record<string, unknown>,
	};
}

export function argValue(args: string[], flag: string): string | null {
	const index = args.indexOf(flag);
	return index >= 0 && index + 1 < args.length ? args[index + 1] : null;
}

if (import.meta.main) {
	const args = process.argv.slice(2);
	const target = args.find((arg) => !arg.startsWith('--'));
	if (!target) {
		console.error('usage: theme.ts <target> [--project <dir>] [--family <name>]');
		process.exit(1);
	}
	try {
		const resolved = resolveTheme(target, argValue(args, '--project') ?? process.cwd(), argValue(args, '--family'));
		console.log(resolved.path);
	} catch (error) {
		console.error((error as Error).message);
		process.exit(3);
	}
}
