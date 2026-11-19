import { TUTORIAL } from '/Users/jasonwarren/.claude/.claude/worktrees/site-pages-site/site/src/lib/content/tutorial.ts';
function newLines(a: string[], b: string[]): number[] {
	const m = a.length, n = b.length;
	const L = Array.from({ length: m + 1 }, () => new Array<number>(n + 1).fill(0));
	for (let i = m - 1; i >= 0; i--) for (let j = n - 1; j >= 0; j--) L[i]![j] = a[i] === b[j] ? L[i + 1]![j + 1]! + 1 : Math.max(L[i + 1]![j]!, L[i]![j + 1]!);
	const out: number[] = [];
	let i = 0, j = 0;
	while (j < n) {
		if (i < m && a[i] === b[j]) { i++; j++; }
		else if (i < m && L[i + 1]![j]! >= L[i]![j + 1]!) i++;
		else { out.push(j + 1); j++; }
	}
	return out;
}
const key = (p: string): string => p.replace(/^tidy\/skills\//, '.claude/skills/');
const prev = new Map<string, string>();
for (const lv of TUTORIAL) {
	for (const f of lv.opening?.files ?? []) prev.set(key(f.path), f.text);
	for (const s of lv.steps) {
		for (const f of s.files) {
			const before = prev.get(key(f.path));
			const lines = f.text.split('\n');
			const dn = before === undefined ? lines.map((_, i) => i + 1) : newLines(before.split('\n'), lines);
			const added = f.added ?? [];
			const extra = added.filter((x) => !dn.includes(x));
			const missed = dn.filter((x) => !added.includes(x) && lines[x - 1]!.trim() !== '');
			const blanks = dn.filter((x) => !added.includes(x) && lines[x - 1]!.trim() === '');
			console.log(s.id, f.path, before === undefined ? '(first)' : '', 'added', JSON.stringify(added), extra.length ? 'NOT IN DIFF ' + extra : '', missed.length ? 'MISSED ' + missed : '', blanks.length ? 'new blanks unmarked ' + blanks : '');
			prev.set(key(f.path), f.text);
		}
		const w = s.prose.join(' ').replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
		console.log('  words', s.id, w);
	}
}
