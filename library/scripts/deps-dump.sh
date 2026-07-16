#!/bin/zsh
# deps-dump.sh — dependency fact-gathering for the project-investigate-deps
# skill. Detects the package manager from lockfiles and dumps declared vs
# installed vs latest versions plus audit output in one pass, so the model
# analyses one structured dump instead of orchestrating several CLIs.
#
# usage: deps-dump.sh [project-dir]   (default .)
# exit codes: 0 ok (sections may note tool absences), 2 no recognised manifest
set -u
cd "${1:-.}" || { print -u2 "cannot cd to ${1:-.}"; exit 2 }

section() { print "\n===== $1 ====="; }

if [[ -f deno.json || -f deno.jsonc ]]; then
	section "manager: deno"
	section "manifest"; cat deno.json* 2>/dev/null
	section "outdated"; deno outdated 2>&1 || print "(deno outdated unavailable)"
elif [[ -f bun.lock || -f bun.lockb ]]; then
	section "manager: bun"
	section "declared (package.json)"; jq '{dependencies, devDependencies, peerDependencies}' package.json 2>/dev/null
	section "outdated"; bun outdated 2>&1 || print "(bun outdated failed)"
	section "audit"; bun audit 2>&1 || print "(bun audit unavailable)"
elif [[ -f pnpm-lock.yaml ]]; then
	section "manager: pnpm"
	section "declared (package.json)"; jq '{dependencies, devDependencies, peerDependencies}' package.json 2>/dev/null
	section "outdated"; pnpm outdated 2>&1 || true
	section "audit"; pnpm audit 2>&1 || true
elif [[ -f package-lock.json || -f package.json ]]; then
	section "manager: npm"
	section "declared (package.json)"; jq '{dependencies, devDependencies, peerDependencies}' package.json 2>/dev/null
	section "outdated"; npm outdated 2>&1 || true
	section "audit"; npm audit 2>&1 || true
else
	print -u2 "no recognised JS/TS manifest (package.json, deno.json, bun.lock, pnpm-lock.yaml)"
	exit 2
fi
exit 0
