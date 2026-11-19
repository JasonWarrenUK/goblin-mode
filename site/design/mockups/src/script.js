// Switcher: one mockup at a time, linkable by hash. Without this script all four stack.
(() => {
	const root = document.documentElement;
	root.classList.add('js');
	const ids = ['ledger', 'scroll', 'specimen', 'zine'];
	const sections = ids.map((id) => document.getElementById(id));
	const buttons = [...document.querySelectorAll('.switch-buttons button')];

	const show = (wanted, { updateHash = false, toTop = false } = {}) => {
		const id = ids.includes(wanted) ? wanted : 'ledger';
		sections.forEach((section) => { section.hidden = section.id !== id; });
		buttons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.target === id)));
		if (updateHash) history.replaceState(null, '', '#' + id);
		if (toTop) window.scrollTo(0, 0);
	};
	buttons.forEach((button) => button.addEventListener('click', () => show(button.dataset.target, { updateHash: true, toTop: true })));
	addEventListener('hashchange', () => show(location.hash.slice(1), { toTop: true }));
	show(location.hash.slice(1), { toTop: Boolean(location.hash) });

	// Ledger: invented and real files as two tabs at narrow widths.
	const real = document.querySelector('#ledger .real');
	real.querySelectorAll('.realtabs button').forEach((button) => button.addEventListener('click', () => {
		real.dataset.show = button.dataset.show;
		real.querySelectorAll('.realtabs button').forEach((other) => other.setAttribute('aria-pressed', String(other === button)));
	}));

	// Scroll story: the pinned file follows the step in the middle of the viewport.
	const story = document.querySelector('#scroll .story');
	const pinned = story.querySelector('.pinned');
	const beats = [...story.querySelectorAll('.beat')];
	const activate = (beat) => {
		const { file, hl } = beat.dataset;
		const upto = Number(beat.dataset.upto);
		pinned.dataset.file = file;
		pinned.querySelectorAll('.pf').forEach((pane) => {
			const current = pane.dataset.file === file;
			pane.hidden = !current;
			if (!current) return;
			pane.querySelectorAll('.ln').forEach((line) => {
				const lineOrder = Number(line.dataset.o);
				line.hidden = lineOrder === -1 ? upto !== 0 : lineOrder > upto;
				line.classList.toggle('hl', line.dataset.hl === hl);
			});
		});
		beats.forEach((other) => {
			other.classList.toggle('on', other === beat);
			other.querySelector('.show').setAttribute('aria-pressed', String(other === beat));
		});
	};
	beats.forEach((beat) => beat.querySelector('.show').addEventListener('click', () => activate(beat)));
	if ('IntersectionObserver' in window) {
		const observer = new IntersectionObserver((entries) => {
			entries.filter((entry) => entry.isIntersecting).forEach((entry) => activate(entry.target));
		}, { rootMargin: '-45% 0px -50% 0px' });
		beats.forEach((beat) => observer.observe(beat));
	}
	activate(beats[0]);
})();
