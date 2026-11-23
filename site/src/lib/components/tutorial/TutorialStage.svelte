<script lang="ts">
	// One level's steps on a pinned specimen sheet. Without JS, or with reduced motion,
	// every step shows its own snapshot of the files and nothing is hidden. Wide and tall
	// enough: the sheet pins and holds still while a scroll track moves through the states,
	// one snap point per state plus one for the release, with snapping on only inside the
	// track. Otherwise: a Steps / File switch over a normal scroll.
	import { flushSync, onMount, tick } from 'svelte';
	import CodePanel from './CodePanel.svelte';
	import { placeCallouts } from './place.ts';
	import Specimen from './Specimen.svelte';
	import { stageView, statesOf, tabLabels, toneMarks } from '#lib/content/tutorial-view.ts';
	import type { FileView, StagePage } from '#lib/content/tutorial.types.ts';

	interface Props {
		level: StagePage;
		/** What a screen reader calls the stage, before ", step by step": "Level 2", say. */
		name: string;
	}

	let { level, name }: Props = $props();

	/**
	 * Below this viewport height the stage never pins, so every level uses one layout at a given
	 * size. Measured at 1280 wide by the lowest height at which each level's every state and tab
	 * fits the sheet with no overlapping callouts: level 1 under 600, level 2 610, level 3 748,
	 * level 4 675, level 5 692. Above it, fits() still checks the level in hand and falls back if
	 * anything would overflow.
	 */
	const PIN_FLOOR = 750;

	const states = $derived(statesOf(level));
	const view = $derived(stageView(level));
	const last = $derived(states.length - 1);

	type Mode = 'static' | 'pinned' | 'list';
	let mode = $state<Mode>('static');
	let current = $state(0);
	let leaving = $state<number | null>(null);
	let entering = $state<number | null>(null);
	let shownView = $state<'steps' | 'file'>('steps');
	let tab = $state(0);

	let tut = $state<HTMLElement>();
	const articles: HTMLElement[] = $state([]);
	const headings: HTMLButtonElement[] = $state([]);
	const snaps: HTMLElement[] = $state([]);

	const own = (k: number): string[] => states[k]!.callouts.map((callout) => callout.label);
	const stateName = (k: number): string => (states[k]!.id ? `Step ${states[k]!.id}: ${states[k]!.title}` : states[k]!.title);
	const asFile = (label: string, text: string): FileView => ({ path: label, lang: 'text', text });
	const ownOnFile = (k: number, path: string) => view.callouts[k]!.filter((callout) => !callout.past && callout.file === path);
	const labelsOf = (k: number, path: string) => new Map(ownOnFile(k, path).map((callout) => [callout.line, { label: callout.label, past: false, tone: callout.tone }]));

	// ---------- moving between states ----------
	let fadeTimer = 0;
	const setCurrent = (n: number, instant = false): void => {
		if (n === current) return;
		const previous = current;
		const focusInside = articles.findIndex((article) => article?.contains(document.activeElement));
		current = n;
		tab = 0;
		clearTimeout(fadeTimer);
		if (mode === 'pinned' && !instant) {
			leaving = previous;
			entering = n;
			fadeTimer = window.setTimeout(() => {
				leaving = null;
				entering = null;
			}, 200);
		} else {
			leaving = null;
			entering = null;
		}
		if (mode === 'pinned' && focusInside >= 0 && focusInside !== n) void tick().then(() => headings[n]?.focus({ preventScroll: true }));
	};

	// ---------- snap positions ----------
	const snapTops = (): number[] =>
		snaps.map((snap) => Math.round(snap.getBoundingClientRect().top + scrollY - (parseFloat(getComputedStyle(snap).scrollMarginTop) || 0)));
	/** The nearest snap index to the scroll position, 0 to the release. */
	const position = (): number => {
		const p = snapTops();
		return Math.max(0, Math.min(p.length - 1, Math.round((scrollY - p[0]!) / (p[1]! - p[0]!))));
	};

	let snapping = false;
	const setSnapping = (on: boolean): void => {
		if (on === snapping) return;
		snapping = on;
		document.documentElement.classList.toggle('tut-snapping', on);
	};
	const updateSnapping = (): void => {
		if (mode !== 'pinned') {
			setSnapping(false);
			return;
		}
		// a scroll the stage started itself ends on a snap point; leave the switch alone until it lands
		if (lock) return;
		const p = snapTops();
		const y = scrollY;
		if (y >= p[0]! - 2 && y <= p[p.length - 1]! + 2) setSnapping(true);
		else setSnapping(false);
	};

	// ---------- which state is active ----------
	let lock = false;
	let lockTimer = 0;
	const fromScroll = (): void => {
		updateSnapping();
		if (lock || mode === 'static' || (mode === 'list' && shownView === 'file')) return;
		let n = 0;
		if (mode === 'pinned') n = Math.min(last, position());
		else {
			const band = innerHeight * 0.38;
			articles.forEach((article, k) => {
				if (k && article.getBoundingClientRect().top < band) n = k;
			});
		}
		if (n !== current) setCurrent(n);
	};
	const holdThenRelease = (ms: number): void => {
		lock = true;
		clearTimeout(lockTimer);
		const release = (): void => {
			clearTimeout(lockTimer);
			lock = false;
			fromScroll();
		};
		lockTimer = window.setTimeout(release, ms);
		if ('onscrollend' in window) addEventListener('scrollend', release, { once: true });
	};

	/** Moves to a state (0 to the last) or, in the pinned stage, the release point after it. */
	const go = (target: number, { focus = false, instant = false } = {}): void => {
		const limit = mode === 'pinned' ? last + 1 : last;
		target = Math.min(limit, Math.max(0, target));
		const n = Math.min(last, target);
		if (mode === 'static') {
			articles[n]?.scrollIntoView({ block: 'start' });
			if (focus) headings[n]?.focus();
			return;
		}
		setCurrent(n, instant);
		if (mode === 'list' && shownView === 'file') return;
		holdThenRelease(instant ? 150 : 1200);
		const behavior: ScrollBehavior = instant ? 'auto' : 'smooth';
		if (mode === 'pinned') {
			setSnapping(true);
			scrollTo({ top: snapTops()[target], behavior });
			if (focus) void tick().then(() => headings[n]?.focus({ preventScroll: true }));
		} else {
			if (focus) headings[n]?.focus({ preventScroll: true });
			articles[n]?.scrollIntoView({ behavior, block: 'start' });
		}
	};

	const onKey = (event: KeyboardEvent): void => {
		if (event.altKey || event.ctrlKey || event.metaKey || mode === 'static') return;
		const key = event.key;
		const delta = key === 'ArrowDown' || key === 'j' ? 1 : key === 'ArrowUp' || key === 'k' ? -1 : 0;
		if (!delta) return;
		let from = current;
		if (mode === 'pinned') {
			const p = snapTops();
			// past either end of the track the keys scroll the page as usual
			if (scrollY < p[0]! - 2 || scrollY > p[p.length - 1]! + 2) return;
			from = position();
			if ((delta > 0 && from === p.length - 1) || (delta < 0 && from === 0 && key === 'ArrowUp')) return;
		}
		event.preventDefault();
		const target = event.target as HTMLElement | null;
		const onToolbar = !!target?.closest('.stepnav, .viewbar');
		go(from + delta, { focus: !onToolbar && !(mode === 'list' && shownView === 'file') });
	};

	// focus arriving inside a hidden write-up (Tab onto its heading) brings that state forward
	const onFocusIn = (k: number): void => {
		if (mode === 'pinned' && k !== current) go(k);
	};

	// ---------- Steps / File ----------
	const setView = (next: 'steps' | 'file'): void => {
		shownView = next;
		lock = true;
		clearTimeout(lockTimer);
		flushSync();
		if (next === 'file') {
			if (tut && tut.getBoundingClientRect().top < 0) tut.scrollIntoView({ block: 'start' });
		} else articles[current]?.scrollIntoView({ block: 'start' });
		requestAnimationFrame(() =>
			requestAnimationFrame(() => {
				lockTimer = window.setTimeout(() => {
					lock = false;
					fromScroll();
				}, 120);
			}),
		);
	};

	// ---------- does every state fit the pinned sheet? ----------
	/** Shows each state and file in turn without painting and checks nothing overflows the sheet. */
	const fits = (): boolean => {
		const saved = { current, tab, leaving, entering };
		leaving = null;
		entering = null;
		let ok = true;
		const writeups = tut?.querySelector('.writeups');
		const stage = tut?.querySelector<HTMLElement>('.specimen .stage');
		if (!writeups || !stage) return false;
		outer: for (let k = 0; k < states.length; k++) {
			for (let t = 0; t < states[k]!.files.length; t++) {
				current = k;
				tab = t;
				flushSync();
				placeCallouts(stage, true);
				const room = writeups.getBoundingClientRect().bottom;
				const article = articles[k]!.getBoundingClientRect();
				const floor = stage.getBoundingClientRect().bottom + 1;
				const lowest = Math.max(stage.querySelector('.code')!.getBoundingClientRect().bottom, ...[...stage.querySelectorAll('.co')].map((note) => note.getBoundingClientRect().bottom));
				const pin = tut!.querySelector('.pin')!;
				const boxes = [...stage.querySelectorAll('.co')].map((note) => note.getBoundingClientRect());
				const overlap = boxes.some((a, i) => boxes.some((b, j) => j > i && a.left < b.right && b.left < a.right && a.top < b.bottom - 1 && b.top < a.bottom - 1));
				if (article.bottom > room + 1 || lowest > floor || overlap || pin.scrollHeight > pin.clientHeight + 1) {
					ok = false;
					break outer;
				}
			}
		}
		current = saved.current;
		tab = saved.tab;
		leaving = saved.leaving;
		entering = saved.entering;
		flushSync();
		return ok;
	};

	let motion: MediaQueryList;
	let wide: MediaQueryList;
	const applyMode = (): void => {
		let next: Mode = !motion.matches ? 'static' : wide.matches && innerHeight >= PIN_FLOOR ? 'pinned' : 'list';
		if (next === 'pinned') {
			mode = 'pinned';
			flushSync();
			if (!fits()) next = 'list';
		}
		mode = next;
		leaving = null;
		entering = null;
		flushSync();
		fromScroll();
	};

	onMount(() => {
		motion = matchMedia('(prefers-reduced-motion: no-preference)');
		wide = matchMedia('(min-width: 1100px)');
		document.documentElement.classList.add('js-tutorial');

		// Wheel inside the track: one gesture, however it arrives (a flick with its momentum
		// tail, or a couple of notches), moves exactly one snap position. Chrome's own wheel
		// snapping picks the point nearest where the scroll would end, so a notch shorter than
		// half a segment falls back. At either end the gesture leaves the track freely.
		let wheelBusy = false;
		let wheelTotal = 0;
		let quietTimer = 0;
		const onWheel = (event: WheelEvent): void => {
			if (mode !== 'pinned' || !event.deltaY || event.ctrlKey) return;
			const p = snapTops();
			const end = p.length - 1;
			const y = scrollY;
			const down = event.deltaY > 0;
			const step = event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY;
			const quiet = (): void => {
				clearTimeout(quietTimer);
				quietTimer = window.setTimeout(() => {
					wheelBusy = false;
					wheelTotal = 0;
				}, 220);
			};
			// outside the track the wheel is free, but a gesture that would cross into it lands
			// exactly on its nearest end: the first state from above, the release from below
			if (y < p[0]! - 2 || y > p[end]! + 2) {
				const crossing = down ? y < p[0]! && y + step >= p[0]! - 2 : y > p[end]! && y + step <= p[end]! + 2;
				if (!crossing) return;
				event.preventDefault();
				wheelBusy = true;
				quiet();
				go(down ? 0 : end);
				return;
			}
			event.preventDefault();
			if (!wheelBusy && ((down && y >= p[end]! - 2) || (!down && y <= p[0]! + 2))) {
				setSnapping(false);
				scrollBy({ top: event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY, behavior: 'instant' });
				return;
			}
			quiet();
			if (wheelBusy) return;
			wheelTotal += event.deltaY;
			if (Math.abs(wheelTotal) < 24) return;
			wheelBusy = true;
			wheelTotal = 0;
			go(position() + (down ? 1 : -1));
		};
		// keys that scroll the page switch snapping off first when they would leave the track
		const onPageKey = (event: KeyboardEvent): void => {
			if (!snapping) return;
			const down = ['ArrowDown', 'PageDown', 'End', 'j'].includes(event.key) || (event.key === ' ' && !event.shiftKey);
			const up = ['ArrowUp', 'PageUp', 'Home', 'k'].includes(event.key) || (event.key === ' ' && event.shiftKey);
			if (!down && !up) return;
			// Home and End always leave the track, so the snap must not hold them back
			if (event.key === 'Home' || event.key === 'End') {
				setSnapping(false);
				return;
			}
			const p = snapTops();
			if (down ? scrollY >= p[p.length - 1]! - 2 : scrollY <= p[0]! + 2) setSnapping(false);
		};
		let scrollFrame = 0;
		const onScroll = (): void => {
			if (!scrollFrame)
				scrollFrame = requestAnimationFrame(() => {
					scrollFrame = 0;
					fromScroll();
				});
		};
		let resizeTimer = 0;
		const onResize = (): void => {
			clearTimeout(resizeTimer);
			resizeTimer = window.setTimeout(applyMode, 150);
		};
		const observer = new IntersectionObserver(fromScroll, { rootMargin: '0px 0px -62% 0px', threshold: [0, 1] });
		for (const article of articles) observer.observe(article);

		addEventListener('wheel', onWheel, { passive: false });
		addEventListener('keydown', onPageKey, { capture: true });
		addEventListener('scroll', onScroll, { passive: true });
		addEventListener('resize', onResize);
		motion.addEventListener('change', applyMode);
		wide.addEventListener('change', applyMode);
		applyMode();
		void document.fonts?.ready.then(applyMode);

		return () => {
			observer.disconnect();
			removeEventListener('wheel', onWheel);
			removeEventListener('keydown', onPageKey, { capture: true });
			removeEventListener('scroll', onScroll);
			removeEventListener('resize', onResize);
			motion.removeEventListener('change', applyMode);
			wide.removeEventListener('change', applyMode);
			setSnapping(false);
			document.documentElement.classList.remove('js-tutorial');
		};
	});
</script>

<!-- The keys are handled where focus already is: the step buttons, headings and switch inside. -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<section
	class="tut"
	id="steps"
	data-mode={mode}
	data-view={shownView}
	data-step={current}
	aria-label="{name}, step by step"
	style:--states={states.length}
	bind:this={tut}
	onkeydown={onKey}
>
	<div class="viewbar">
		<div class="switch" role="group" aria-label="Show">
			<button type="button" aria-pressed={shownView === 'steps'} onclick={() => setView('steps')}>Steps</button>
			<button type="button" aria-pressed={shownView === 'file'} onclick={() => setView('file')}>File</button>
		</div>
		<p class="viewstate" aria-live="polite">{stateName(current)}</p>
	</div>
	<div class="track">
		<div class="pin">
			<div class="pin-bar">
				<p class="pin-title">
					Specimen <span class="pin-file">{tabLabels(states[current]!.files.map((file) => file.path))[Math.min(tab, states[current]!.files.length - 1)]}</span>
					<span class="spec-state">{states[current]!.id ? `after step ${states[current]!.id}` : states[current]!.title}</span>
				</p>
				<div class="stepnav" role="group" aria-label="Go to step">
					{#each states as state, k (k)}
						{#if state.id}
							<button type="button" aria-current={k === current ? 'step' : undefined} onclick={() => go(k)}>
								<span aria-hidden="true">{state.id}</span><span class="visually-hidden">Step {state.id}: {state.title}</span>
							</button>
						{/if}
					{/each}
				</div>
			</div>

			<div class="writeups">
				{#each states as state, k (k)}
					{@const id = state.id ? `step-${state.id.replace('.', '-')}` : 'opening'}
					<article
						class={['sheet', 'step', mode === 'pinned' && k !== current && k !== leaving && 'inactive', mode === 'pinned' && k === leaving && 'leaving', mode === 'pinned' && k === entering && 'entering']}
						{id}
						data-state={k < current ? 'past' : k === current ? 'active' : 'pending'}
						aria-labelledby="{id}-h"
						bind:this={articles[k]}
						onfocusin={() => onFocusIn(k)}
					>
						<h2 class="step-h" id="{id}-h">
							<button type="button" class="step-btn" aria-current={k === current ? 'step' : undefined} bind:this={headings[k]} onclick={() => go(k)}>
								{#if state.id}<span class="snum">{state.id}</span>{/if}
								{state.title}
							</button>
						</h2>
						{#each state.prose as paragraph, index (index)}
							<p>{@html toneMarks(paragraph, level, own(k))}</p>
						{/each}
						{#if state.output}
							<div class="output file small">
								<p class="fname">{state.output.label}</p>
								<CodePanel file={asFile(state.output.label, state.output.text)} markAdded={false} />
							</div>
						{/if}
						<div class="after-step">
							<p class="snap-title">{state.id ? `The files after step ${state.id}` : 'The files at the start'}</p>
							<div class="snapshot">
								{#each state.files as file (file.path)}
									{@const notes = ownOnFile(k, file.path)}
									<div class="snapshot-file">
										<div class="fname-wrap file">
											<p class="fname">{file.path}</p>
											<CodePanel {file} tones={view.tones[k]?.get(file.path)} labels={labelsOf(k, file.path)} />
										</div>
										{#if notes.length}
											<ol class="co-list" aria-label="Notes on {file.path}">
												{#each notes as callout (callout.label)}
													<li class="co {callout.tone}"><p><span class="lab">{callout.label}</span> {@html toneMarks(callout.html, level)}</p></li>
												{/each}
											</ol>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					</article>
				{/each}
			</div>

			<aside class="specimen" aria-label="The files as they stand at the active step">
				<Specimen
					{level}
					files={states[current]!.files}
					tones={view.tones[current]}
					callouts={view.callouts[current] ?? []}
					layout={mode === 'pinned' ? 'margins' : 'list'}
					fixed={mode === 'pinned'}
					live
					stateKey={current}
					bind:tab
				/>
			</aside>
		</div>
		<div class="snaps" aria-hidden="true">
			{#each { length: states.length + 1 }, k (k)}
				<div class="snap" style:--k={k} bind:this={snaps[k]}></div>
			{/each}
		</div>
	</div>
</section>
