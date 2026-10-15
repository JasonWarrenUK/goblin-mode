#!/usr/bin/env node
// open-states.ts: find every openable state on each route, open it and
// measure whether any toolbar's controls moved (principle 4). Node, not Bun:
// Playwright's launch path has a history of hanging under Bun.
//
//   node --experimental-strip-types open-states.ts --base URL-or-dir \
//     --routes '{"home":"/","document":"/documents/5"}' \
//     --devices '{"phone":390,"desktop":1440}' [--out states.json] [--wait 800]
//
// --base is a served origin (http://localhost:5173) or a directory of HTML
// files, in which case each route path is a file under it. Output: JSON,
// one entry per route × device × openable element, with the JS that opens
// it again under shot-scraper and the toolbar controls that moved.

import { chromium, type Page } from 'playwright';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

interface Moved { toolbar: string; control: string; before: number[]; after: number[] }
interface State {
	route: string;
	device: string;
	width: number;
	specifier: string;
	kind: 'details' | 'expanded' | 'popup' | 'controls';
	name: string;
	selector: string;
	javascript: string;
	toolbarMoved: Moved[];
}

function argValue(args: string[], flag: string): string | null {
	const index = args.indexOf(flag);
	return index >= 0 ? args[index + 1] ?? null : null;
}

function slug(text: string): string {
	return text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'state';
}

// Page-side globals; this file runs under Node with no DOM types.
declare const document: any;
declare const window: any;
declare const getComputedStyle: any;
declare const CSS: any;

// Runs in the page: list openable triggers with a stable CSS path each.
const DISCOVER = () => {
	const path = (el: any) => {
		const parts: string[] = [];
		while (el && el.nodeType === 1 && el !== document.body) {
			let part = el.tagName.toLowerCase();
			if (el.id) { parts.unshift('#' + CSS.escape(el.id)); break; }
			const siblings = Array.from(el.parentNode.children).filter(s => s.tagName === el.tagName);
			if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(el) + 1) + ')';
			parts.unshift(part);
			el = el.parentNode;
		}
		return parts.join(' > ');
	};
	const name = (el: any) => (el.getAttribute('aria-label') || el.textContent || el.id || '').trim().replace(/\s+/g, ' ').slice(0, 60);
	const out: { kind: string; selector: string; name: string }[] = [];
	for (const d of document.querySelectorAll('details:not([open])')) {
		const s = d.querySelector('summary');
		out.push({ kind: 'details', selector: path(d), name: name(s || d) });
	}
	for (const el of document.querySelectorAll('[aria-expanded="false"]')) out.push({ kind: 'expanded', selector: path(el), name: name(el) });
	for (const el of document.querySelectorAll('[aria-haspopup]:not([aria-expanded])')) out.push({ kind: 'popup', selector: path(el), name: name(el) });
	for (const el of document.querySelectorAll('[aria-controls]:not([aria-expanded]):not([aria-haspopup])')) {
		const target = document.getElementById(el.getAttribute('aria-controls'));
		if (target && (target.hidden || getComputedStyle(target).display === 'none')) out.push({ kind: 'controls', selector: path(el), name: name(el) });
	}
	return out;
};

// Runs in the page with the trigger's selector: every toolbar's controls
// with their boxes, plus whether the bar holds the trigger and where its
// top sits, so a bar that merely got pushed down from above is not judged.
const TOOLBARS = (triggerSelector: string) => {
	const path = (el: any) => {
		const parts: string[] = [];
		while (el && el.nodeType === 1 && el !== document.body) {
			let part = el.tagName.toLowerCase();
			if (el.id) { parts.unshift('#' + CSS.escape(el.id)); break; }
			const siblings = Array.from(el.parentNode.children).filter(s => s.tagName === el.tagName);
			if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(el) + 1) + ')';
			parts.unshift(part);
			el = el.parentNode;
		}
		return parts.join(' > ');
	};
	const trigger = document.querySelector(triggerSelector);
	const triggerTop = trigger ? trigger.getBoundingClientRect().y + window.scrollY : 0;
	const bars = document.querySelectorAll('[role="toolbar"], .toolbar, .actions, .row-actions, [class*="toolbar"], [class*="-actions"]');
	const out: Record<string, { judged: boolean; controls: Record<string, number[]> }> = {};
	for (const bar of bars) {
		const key = path(bar);
		const top = bar.getBoundingClientRect().y + window.scrollY;
		const controls: Record<string, number[]> = {};
		for (const c of bar.querySelectorAll('button, a, select, input')) {
			const r = c.getBoundingClientRect();
			controls[path(c)] = [Math.round(r.x), Math.round(r.y + window.scrollY), Math.round(r.width), Math.round(r.height)];
		}
		out[key] = { judged: (trigger && bar.contains(trigger)) || top < triggerTop, controls };
	}
	return out;
};

function openScript(kind: State['kind'], selector: string): string {
	const sel = JSON.stringify(selector);
	if (kind === 'details') return `document.querySelector(${sel}).open = true`;
	return `document.querySelector(${sel}).click()`;
}

async function discover(page: Page, url: string, route: string, device: string, width: number, wait: number): Promise<State[]> {
	await page.setViewportSize({ width, height: 900 });
	await page.goto(url, { waitUntil: 'networkidle' });
	await page.waitForTimeout(wait);
	const triggers = await page.evaluate(DISCOVER) as { kind: State['kind']; selector: string; name: string }[];
	const states: State[] = [];
	const seen = new Set<string>();
	for (const trigger of triggers) {
		let specifier = slug(trigger.name) + '-open';
		while (seen.has(specifier)) specifier += '-2';
		seen.add(specifier);
		await page.goto(url, { waitUntil: 'networkidle' });
		await page.waitForTimeout(wait);
		type Bars = Record<string, { judged: boolean; controls: Record<string, number[]> }>;
		const before = await page.evaluate(TOOLBARS, trigger.selector) as Bars;
		const javascript = openScript(trigger.kind, trigger.selector);
		try {
			await page.evaluate(javascript);
		} catch {
			continue;
		}
		await page.waitForTimeout(300);
		const after = await page.evaluate(TOOLBARS, trigger.selector) as Bars;
		const toolbarMoved: Moved[] = [];
		for (const [toolbar, bar] of Object.entries(before)) {
			if (!bar.judged) continue;
			for (const [control, box] of Object.entries(bar.controls)) {
				const now = after[toolbar]?.controls[control];
				if (now && (now[0] !== box[0] || now[1] !== box[1])) toolbarMoved.push({ toolbar, control, before: box, after: now });
			}
		}
		states.push({ route, device, width, specifier, kind: trigger.kind, name: trigger.name, selector: trigger.selector, javascript, toolbarMoved });
	}
	return states;
}

async function main(): Promise<void> {
	const args = process.argv.slice(2);
	const base = argValue(args, '--base');
	const routesArg = argValue(args, '--routes');
	const devicesArg = argValue(args, '--devices');
	if (!base || !routesArg || !devicesArg) {
		console.error("usage: open-states.ts --base URL-or-dir --routes '{slug:path}' --devices '{name:width}' [--out states.json] [--wait ms]");
		process.exit(1);
	}
	const routes = JSON.parse(routesArg) as Record<string, string>;
	const devices = JSON.parse(devicesArg) as Record<string, number>;
	const wait = Number(argValue(args, '--wait') ?? 800);
	const out = argValue(args, '--out');
	const served = /^https?:\/\//.test(base);
	const browser = await chromium.launch();
	const page = await browser.newPage();
	const states: State[] = [];
	try {
		for (const [route, path] of Object.entries(routes)) {
			const url = served ? new URL(path, base).href : pathToFileURL(resolve(base, path.replace(/^\//, ''))).href;
			for (const [device, width] of Object.entries(devices)) {
				states.push(...await discover(page, url, route, device, width, wait));
			}
		}
	} finally {
		await browser.close();
	}
	const text = JSON.stringify({ base, routes, devices, states }, null, '\t') + '\n';
	if (out) {
		writeFileSync(out, text);
		console.error(`wrote ${out}: ${states.length} states, ${states.filter(s => s.toolbarMoved.length).length} with a moved toolbar`);
	} else {
		process.stdout.write(text);
	}
}

main().catch((err) => { console.error(err); process.exit(1); });
