# Technical Profile

Moved from CLAUDE.md section 1 on 2026-10-21. Text is unchanged.

Options are listed in order of preference & proficiency

### 1a. Scales: Preference & Proficiency

#### 1a1. Preference

| Value | Definition |
|-------|------------|
|   1   | "Love using" or "Learning this is a high priority" |
|   2   | "Like using" or "Want to learn" |
|   3   | "No strong feelings" |
|   4   | "Dislike using" or "Not that interested in learning" |
|   5   | "Hate using" or "Actively don't want to learn" |

#### 1a2. Proficiency

| Value | Definition |
|-------|------------|
|   1   | Proficient with advanced features |
|   2   | Proficient with base features |
|   3   | Actively learning or limited experience |
|   4   | Have dabbled slightly |
|   5   | No experience |

### 1b. Domains

#### 1b1. Languages

| Priority | Status     | Language |
|----------|------------|----------|
|    1     | Preferred  | TypeScript |
|    2     | Proficient | JavaScript |
|    3     | Proficient |  Python  |
|    4     |  Learning  |    Go    |
|    5     |  Dabbled   | GDScript |
|    6     |  Dabbled   |    C#    |

### 1.2. Frontend

| #   | Status        | Front End | Full Stack |
|-----|---------------|-----------|------------|
|  1  |   Preferred   | Svelte 5  | SvelteKit 2 |
|  2  | When Required |   React   |  Next.js   |

### 1.3. Backend

| #   | Status        | Runtime | Server |
|-----|---------------|---------|--------|
|  1  |   Preferred   |   Bun   | undecided |
|  2  |  Proficient   | Python  | FastAPI (Poetry, poethepoet, pytest) |
|  3  |  Interested   |  Deno   |  Oak   |
|  4  | When Required |  Node   | Express |

### 1.4. TUI

This is ordered by *familiarity*, not preference

| #   | Language | Libraries |
|-----|----------|-----------|
|  1  |    Go    | Charm (bubbletea, bubbles, lipgloss etc) |
|  2  |    TS    |  OpenTUI  |
|  3  |  Python  |  Textual  |

### 1.5. Databases

One db tech stack per paradigm

| Paradigm   | Stack                | Notes |
|------------|----------------------|-------|
| Relational | PostgreSQL, Supabase | RLS expertise; pgvector for embeddings |
|   Graph    |        Neo4j         | Preferred data model |
|   Object   |       MongoDB        | Limited experience: Auth.js adapter and mongodb-memory-server integration tests in Urheimat |

### 1.6. Testing

No stated preference between runners. In use across current projects:

| Runner | Where |
|--------|-------|
| Vitest | SvelteKit projects; vitest-browser-svelte + Playwright for component tests and mongodb-memory-server for real-database integration tests (Urheimat) |
| bun:test | Framework-free engine code (The Tongue, Grumble) |
| pytest | FastAPI (CHIRPdb) |
| go test | Wyrd |
| GUT (headless) | Godot: unit tests for the sim layer plus one journey test per phase |
| Jest | Older React work only |

Practices already in use: save fixtures captured per tagged release and loaded under a version policy (The Work); pipeline evals against a hand-labelled gold set (CHIRPdb); deterministic seeds threaded through every sim so a run reproduces exactly.

### 1.7. Tooling

| Role       | Tool |
|------------|------|
| Versioning | git, Github, svu |
|    IDE     | Zed  |
| Deployment | Vercel, Deno Deploy, Github Pages; Docker Compose behind a Cloudflare tunnel for long-running services |
| Containers | Colima (Docker Desktop replaced June 2026) |

### 1.8 Packages & Apps

#### 1.8.1. System Apps

| #   | Tool |
|-----|------|
|  1  | Homebrew |

#### 1.8.2. JS/TS Ecosystem

Primarily determined by project context, but for tiebreaks use the following preference order:

| #   | Tool |
|-----|------|
|  1  | bun  |
|  2  | deno |
|  3  | npm, pnpm |

#### 1.8.3. Other Ecosystems

Python: Poetry with poethepoet as the task runner is what production work uses; the roadmap plugin's scripts stay stdlib-only. No favoured package manager decided beyond that.

