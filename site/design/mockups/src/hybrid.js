// Tutorial hybrid. Without this script, or with reduced motion, every step shows its own
// snapshot of the file and nothing is hidden. With it, the specimen sheet builds in step with the prose.
(() => {
	const root = document.documentElement;
	root.classList.add('js');
	const SVG = 'http://www.w3.org/2000/svg';

	const tut = document.getElementById('tut');
	const steps = [...tut.querySelectorAll('.step')];
	const stepButtons = steps.map((step) => step.querySelector('.step-btn'));
	const sheet = tut.querySelector('.specimen');
	const mainStage = sheet.querySelector('.stage');
	const lines = [...mainStage.querySelectorAll('.ln')];
	const notes = [...mainStage.querySelectorAll('.co')];
	const specState = sheet.querySelector('.spec-state');
	const viewButtons = [...tut.querySelectorAll('.viewbar button')];
	const viewState = tut.querySelector('.viewstate');
	const realStage = document.querySelector('.real .stage');

	const motionOK = matchMedia('(prefers-reduced-motion: no-preference)');
	const wide = matchMedia('(min-width: 1100px)');
	const realWide = matchMedia('(min-width: 900px)');
	const isLive = () => motionOK.matches;
	const fileView = () => !wide.matches && tut.dataset.view === 'file';

	let current = 0;
	let lock = false;
	let lockTimer = 0;

	// ---------- state ----------
	const render = (n) => {
		const previous = current;
		current = n;
		tut.dataset.step = String(n);
		steps.forEach((step, i) => {
			const k = i + 1;
			step.dataset.state = k < n ? 'past' : k === n ? 'active' : 'pending';
			if (k === n) stepButtons[i].setAttribute('aria-current', 'step');
			else stepButtons[i].removeAttribute('aria-current');
		});
		lines.forEach((line) => {
			const s = Number(line.dataset.s);
			const show = s === 0 || (s > 0 && s <= n) || (s === -1 && n <= 1);
			const wasHidden = line.hidden;
			line.hidden = !show;
			line.classList.toggle('del', s === -1 && n === 1);
			line.classList.toggle('cur', s > 0 && s === n);
			line.classList.toggle('new', s > 0 && s === n);
			line.classList.toggle('fresh', show && wasHidden && n > previous);
			line.removeAttribute('data-label');
			line.classList.remove('pastpin');
		});
		notes.forEach((note) => {
			const s = Number(note.dataset.s);
			const state = s < n ? 'past' : s === n ? 'cur' : 'future';
			note.classList.toggle('fresh', state === 'cur' && note.dataset.state === 'future' && n > previous);
			note.dataset.state = state;
			// the gutter carries the label of every note on show
			const onShow = state === 'cur' || (state === 'past' && wide.matches);
			if (onShow) {
				const target = lines[Number(note.dataset.from)];
				target.dataset.label = note.dataset.label;
				target.classList.toggle('pastpin', state === 'past');
			}
		});
		const title = n ? steps[n - 1].dataset.title : '';
		specState.textContent = n ? `After step 2.${n}: ${title}` : 'Where level 1 left it';
		viewState.textContent = n ? `Step 2.${n}: ${title}` : 'Level 1 file';
		scheduleLayout();
	};

	// ---------- callouts and leader lines, measured from the rendered lines ----------
	const clearStage = (stage) => {
		stage.style.minHeight = '';
		stage.querySelector('.leaders').replaceChildren();
		stage.querySelectorAll('.co').forEach((note) => { note.style.top = ''; });
	};

	const layoutStage = (stage, active) => {
		if (!active || !stage.offsetParent) { clearStage(stage); return; }
		const svg = stage.querySelector('.leaders');
		const panel = stage.querySelector('.code');
		const stageRect = stage.getBoundingClientRect();
		const panelRect = panel.getBoundingClientRect();
		const stageLines = [...stage.querySelectorAll('.ln')];
		const shown = [...stage.querySelectorAll('.co')].filter((note) => getComputedStyle(note).display !== 'none');
		const placed = shown.map((note) => {
			const first = stageLines[Number(note.dataset.from)].getBoundingClientRect();
			const last = stageLines[Number(note.dataset.to)].getBoundingClientRect();
			return {
				note,
				side: note.dataset.side,
				top: first.top - stageRect.top,
				bottom: last.bottom - stageRect.top,
				mid: (first.top + last.bottom) / 2 - stageRect.top,
				height: note.offsetHeight,
			};
		});
		let lowest = panelRect.bottom - stageRect.top;
		['left', 'right'].forEach((side) => {
			let floor = 0;
			placed.filter((p) => p.side === side).sort((a, b) => a.mid - b.mid).forEach((p) => {
				p.y = Math.max(p.mid - 16, floor);
				floor = p.y + p.height + 12;
				lowest = Math.max(lowest, p.y + p.height);
				p.note.style.top = `${p.y}px`;
			});
		});
		stage.style.minHeight = `${Math.ceil(lowest)}px`;
		const edgeLeft = panelRect.left - stageRect.left;
		const edgeRight = panelRect.right - stageRect.left;
		const parts = [];
		placed.forEach((p) => {
			const left = p.side === 'left';
			const x1 = left ? p.note.offsetLeft + p.note.offsetWidth : p.note.offsetLeft;
			const y1 = p.y + 16;
			const x2 = left ? edgeLeft - 5 : edgeRight + 5;
			const y2 = p.mid;
			const bend = (x1 + x2) / 2;
			const tone = [...p.note.classList].find((c) => /^m[0-9r]$/.test(c)) || '';
			const past = p.note.dataset.state === 'past' ? ' past' : '';
			const path = document.createElementNS(SVG, 'path');
			path.setAttribute('class', `ld${past}`);
			path.setAttribute('d', `M${x1} ${y1} C${bend} ${y1} ${bend} ${y2} ${x2} ${y2}`);
			parts.push(path);
			if (p.bottom - p.top > 30) {
				const bracket = document.createElementNS(SVG, 'path');
				bracket.setAttribute('class', `br${past}`);
				bracket.setAttribute('d', `M${x2} ${p.top + 3} V${p.bottom - 3}`);
				parts.push(bracket);
			}
			const dot = document.createElementNS(SVG, 'circle');
			dot.setAttribute('class', `dot ${tone}${past}`);
			dot.setAttribute('cx', String(x2));
			dot.setAttribute('cy', String(y2));
			dot.setAttribute('r', '4.5');
			parts.push(dot);
		});
		svg.replaceChildren(...parts);
	};

	let layoutFrame = 0;
	const layout = () => {
		layoutFrame = 0;
		layoutStage(mainStage, isLive() && wide.matches);
		layoutStage(realStage, realWide.matches);
	};
	function scheduleLayout() {
		if (!layoutFrame) layoutFrame = requestAnimationFrame(layout);
	}

	// ---------- which step is active: IntersectionObserver on the steps ----------
	const band = () => innerHeight * 0.38;
	const fromScroll = () => {
		if (!isLive() || lock || fileView()) return;
		let n = 0;
		steps.forEach((step, i) => { if (step.getBoundingClientRect().top < band()) n = i + 1; });
		if (n !== current) render(n);
	};
	const observer = new IntersectionObserver(fromScroll, { rootMargin: '0px 0px -62% 0px', threshold: [0, 1] });
	steps.forEach((step) => observer.observe(step));

	const holdThenRelease = (ms) => {
		lock = true;
		clearTimeout(lockTimer);
		const release = () => { clearTimeout(lockTimer); lock = false; fromScroll(); };
		lockTimer = setTimeout(release, ms);
		if ('onscrollend' in window) addEventListener('scrollend', release, { once: true });
	};

	// ---------- buttons and keys ----------
	const go = (n, { focus = false } = {}) => {
		n = Math.min(steps.length, Math.max(1, n));
		render(n);
		if (!isLive()) { steps[n - 1].scrollIntoView({ block: 'start' }); if (focus) stepButtons[n - 1].focus(); return; }
		if (fileView()) return;
		holdThenRelease(1200);
		if (focus) stepButtons[n - 1].focus({ preventScroll: true });
		steps[n - 1].scrollIntoView({ behavior: 'smooth', block: 'start' });
	};
	stepButtons.forEach((button, i) => button.addEventListener('click', () => go(i + 1)));

	tut.addEventListener('keydown', (event) => {
		if (event.altKey || event.ctrlKey || event.metaKey || !isLive()) return;
		const key = event.key;
		const delta = key === 'ArrowDown' || key === 'j' ? 1 : key === 'ArrowUp' || key === 'k' ? -1 : 0;
		if (!delta) return;
		event.preventDefault();
		go(current + delta, { focus: !fileView() });
	});

	// ---------- Steps / File at narrow widths ----------
	const setView = (view) => {
		tut.dataset.view = view;
		viewButtons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.view === view)));
		lock = true;
		clearTimeout(lockTimer);
		if (view === 'file') {
			const top = tut.getBoundingClientRect().top;
			if (top < 0) tut.scrollIntoView({ block: 'start' });
		} else if (current) {
			steps[current - 1].scrollIntoView({ block: 'start' });
		} else {
			scrollTo(0, 0);
		}
		render(current);
		// let the observer settle on the restored position before it may change the step again
		requestAnimationFrame(() => requestAnimationFrame(() => {
			lockTimer = setTimeout(() => { lock = false; fromScroll(); }, 120);
		}));
	};
	viewButtons.forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));

	// ---------- keep it measured ----------
	const reflow = () => { render(current); };
	motionOK.addEventListener('change', reflow);
	wide.addEventListener('change', reflow);
	realWide.addEventListener('change', scheduleLayout);
	if ('ResizeObserver' in window) {
		const resized = new ResizeObserver(scheduleLayout);
		resized.observe(mainStage.querySelector('.code'));
		resized.observe(realStage.querySelector('.code'));
	}
	addEventListener('resize', scheduleLayout);
	if (document.fonts) document.fonts.ready.then(scheduleLayout);

	render(0);
	fromScroll();
})();
