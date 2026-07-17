# SvelteKit Routes and Middleware

Detail for `role-expert-api_designer` — SvelteKit endpoint patterns and middleware composition.

## SvelteKit API Routes

### Basic GET Endpoint
```typescript
// src/routes/api/users/+server.ts
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
	const limit = parseInt(url.searchParams.get('limit') || '10');
	const offset = parseInt(url.searchParams.get('offset') || '0');

	const users = await db.users.findMany(limit, offset);
	const total = await db.users.count();

	return json({
		success: true,
		data: {
			users,
			total,
			limit,
			offset
		}
	});
};
```

### POST with Validation
```typescript
// src/routes/api/users/+server.ts
import { json } from '@sveltejs/kit';
import { CreateUserSchema } from '$lib/schemas';
import { handleApiError } from '$lib/server/errors';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request }) => {
	try {
		const body = await request.json();

		// Validate with Zod
		const data = CreateUserSchema.parse(body);

		// Business logic
		const user = await createUser(data);

		return json({
			success: true,
			data: user
		}, { status: 201 });

	} catch (error) {
		return handleApiError(error);
	}
};
```

### Dynamic Route Parameters
```typescript
// src/routes/api/users/[id]/+server.ts
import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params }) => {
	const result = await findUser(params.id);

	if (!result.success) {
		throw error(404, 'User not found');
	}

	return json({
		success: true,
		data: result.data
	});
};

export const PATCH: RequestHandler = async ({ params, request }) => {
	try {
		const body = await request.json();
		const data = UpdateUserSchema.parse(body);

		const user = await updateUser(params.id, data);

		return json({
			success: true,
			data: user
		});

	} catch (error) {
		return handleApiError(error);
	}
};

export const DELETE: RequestHandler = async ({ params }) => {
	await deleteUser(params.id);

	return new Response(null, { status: 204 });
};
```

## Middleware Patterns

**Key principle**: Middleware are reusable functions for cross-cutting concerns.

### Authentication Middleware
```typescript
// lib/server/middleware/auth.ts
import { error } from '@sveltejs/kit';
import type { RequestEvent } from '@sveltejs/kit';

export async function requireAuth(event: RequestEvent): Promise<User> {
	const session = event.cookies.get('session');

	if (!session) {
		throw error(401, 'Authentication required');
	}

	const user = await verifySession(session);

	if (!user) {
		throw error(401, 'Invalid session');
	}

	return user;
}

// Usage
export const GET: RequestHandler = async (event) => {
	const user = await requireAuth(event);
	// Now we know user is authenticated
	const data = await getUserData(user.id);
	return json({ success: true, data });
};
```

### Validation Middleware
```typescript
// lib/server/middleware/validate.ts
import { type z } from 'zod';
import { handleApiError } from '$lib/server/errors';

export async function validateRequest<T extends z.ZodType>(
	request: Request,
	schema: T
): Promise<z.infer<T>> {
	const body = await request.json();
	return schema.parse(body); // Throws ZodError if invalid
}

// Usage
export const POST: RequestHandler = async ({ request }) => {
	try {
		const data = await validateRequest(request, CreateUserSchema);
		// data is fully typed as CreateUserRequest!

		const user = await createUser(data);
		return json({ success: true, data: user });

	} catch (error) {
		return handleApiError(error);
	}
};
```

### Rate Limiting Middleware

**Note**: Simple in-memory pattern for learning/development. Production apps should use Redis or external service.
```typescript
// lib/server/middleware/rateLimit.ts
const rateLimits = new Map<string, { count: number; resetAt: number }>();

export function checkRateLimit(
	key: string,
	maxRequests: number = 10,
	windowMs: number = 60000 // 1 minute
): boolean {
	const now = Date.now();
	const limit = rateLimits.get(key);

	if (!limit || now > limit.resetAt) {
		rateLimits.set(key, {
			count: 1,
			resetAt: now + windowMs
		});
		return true;
	}

	if (limit.count >= maxRequests) {
		return false;
	}

	limit.count++;
	return true;
}

// Usage
export const POST: RequestHandler = async ({ request, getClientAddress }) => {
	const ip = getClientAddress();

	if (!checkRateLimit(ip, 10, 60000)) {
		throw error(429, 'Too many requests');
	}

	// Continue with request
};
```

### Composing Middleware
```typescript
// lib/server/middleware/compose.ts
export async function withMiddleware<T>(
	event: RequestEvent,
	...middlewares: Array<(event: RequestEvent) => Promise<any>>
): Promise<T[]> {
	const results = [];
	for (const middleware of middlewares) {
		results.push(await middleware(event));
	}
	return results as T[];
}

// Usage
export const POST: RequestHandler = async (event) => {
	const [user, data] = await withMiddleware<[User, CreatePostRequest]>(
		event,
		requireAuth,
		(e) => validateRequest(e.request, CreatePostSchema)
	);

	const post = await createPost(user.id, data);
	return json({ success: true, data: post });
};
```
