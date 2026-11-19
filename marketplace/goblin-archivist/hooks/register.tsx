// goblin-archivist: connects Claude Code sessions on this Mac to one Obsidian
// vault. This first slice ships only the read-only survey skill
// (/goblin-archivist:sniff-vault), so the mod registers no handler yet. The
// hooks, the pane and the band arrive in later slices; SPEC.md holds the plan.

import type { Register } from 'claude-code'

export const register: Register = (_on, options) => {
	if (options.enabled === false) return
}
