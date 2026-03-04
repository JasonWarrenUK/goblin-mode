#!/bin/bash
set -euo pipefail

# Only run in remote (web) sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
	exit 0
fi

ENV="$CLAUDE_ENV_FILE"
PROJECT="$CLAUDE_PROJECT_DIR"

# ─── Project Identity ────────────────────────────────────────────────

# Project name (from package.json, fallback to directory name)
if [ -f "$PROJECT/package.json" ]; then
	PROJECT_NAME=$(grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' "$PROJECT/package.json" | head -1 | sed 's/"name"[[:space:]]*:[[:space:]]*"//;s/"$//')
fi
if [ -z "${PROJECT_NAME:-}" ]; then
	PROJECT_NAME=$(basename "$PROJECT")
fi
echo "export PROJECT_NAME=\"$PROJECT_NAME\"" >> "$ENV"

# ─── Project Detection ───────────────────────────────────────────────

# Package manager
if [ -f "$PROJECT/bun.lockb" ] || [ -f "$PROJECT/bun.lock" ]; then
	echo 'export PACKAGE_MANAGER="bun"' >> "$ENV"
elif [ -f "$PROJECT/pnpm-lock.yaml" ]; then
	echo 'export PACKAGE_MANAGER="pnpm"' >> "$ENV"
elif [ -f "$PROJECT/yarn.lock" ]; then
	echo 'export PACKAGE_MANAGER="yarn"' >> "$ENV"
elif [ -f "$PROJECT/package-lock.json" ]; then
	echo 'export PACKAGE_MANAGER="npm"' >> "$ENV"
elif [ -f "$PROJECT/requirements.txt" ] || [ -f "$PROJECT/pyproject.toml" ]; then
	echo 'export PACKAGE_MANAGER="pip"' >> "$ENV"
fi

# Framework detection
if [ -f "$PROJECT/svelte.config.js" ] || [ -f "$PROJECT/svelte.config.ts" ]; then
	echo 'export FRAMEWORK="sveltekit"' >> "$ENV"
elif [ -f "$PROJECT/next.config.js" ] || [ -f "$PROJECT/next.config.ts" ] || [ -f "$PROJECT/next.config.mjs" ]; then
	echo 'export FRAMEWORK="nextjs"' >> "$ENV"
elif [ -f "$PROJECT/vite.config.ts" ] || [ -f "$PROJECT/vite.config.js" ]; then
	echo 'export FRAMEWORK="vite"' >> "$ENV"
elif [ -f "$PROJECT/package.json" ]; then
	echo 'export FRAMEWORK="node"' >> "$ENV"
elif [ -f "$PROJECT/pyproject.toml" ] || [ -f "$PROJECT/setup.py" ]; then
	echo 'export FRAMEWORK="python"' >> "$ENV"
fi

# Test runner
if [ -f "$PROJECT/vitest.config.ts" ] || [ -f "$PROJECT/vitest.config.js" ]; then
	echo 'export TEST_RUNNER="vitest"' >> "$ENV"
elif [ -f "$PROJECT/jest.config.ts" ] || [ -f "$PROJECT/jest.config.js" ] || [ -f "$PROJECT/jest.config.cjs" ]; then
	echo 'export TEST_RUNNER="jest"' >> "$ENV"
elif [ -f "$PROJECT/bun.lockb" ] && grep -q '"test"' "$PROJECT/package.json" 2>/dev/null; then
	echo 'export TEST_RUNNER="bun test"' >> "$ENV"
elif [ -f "$PROJECT/pytest.ini" ] || [ -f "$PROJECT/pyproject.toml" ] && grep -q "pytest" "$PROJECT/pyproject.toml" 2>/dev/null; then
	echo 'export TEST_RUNNER="pytest"' >> "$ENV"
fi

# Database detection
DATABASES=""
if [ -f "$PROJECT/.env" ] || [ -f "$PROJECT/.env.local" ]; then
	if grep -ql "SUPABASE\|supabase" "$PROJECT/.env" "$PROJECT/.env.local" 2>/dev/null; then
		DATABASES="${DATABASES}supabase,"
	fi
	if grep -ql "NEO4J\|neo4j" "$PROJECT/.env" "$PROJECT/.env.local" 2>/dev/null; then
		DATABASES="${DATABASES}neo4j,"
	fi
	if grep -ql "MONGO\|mongo" "$PROJECT/.env" "$PROJECT/.env.local" 2>/dev/null; then
		DATABASES="${DATABASES}mongodb,"
	fi
fi
# Also check package.json for DB client libraries
if [ -f "$PROJECT/package.json" ]; then
	if grep -q "@supabase/supabase-js" "$PROJECT/package.json" 2>/dev/null; then
		DATABASES="${DATABASES}supabase,"
	fi
	if grep -q "neo4j-driver" "$PROJECT/package.json" 2>/dev/null; then
		DATABASES="${DATABASES}neo4j,"
	fi
	if grep -q "mongoose\|mongodb" "$PROJECT/package.json" 2>/dev/null; then
		DATABASES="${DATABASES}mongodb,"
	fi
fi
# Deduplicate and trim trailing comma
if [ -n "$DATABASES" ]; then
	DATABASES=$(echo "$DATABASES" | tr ',' '\n' | sort -u | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
	echo "export DATABASES=\"$DATABASES\"" >> "$ENV"
fi

# Linter detection
if [ -f "$PROJECT/eslint.config.js" ] || [ -f "$PROJECT/eslint.config.ts" ] || [ -f "$PROJECT/.eslintrc.js" ] || [ -f "$PROJECT/.eslintrc.json" ]; then
	echo 'export LINTER="eslint"' >> "$ENV"
elif [ -f "$PROJECT/biome.json" ] || [ -f "$PROJECT/biome.jsonc" ]; then
	echo 'export LINTER="biome"' >> "$ENV"
fi

# ─── Architecture Detection ──────────────────────────────────────────

# Database ORM/client
if [ -f "$PROJECT/prisma/schema.prisma" ]; then
	echo 'export DATABASE_ORM="prisma"' >> "$ENV"
elif [ -f "$PROJECT/drizzle.config.ts" ] || [ -f "$PROJECT/drizzle.config.js" ]; then
	echo 'export DATABASE_ORM="drizzle"' >> "$ENV"
elif [ -f "$PROJECT/package.json" ] && grep -q "@supabase/supabase-js" "$PROJECT/package.json" 2>/dev/null; then
	echo 'export DATABASE_ORM="supabase-client"' >> "$ENV"
fi

# API style
if [ -d "$PROJECT/src/trpc" ] || ([ -f "$PROJECT/package.json" ] && grep -q "@trpc" "$PROJECT/package.json" 2>/dev/null); then
	echo 'export API_STYLE="trpc"' >> "$ENV"
elif find "$PROJECT/src" -maxdepth 3 -name "*.graphql" -o -name "*.gql" 2>/dev/null | head -1 | grep -q .; then
	echo 'export API_STYLE="graphql"' >> "$ENV"
elif [ -d "$PROJECT/src/routes/api" ] || [ -d "$PROJECT/src/app/api" ] || [ -d "$PROJECT/src/pages/api" ]; then
	echo 'export API_STYLE="rest"' >> "$ENV"
fi

# Monorepo detection
if [ -f "$PROJECT/turbo.json" ]; then
	echo 'export MONOREPO="turborepo"' >> "$ENV"
elif [ -f "$PROJECT/nx.json" ]; then
	echo 'export MONOREPO="nx"' >> "$ENV"
elif [ -f "$PROJECT/pnpm-workspace.yaml" ]; then
	echo 'export MONOREPO="pnpm-workspaces"' >> "$ENV"
elif [ -f "$PROJECT/package.json" ] && grep -q '"workspaces"' "$PROJECT/package.json" 2>/dev/null; then
	echo 'export MONOREPO="npm-workspaces"' >> "$ENV"
fi

# ─── Git Context ─────────────────────────────────────────────────────

if git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	BRANCH=$(git -C "$PROJECT" branch --show-current 2>/dev/null || echo "detached")
	echo "export GIT_BRANCH=\"$BRANCH\"" >> "$ENV"

	# Branch type (feat/, fix/, enhance/, refactor/, test/, docs/, config/, claude/)
	BRANCH_TYPE=$(echo "$BRANCH" | sed -n 's@^\([a-z]*\)/.*@\1@p')
	if [ -n "$BRANCH_TYPE" ]; then
		echo "export GIT_BRANCH_TYPE=\"$BRANCH_TYPE\"" >> "$ENV"
	fi

	# Default branch
	DEFAULT_BRANCH=$(git -C "$PROJECT" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
	echo "export GIT_DEFAULT_BRANCH=\"$DEFAULT_BRANCH\"" >> "$ENV"

	# Commits ahead of default branch
	AHEAD=$(git -C "$PROJECT" rev-list --count "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null || echo "0")
	echo "export GIT_COMMITS_AHEAD=\"$AHEAD\"" >> "$ENV"

	# Recent commits (last 5, one-line)
	RECENT=$(git -C "$PROJECT" log --oneline -5 2>/dev/null || echo "no history")
	echo "export GIT_RECENT_COMMITS=\"$RECENT\"" >> "$ENV"

	# Uncommitted changes summary
	DIRTY=$(git -C "$PROJECT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
	echo "export GIT_DIRTY_FILES=\"$DIRTY\"" >> "$ENV"

	# Stash count
	STASHES=$(git -C "$PROJECT" stash list 2>/dev/null | wc -l | tr -d ' ')
	if [ "$STASHES" -gt 0 ]; then
		echo "export GIT_STASH_COUNT=\"$STASHES\"" >> "$ENV"
	fi
fi

# ─── Dependency Installation ─────────────────────────────────────────

# Install dependencies if node_modules is missing
if [ -f "$PROJECT/package.json" ] && [ ! -d "$PROJECT/node_modules" ]; then
	if [ -f "$PROJECT/bun.lockb" ] || [ -f "$PROJECT/bun.lock" ]; then
		(cd "$PROJECT" && bun install 2>/dev/null) || true
	elif [ -f "$PROJECT/pnpm-lock.yaml" ]; then
		(cd "$PROJECT" && pnpm install 2>/dev/null) || true
	elif [ -f "$PROJECT/package-lock.json" ]; then
		(cd "$PROJECT" && npm install 2>/dev/null) || true
	fi
fi

if [ -f "$PROJECT/requirements.txt" ] && ! python3 -c "import pkg_resources; pkg_resources.require(open('$PROJECT/requirements.txt').read().splitlines())" 2>/dev/null; then
	pip install -r "$PROJECT/requirements.txt" 2>/dev/null || true
fi
