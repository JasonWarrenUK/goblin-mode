// Tutorial hybrid, version 2. Without this script, or with reduced motion, every step shows its own
// snapshot of the file and nothing is hidden. Wide and live: one pinned stage holds still while a
// scroll track moves through the steps. Narrow and live: a Steps / File switch over a normal scroll.
(() => {
	const root = document.documentElement;
	root.classList.add('js');
	const SVG = 'http://www.w3.org/2000/svg';
	const GAP = 10;

	const tut = document.getElementById('tut');
	const track = tut.querySelector('.track');
	const pin = tut.querySelector('.pin');
	const articles = [...tut.querySelectorAll('.step')];
	const headingButtons = articles.map((article) => article.querySelector('.step-btn'));
	const navButtons = [...pin.querySelectorAll('.stepnav button')];
	const segs = [...tut.querySelectorAll('.seg')];
	const mainStage = pin.querySelector('.specimen .stage');
	const lines = [...mainStage.querySelectorAll('.ln')];
	const notes = [...mainStage.querySelectorAll('.co')];
	const specState = pin.querySelector('.spec-state');
	const viewButtons = [...tut.querySelectorAll('.viewbar button')];
	const viewState = tut.querySelector('.viewstate');
	const realStage = document.querySelector('.real .stage');
	const last = articles.length - 1;

	const motionOK = matchMedia('(prefers-reduced-motion: no-preference)');
	const wide = matchMedia('(min-width: 1100px)');
	const canFind = 'onbeforematch' in document.body;
	const modeNow = () => (!motionOK.matches ? 'static' : wide.matches ? 'pinned' : 'list');

	let mode = 'static';
	let current = 0;
	let lock = false;
	let lockTimer = 0;
	const fileView = () => mode === 'list' && tut.dataset.view === 'file';

	// ---------- write-ups in the pinned stage: one shows; the others keep their headings for screen
	// readers (clipped) and their bodies hidden until find-in-page lands on them ----------
	const bodies = articles.map((article) => article.querySelector('.step-body'));
	const isOff = (k) => articles[k].classList.contains('inactive');
	const hideArticle = (k) => {
		articles[k].classList.remove('leaving', 'entering');
		articles[k].classList.add('inactive');
		if (canFind) bodies[k].setAttribute('hidden', 'until-found');
		else bodies[k].classList.add('off');
	};
	const showOnly = (n, instant) => {
		articles.forEach((article, k) => {
			clearTimeout(article.leaveTimer);
			if (k === n) {
				const wasOff = isOff(k) || article.classList.contains('leaving');
				article.classList.remove('inactive', 'leaving', 'entering');
				bodies[k].removeAttribute('hidden');
				bodies[k].classList.remove('off');
				if (wasOff && !instant) { void article.offsetWidth; article.classList.add('entering'); }
			} else if (!isOff(k)) {
				if (instant) hideArticle(k);
				else {
					article.classList.add('leaving');
					article.leaveTimer = setTimeout(() => hideArticle(k), 170);
				}
			}
		});
	};
	const showAll = () => articles.forEach((article, k) => {
		clearTimeout(article.leaveTimer);
		article.classList.remove('inactive', 'leaving', 'entering');
		bodies[k].removeAttribute('hidden');
		bodies[k].classList.remove('off');
	});

	// ---------- state ----------
	const render = (n, { instant = false } = {}) => {
		const previous = current;
		current = n;
		tut.dataset.step = String(n);
		articles.forEach((article, k) => {
			article.dataset.state = k < n ? 'past' : k === n ? 'active' : 'pending';
			if (k === n) headingButtons[k].setAttribute('aria-current', 'step');
			else headingButtons[k].removeAttribute('aria-current');
		});
		navButtons.forEach((button) => {
			if (Number(button.dataset.go) === n) button.setAttribute('aria-current', 'step');
			else button.removeAttribute('aria-current');
		});
		if (mode === 'pinned') {
			const focusInside = articles.findIndex((article) => article.contains(document.activeElement));
			showOnly(n, instant);
			if (focusInside >= 0 && focusInside !== n) headingButtons[n].focus({ preventScroll: true });
		}
		lines.forEach((line) => {
			const s = Number(line.dataset.s);
			const show = s === 0 || (s > 0 && s <= n) || (s === -1 && n <= 1);
			const wasHidden = line.hidden;
			line.hidden = !show;
			line.classList.toggle('del', s === -1 && n === 1);
			line.classList.toggle('cur', s > 0 && s === n);
			line.classList.toggle('new', s > 0 && s === n);
			line.classList.toggle('fresh', show && wasHidden && n > previous && !instant);
			line.removeAttribute('data-label');
			line.classList.remove('pastpin');
		});
		notes.forEach((note) => {
			const s = Number(note.dataset.s);
			const state = s < n ? 'past' : s === n ? 'cur' : 'future';
			note.classList.toggle('fresh', state === 'cur' && note.dataset.state === 'future' && n > previous && !instant);
			note.dataset.state = state;
			const onShow = state === 'cur' || (state === 'past' && mode === 'pinned');
			if (onShow) {
				const target = lines[Number(note.dataset.from)];
				target.dataset.label = note.dataset.label;
				target.classList.toggle('pastpin', state === 'past');
			}
		});
		const title = n ? articles[n].dataset.title : '';
		specState.textContent = n ? `after step 2.${n}` : 'where level 1 left it';
		viewState.textContent = n ? `Step 2.${n}: ${title}` : 'Level 1 file';
		scheduleLayout();
	};

	// ---------- callouts: each leader ends on its target's measured centre ----------
	const clearStage = (stage) => {
		stage.classList.remove('marginal');
		stage.style.minHeight = '';
		stage.querySelector('.leaders').replaceChildren();
		stage.querySelectorAll('.co').forEach((note) => { note.style.top = ''; delete note.dataset.at; });
	};

	const resolveSide = (items, maxBottom) => {
		// clusters of overlapping notes sit where their total displacement is smallest
		const clusters = [];
		items.forEach((item) => {
			clusters.push({ items: [item], top: item.want, h: item.h });
			while (clusters.length > 1) {
				const a = clusters[clusters.length - 2];
				const b = clusters[clusters.length - 1];
				if (a.top + a.h + GAP <= b.top) break;
				a.items.push(...b.items);
				a.h += GAP + b.h;
				let offset = 0;
				let sum = 0;
				a.items.forEach((x) => { sum += x.want - offset; offset += x.h + GAP; });
				a.top = sum / a.items.length;
				clusters.pop();
			}
		});
		let floor = 0;
		clusters.forEach((cluster) => {
			cluster.top = Math.max(cluster.top, floor);
			floor = cluster.top + cluster.h + GAP;
		});
		let ceiling = maxBottom;
		[...clusters].reverse().forEach((cluster) => {
			if (cluster.top + cluster.h > ceiling) cluster.top = Math.max(0, ceiling - cluster.h);
			ceiling = cluster.top - GAP;
		});
		clusters.forEach((cluster) => {
			let y = cluster.top;
			cluster.items.forEach((x) => { x.y = y; y += x.h + GAP; });
		});
	};

	const layoutStage = (stage, on, fixedHeight) => {
		if (!on || !stage.offsetParent) { clearStage(stage); return; }
		stage.classList.add('marginal');
		stage.style.minHeight = '';
		const svg = stage.querySelector('.leaders');
		const panel = stage.querySelector('.code');
		const stageLines = [...stage.querySelectorAll('.ln')];
		const sr = stage.getBoundingClientRect();
		const pr = panel.getBoundingClientRect();
		const items = [...stage.querySelectorAll('.co')]
			.filter((note) => getComputedStyle(note).display !== 'none')
			.map((note) => {
				const first = stageLines[Number(note.dataset.from)].getBoundingClientRect();
				const lastLine = stageLines[Number(note.dataset.to)].getBoundingClientRect();
				const nr = note.getBoundingClientRect();
				const lab = note.querySelector('.lab').getBoundingClientRect();
				const mid = (first.top + lastLine.bottom) / 2 - sr.top;
				const anchor = (lab.top + lab.bottom) / 2 - nr.top;
				return { note, pref: note.dataset.side, mid, top: first.top - sr.top, bottom: lastLine.bottom - sr.top, h: nr.height, anchor, want: mid - anchor };
			})
			.sort((a, b) => a.mid - b.mid);
		// a note whose slot is taken on its own side moves to the other side when that side is free
		const bySide = { left: [], right: [] };
		const clash = (list, item) => list.some((o) => item.want < o.want + o.h + GAP && o.want < item.want + item.h + GAP);
		items.forEach((item) => {
			const other = item.pref === 'left' ? 'right' : 'left';
			item.side = clash(bySide[item.pref], item) && !clash(bySide[other], item) ? other : item.pref;
			bySide[item.side].push(item);
		});
		const maxBottom = fixedHeight ? stage.clientHeight : Infinity;
		resolveSide(bySide.left, maxBottom);
		resolveSide(bySide.right, maxBottom);
		let lowest = pr.bottom - sr.top;
		items.forEach((item) => {
			item.note.dataset.at = item.side;
			item.note.style.top = `${item.y}px`;
			lowest = Math.max(lowest, item.y + item.h);
		});
		if (!fixedHeight) stage.style.minHeight = `${Math.ceil(lowest)}px`;
		const parts = [];
		items.forEach((item) => {
			const nr = item.note.getBoundingClientRect();
			const left = item.side === 'left';
			const x1 = (left ? nr.right : nr.left) - sr.left;
			const y1 = item.y + item.anchor;
			const x2 = (left ? pr.left - 5 : pr.right + 5) - sr.left;
			const y2 = item.mid;
			const bend = (x1 + x2) / 2;
			const tone = [...item.note.classList].find((c) => /^m[0-9r]$/.test(c)) || '';
			const past = item.note.dataset.state === 'past' ? ' past' : '';
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
			dot.dataset.label = item.note.dataset.label;
			dot.dataset.lead = String(y1);
			parts.push(dot);
		});
		svg.replaceChildren(...parts);
	};

	let layoutFrame = 0;
	const layout = () => {
		layoutFrame = 0;
		layoutStage(mainStage, mode === 'pinned', true);
		layoutStage(realStage, wide.matches, false);
	};
	function scheduleLayout() {
		if (!layoutFrame) layoutFrame = requestAnimationFrame(layout);
	}

	// ---------- which step is active ----------
	const fromScroll = () => {
		if (lock || mode === 'static' || fileView()) return;
		let n = 0;
		if (mode === 'pinned') {
			segs.forEach((seg, k) => { if (k && seg.getBoundingClientRect().top <= 2) n = k; });
		} else {
			const band = innerHeight * 0.38;
			articles.forEach((article, k) => { if (k && article.getBoundingClientRect().top < band) n = k; });
		}
		if (n !== current) render(n);
	};
	// a one-per-cent line at the top of the viewport for the track; a band for the list
	const segObserver = new IntersectionObserver(fromScroll, { rootMargin: '0px 0px -99% 0px', threshold: [0, 1] });
	segs.forEach((seg) => segObserver.observe(seg));
	const listObserver = new IntersectionObserver(fromScroll, { rootMargin: '0px 0px -62% 0px', threshold: [0, 1] });
	articles.forEach((article) => listObserver.observe(article));

	const holdThenRelease = (ms) => {
		lock = true;
		clearTimeout(lockTimer);
		const release = () => { clearTimeout(lockTimer); lock = false; fromScroll(); };
		lockTimer = setTimeout(release, ms);
		if ('onscrollend' in window) addEventListener('scrollend', release, { once: true });
	};

	// ---------- buttons, keys and find-in-page all move the scroll position ----------
	const go = (n, { focus = false, instant = false } = {}) => {
		n = Math.min(last, Math.max(0, n));
		if (mode === 'static') {
			articles[n].scrollIntoView({ block: 'start' });
			if (focus) headingButtons[n].focus();
			return;
		}
		render(n, { instant });
		if (fileView()) return;
		holdThenRelease(instant ? 150 : 1200);
		const behavior = instant ? 'auto' : 'smooth';
		if (mode === 'pinned') {
			scrollTo({ top: scrollY + segs[n].getBoundingClientRect().top + 2, behavior });
			if (focus) headingButtons[n].focus({ preventScroll: true });
		} else {
			if (focus) headingButtons[n].focus({ preventScroll: true });
			articles[n].scrollIntoView({ behavior, block: 'start' });
		}
	};
	headingButtons.forEach((button) => button.addEventListener('click', () => go(Number(button.dataset.go))));
	navButtons.forEach((button) => button.addEventListener('click', () => go(Number(button.dataset.go))));
	bodies.forEach((body, k) => body.addEventListener('beforematch', () => { if (mode === 'pinned') go(k, { instant: true }); }));
	// tabbing onto a clipped heading brings its step forward, so focus is never invisible
	headingButtons.forEach((button, k) => button.addEventListener('focus', () => { if (mode === 'pinned' && isOff(k)) go(k); }));

	tut.addEventListener('keydown', (event) => {
		if (event.altKey || event.ctrlKey || event.metaKey || mode === 'static') return;
		const key = event.key;
		const delta = key === 'ArrowDown' || key === 'j' ? 1 : key === 'ArrowUp' || key === 'k' ? -1 : 0;
		if (!delta) return;
		event.preventDefault();
		const inNav = navButtons.includes(document.activeElement) || viewButtons.includes(document.activeElement);
		go(current + delta, { focus: !inNav && !fileView() });
	});

	// ---------- Steps / File at narrow widths ----------
	const setView = (view) => {
		tut.dataset.view = view;
		viewButtons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.view === view)));
		lock = true;
		clearTimeout(lockTimer);
		if (view === 'file') {
			if (tut.getBoundingClientRect().top < 0) tut.scrollIntoView({ block: 'start' });
		} else {
			articles[current].scrollIntoView({ block: 'start' });
		}
		render(current, { instant: true });
		requestAnimationFrame(() => requestAnimationFrame(() => {
			lockTimer = setTimeout(() => { lock = false; fromScroll(); }, 120);
		}));
	};
	viewButtons.forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));

	// ---------- modes and measuring ----------
	const applyMode = () => {
		mode = modeNow();
		tut.dataset.mode = mode;
		if (mode === 'pinned') showOnly(current, true);
		else showAll();
		render(current, { instant: true });
		fromScroll();
	};
	motionOK.addEventListener('change', applyMode);
	wide.addEventListener('change', applyMode);
	if ('ResizeObserver' in window) {
		const resized = new ResizeObserver(scheduleLayout);
		resized.observe(mainStage);
		resized.observe(realStage.querySelector('.code'));
	}
	addEventListener('resize', scheduleLayout);
	if (document.fonts) document.fonts.ready.then(scheduleLayout);

	applyMode();
})();
