# React → Svelte 5 (runes) idiom mapping

Reference for porting React/JSX code to Svelte 5. Used by
`project-scaffold-from_artefact` Step 4; applies to any React→Svelte port.

| React (JSX) | Svelte 5 (runes) | Notes |
|-------------|------------------|-------|
| `useState(x)` | `let v = $state(x)` | Direct reassignment; no setter function |
| `useEffect(fn, deps)` | `$effect(() => { ... })` | Reactive deps are tracked automatically; drop the deps array |
| `useEffect` cleanup (`return () => ...`) | `$effect(() => { ...; return () => cleanup })` | Return value is the teardown; verify it still fires on the right dependency change |
| `useMemo(fn, deps)` | `let d = $derived.by(() => ...)` (or `$derived(expr)`) | Recomputes when tracked deps change |
| `useCallback` | plain function | Rarely needed; Svelte does not re-create closures per render |
| props (`function C({a, b})`) | `let { a, b } = $props()` | Type with an interface: `let { a, b }: Props = $props()` |
| `children` | `{@render children()}` + `let { children } = $props()` | Snippets replace `props.children` |
| named slots / render props | snippets (`{#snippet}` / `{@render}`) | |
| `onClick={fn}` | `onclick={fn}` | Lowercase native event names in Svelte 5 |
| `{cond && <X/>}` | `{#if cond}<X/>{/if}` | |
| `list.map(i => <X/>)` | `{#each list as i (i.id)}<X/>{/each}` | Always provide a key expression |
| `useRef` (DOM) | `bind:this={el}` | |
| `useRef` (mutable box) | plain `let` (no rune) | Not reactive by design |
| `useContext` / `createContext` | `setContext` / `getContext` | Call during component init, not inside effects |
| `createPortal` | Svelte has no portal primitive | Use a top-level container + an action, or a small `{@render}` into a fixed element; flag as a manual port |
| `dangerouslySetInnerHTML` | `{@html value}` | Sanitise untrusted input |

## Gotchas to call out when present

- **Effect cleanup timing:** `$effect` teardown fires before re-run and on
  destroy, which differs subtly from React's dependency-array semantics.
- **Context** must be set synchronously during component init.
- **Portals** have no direct equivalent; flag as a manual port.
- A `useRef` used as a mutable box must NOT become `$state`.
