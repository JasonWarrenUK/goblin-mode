# Session Management and Database Layer

Detail for `role-expert-api_designer` — auth session patterns and typed database wrappers.

## Session Management Patterns

### Pattern 1: SvelteKit Cookies (Simple Apps)
```typescript
// lib/server/auth/cookies.ts
import type { Cookies } from '@sveltejs/kit';

export function createSession(cookies: Cookies, userId: string) {
	const sessionId = generateSessionId();

	cookies.set('session', sessionId, {
		path: '/',
		httpOnly: true,
		secure: true,
		sameSite: 'strict',
		maxAge: 60 * 60 * 24 * 7 // 1 week
	});

	// Store session in database
	await db.sessions.create({ sessionId, userId });
}

export async function getSession(cookies: Cookies): Promise<User | null> {
	const sessionId = cookies.get('session');
	if (!sessionId) return null;

	const session = await db.sessions.findUnique(sessionId);
	if (!session) return null;

	return await db.users.findUnique(session.userId);
}

export function clearSession(cookies: Cookies) {
	cookies.delete('session', { path: '/' });
}
```

**When to use**: Simple apps, server-rendered, no mobile apps.

### Pattern 2: JWT Tokens (Stateless APIs)
```typescript
// lib/server/auth/jwt.ts
import jwt from 'jsonwebtoken';

const SECRET = process.env.JWT_SECRET!;

export function createToken(userId: string): string {
	return jwt.sign(
		{ userId },
		SECRET,
		{ expiresIn: '7d' }
	);
}

export function verifyToken(token: string): { userId: string } | null {
	try {
		return jwt.verify(token, SECRET) as { userId: string };
	} catch {
		return null;
	}
}

// Middleware
export async function requireJwt(event: RequestEvent): Promise<User> {
	const auth = event.request.headers.get('Authorization');
	if (!auth?.startsWith('Bearer ')) {
		throw error(401, 'Missing token');
	}

	const token = auth.slice(7);
	const payload = verifyToken(token);

	if (!payload) {
		throw error(401, 'Invalid token');
	}

	const user = await db.users.findUnique(payload.userId);
	if (!user) {
		throw error(401, 'User not found');
	}

	return user;
}
```

**When to use**: Stateless APIs, mobile apps, microservices.

### Pattern 3: Supabase Auth (Full-Featured)
```typescript
// lib/server/auth/supabase.ts
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
	process.env.SUPABASE_URL!,
	process.env.SUPABASE_SERVICE_KEY!
);

export async function requireSupabaseAuth(event: RequestEvent): Promise<User> {
	const token = event.request.headers.get('Authorization')?.slice(7);

	if (!token) {
		throw error(401, 'Missing token');
	}

	const { data: { user }, error: authError } = await supabase.auth.getUser(token);

	if (authError || !user) {
		throw error(401, 'Invalid token');
	}

	return user;
}
```

**When to use**: Need OAuth, email verification, password reset, etc.

## Database Layer (Typed Wrappers)

**Principle**: No universal ORM for polyglot persistence. Use native clients with typed wrappers.

### PostgreSQL/Supabase Wrapper
```typescript
// lib/db/users.ts
import { supabase } from '$lib/server/supabase';

export interface CreateUserData {
	email: string;
	name: string;
	passwordHash: string;
}

export interface UpdateUserData {
	email?: string;
	name?: string;
}

export async function createUser(data: CreateUserData): Promise<User> {
	const { data: user, error } = await supabase
		.from('users')
		.insert(data)
		.select()
		.single();

	if (error) throw new Error(error.message);
	return user;
}

export async function findUser(id: string): Promise<User | null> {
	const { data: user } = await supabase
		.from('users')
		.select()
		.eq('id', id)
		.single();

	return user;
}

export async function updateUser(
	id: string,
	data: UpdateUserData
): Promise<User> {
	const { data: user, error } = await supabase
		.from('users')
		.update(data)
		.eq('id', id)
		.select()
		.single();

	if (error) throw new Error(error.message);
	return user;
}
```

### Neo4j Wrapper
```typescript
// lib/db/graph.ts
import { neo4j } from '$lib/server/neo4j';

export async function createFollowRelationship(
	followerId: string,
	followedId: string
): Promise<void> {
	await neo4j.run(`
		MATCH (a:User {id: $followerId})
		MATCH (b:User {id: $followedId})
		MERGE (a)-[:FOLLOWS {since: datetime()}]->(b)
	`, { followerId, followedId });
}

export async function getFollowers(userId: string): Promise<User[]> {
	const result = await neo4j.run(`
		MATCH (follower:User)-[:FOLLOWS]->(u:User {id: $userId})
		RETURN follower
	`, { userId });

	return result.records.map(r => r.get('follower').properties);
}

export async function getSuggestedFollows(
	userId: string,
	limit: number = 10
): Promise<User[]> {
	const result = await neo4j.run(`
		MATCH (u:User {id: $userId})-[:FOLLOWS]->()-[:FOLLOWS]->(suggestion:User)
		WHERE NOT (u)-[:FOLLOWS]->(suggestion)
		  AND u <> suggestion
		RETURN DISTINCT suggestion
		LIMIT $limit
	`, { userId, limit });

	return result.records.map(r => r.get('suggestion').properties);
}
```
