// Places margin callouts against the measured centres of the lines they point at
// and draws their leader lines. Runs in the browser only, after the stage renders.

const SVG = 'http://www.w3.org/2000/svg';
const GAP = 10;

const STACK_GAP = 4;

/** One leader's worth of callouts: one note, or several pointing at exactly the same lines, stacked. */
interface Item {
	notes: HTMLElement[];
	note: HTMLElement;
	pref: 'left' | 'right';
	side: 'left' | 'right';
	mid: number;
	top: number;
	bottom: number;
	h: number;
	anchor: number;
	want: number;
	y: number;
}

/** Clusters of overlapping notes sit where their total displacement is smallest. */
const resolveSide = (items: Item[], maxBottom: number): void => {
	const clusters: { items: Item[]; top: number; h: number }[] = [];
	for (const item of items) {
		clusters.push({ items: [item], top: item.want, h: item.h });
		while (clusters.length > 1) {
			const a = clusters[clusters.length - 2]!;
			const b = clusters[clusters.length - 1]!;
			if (a.top + a.h + GAP <= b.top) break;
			a.items.push(...b.items);
			a.h += GAP + b.h;
			let offset = 0;
			let sum = 0;
			for (const x of a.items) {
				sum += x.want - offset;
				offset += x.h + GAP;
			}
			a.top = sum / a.items.length;
			clusters.pop();
		}
	}
	let floor = 0;
	for (const cluster of clusters) {
		cluster.top = Math.max(cluster.top, floor);
		floor = cluster.top + cluster.h + GAP;
	}
	let ceiling = maxBottom;
	for (const cluster of [...clusters].reverse()) {
		if (cluster.top + cluster.h > ceiling) cluster.top = Math.max(0, ceiling - cluster.h);
		ceiling = cluster.top - GAP;
	}
	for (const cluster of clusters) {
		let y = cluster.top;
		for (const x of cluster.items) {
			x.y = y;
			y += x.h + GAP;
		}
	}
};

/** Undoes placeCallouts, for the layouts that list the callouts under the file. */
export const clearCallouts = (stage: HTMLElement): void => {
	stage.style.minHeight = '';
	stage.querySelector('.leaders')?.replaceChildren();
	for (const note of stage.querySelectorAll<HTMLElement>('.co')) {
		note.style.top = '';
		delete note.dataset.at;
	}
};

/**
 * Puts each callout (`.co` with data-line, data-to and data-side) beside the line it points
 * at (`.ln[data-n]`), so its leader meets the line's vertical centre. A callout whose slot is
 * taken on its own side moves to the other side when that side is free; otherwise the side's
 * callouts move the least distance needed and the leader bends. With a fixed height the
 * callouts stay inside the stage; otherwise the stage grows to hold them.
 */
export const placeCallouts = (stage: HTMLElement, fixedHeight: boolean): void => {
	stage.style.minHeight = '';
	const svg = stage.querySelector('.leaders');
	const panel = stage.querySelector('.code');
	if (!svg || !panel) return;
	const sr = stage.getBoundingClientRect();
	const pr = panel.getBoundingClientRect();
	const lineAt = (n: number): Element | null => stage.querySelector(`.ln[data-n="${n}"]`);
	const items: Item[] = [];
	const byTarget = new Map<string, Item>();
	for (const note of stage.querySelectorAll<HTMLElement>('.co')) {
		if (getComputedStyle(note).display === 'none') continue;
		const first = lineAt(Number(note.dataset.line));
		const last = lineAt(Number(note.dataset.to ?? note.dataset.line));
		const lab = note.querySelector('.lab');
		if (!first || !last || !lab) continue;
		const nr = note.getBoundingClientRect();
		// callouts on exactly the same lines stack, touching, under one leader
		const key = `${note.dataset.line}-${note.dataset.to ?? note.dataset.line}`;
		const stack = byTarget.get(key);
		if (stack) {
			stack.notes.push(note);
			stack.h += STACK_GAP + nr.height;
			stack.want = stack.mid - stack.anchor;
			continue;
		}
		const a = first.getBoundingClientRect();
		const b = last.getBoundingClientRect();
		const lr = lab.getBoundingClientRect();
		const mid = (a.top + b.bottom) / 2 - sr.top;
		const anchor = (lr.top + lr.bottom) / 2 - nr.top;
		const pref = note.dataset.side === 'right' ? 'right' : 'left';
		const item: Item = { notes: [note], note, pref, side: pref, mid, top: a.top - sr.top, bottom: b.bottom - sr.top, h: nr.height, anchor, want: mid - anchor, y: 0 };
		byTarget.set(key, item);
		items.push(item);
	}
	items.sort((a, b) => a.mid - b.mid);
	const bySide: Record<'left' | 'right', Item[]> = { left: [], right: [] };
	const clash = (list: Item[], item: Item): boolean => list.some((o) => item.want < o.want + o.h + GAP && o.want < item.want + item.h + GAP);
	for (const item of items) {
		const other = item.pref === 'left' ? 'right' : 'left';
		item.side = clash(bySide[item.pref], item) && !clash(bySide[other], item) ? other : item.pref;
		bySide[item.side].push(item);
	}
	const maxBottom = fixedHeight ? stage.clientHeight : Infinity;
	// when one side's notes are taller than the stage, move notes across while the other side has
	// room: an earlier step's compact note first, then the smallest
	const total = (list: Item[]): number => list.reduce((sum, item) => sum + item.h + GAP, 0);
	for (const side of ['left', 'right'] as const) {
		const other = side === 'left' ? 'right' : 'left';
		const movable = [...bySide[side]].sort((a, b) => Number(b.notes.every((n) => n.classList.contains('past'))) - Number(a.notes.every((n) => n.classList.contains('past'))) || a.h - b.h);
		for (const item of movable) {
			if (total(bySide[side]) <= maxBottom) break;
			if (total(bySide[other]) + item.h + GAP > maxBottom) continue;
			bySide[side] = bySide[side].filter((x) => x !== item);
			bySide[other] = [...bySide[other], item].sort((a, b) => a.mid - b.mid);
			item.side = other;
		}
	}
	resolveSide(bySide.left, maxBottom);
	resolveSide(bySide.right, maxBottom);
	let lowest = pr.bottom - sr.top;
	for (const item of items) {
		let y = item.y;
		for (const note of item.notes) {
			note.dataset.at = item.side;
			note.style.top = `${y}px`;
			y += note.getBoundingClientRect().height + STACK_GAP;
		}
		lowest = Math.max(lowest, item.y + item.h);
	}
	if (!fixedHeight) stage.style.minHeight = `${Math.ceil(lowest)}px`;
	const parts: Element[] = [];
	for (const item of items) {
		const nr = item.note.getBoundingClientRect();
		const left = item.side === 'left';
		const x1 = (left ? nr.right : nr.left) - sr.left;
		const y1 = item.y + item.anchor;
		const x2 = (left ? pr.left - 5 : pr.right + 5) - sr.left;
		const y2 = item.mid;
		const bend = (x1 + x2) / 2;
		const tone = [...item.note.classList].find((c) => /^t[0-9r]$/.test(c)) ?? '';
		const past = item.notes.every((note) => note.classList.contains('past')) ? ' past' : '';
		const path = document.createElementNS(SVG, 'path');
		path.setAttribute('class', `ld${past}`);
		path.setAttribute('d', `M${x1} ${y1} C${bend} ${y1} ${bend} ${y2} ${x2} ${y2}`);
		parts.push(path);
		if (item.bottom - item.top > 30) {
			const bracket = document.createElementNS(SVG, 'path');
			bracket.setAttribute('class', `br${past}`);
			bracket.setAttribute('d', `M${x2} ${item.top + 3} V${item.bottom - 3}`);
			parts.push(bracket);
		}
		const dot = document.createElementNS(SVG, 'circle');
		dot.setAttribute('class', `dot ${tone}${past}`);
		dot.setAttribute('cx', String(x2));
		dot.setAttribute('cy', String(y2));
		dot.setAttribute('r', '4.5');
		dot.setAttribute('data-label', item.notes.map((note) => note.dataset.label ?? '').join(' '));
		dot.setAttribute('data-lead', String(y1));
		parts.push(dot);
	}
	svg.replaceChildren(...parts);
};
