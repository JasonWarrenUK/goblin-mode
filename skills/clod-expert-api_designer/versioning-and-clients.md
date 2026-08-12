# Versioning, Type-Safe Clients, OpenAPI, and Testing

Detail for `role-expert-api_designer` — API lifecycle patterns beyond initial design.

## API Versioning

**Recommended approach**: URL-based versioning

### Directory Structure
```
src/routes/api/
├── v1/
│   ├── users/
│   │   └── +server.ts
│   └── posts/
│       └── +server.ts
└── v2/
    ├── users/
    │   ├── +server.ts
    │   └── [id]/+server.ts
    └── posts/
        └── +server.ts
```

### Version-Specific Types
```typescript
// types/api/v1.ts
export interface UserV1 {
	id: string;
	name: string;
}

// types/api/v2.ts
export interface UserV2 {
	id: string;
	name: string;
	email: string;      // Added in v2
	createdAt: string;  // Added in v2
}
```

### Shared Business Logic
```typescript
// lib/services/users.ts
import type { UserV1, UserV2 } from '$lib/types/api';

export async function getUserById(id: string): Promise<User> {
	// Single source of truth
	return await db.users.findUnique(id);
}

// Transform for v1
export function toUserV1(user: User): UserV1 {
	return {
		id: user.id,
		name: user.name
	};
}

// Transform for v2
export function toUserV2(user: User): UserV2 {
	return {
		id: user.id,
		name: user.name,
		email: user.email,
		createdAt: user.createdAt
	};
}
```

### Version-Specific Endpoints
```typescript
// src/routes/api/v1/users/[id]/+server.ts
import { toUserV1 } from '$lib/services/users';

export const GET: RequestHandler = async ({ params }) => {
	const user = await getUserById(params.id);
	return json({
		success: true,
		data: toUserV1(user) // v1 format
	});
};

// src/routes/api/v2/users/[id]/+server.ts
import { toUserV2 } from '$lib/services/users';

export const GET: RequestHandler = async ({ params }) => {
	const user = await getUserById(params.id);
	return json({
		success: true,
		data: toUserV2(user) // v2 format
	});
};
```

### When to Version

**Create new version when**:
- Breaking changes to existing endpoints
- Removing fields
- Changing field types
- Changing behavior significantly

**Don't version for**:
- Adding optional fields (backward compatible)
- New endpoints
- Bug fixes
- Performance improvements

## Type-Safe API Client

**Pattern**: Create typed wrapper functions for consuming your API.

### Basic Client
```typescript
// lib/api/client.ts
export class ApiClient {
	constructor(private baseUrl: string = '') {}

	private async request<T>(
		method: string,
		endpoint: string,
		data?: any
	): Promise<T> {
		const response = await fetch(`${this.baseUrl}${endpoint}`, {
			method,
			headers: {
				'Content-Type': 'application/json'
			},
			body: data ? JSON.stringify(data) : undefined
		});

		const json = await response.json();

		if (!json.success) {
			throw new ApiError(
				json.error.code,
				json.error.message,
				response.status,
				json.error.details
			);
		}

		return json.data;
	}

	get<T>(endpoint: string): Promise<T> {
		return this.request<T>('GET', endpoint);
	}

	post<T>(endpoint: string, data: any): Promise<T> {
		return this.request<T>('POST', endpoint, data);
	}

	patch<T>(endpoint: string, data: any): Promise<T> {
		return this.request<T>('PATCH', endpoint, data);
	}

	delete(endpoint: string): Promise<void> {
		return this.request<void>('DELETE', endpoint);
	}
}
```

### Type-Safe API Methods
```typescript
// lib/api/users.ts
import { ApiClient } from './client';
import type { CreateUserRequest, User, UpdateUserRequest } from '$lib/types/api';

export class UsersApi {
	constructor(private client: ApiClient) {}

	create(data: CreateUserRequest): Promise<User> {
		return this.client.post<User>('/api/users', data);
	}

	get(id: string): Promise<User> {
		return this.client.get<User>(`/api/users/${id}`);
	}

	update(id: string, data: UpdateUserRequest): Promise<User> {
		return this.client.patch<User>(`/api/users/${id}`, data);
	}

	delete(id: string): Promise<void> {
		return this.client.delete(`/api/users/${id}`);
	}

	list(params: { limit?: number; offset?: number } = {}): Promise<User[]> {
		const query = new URLSearchParams(
			Object.entries(params)
				.filter(([_, v]) => v !== undefined)
				.map(([k, v]) => [k, String(v)])
		);

		return this.client.get<User[]>(`/api/users?${query}`);
	}
}

// Main API object
export const api = {
	users: new UsersApi(new ApiClient())
};
```

### Usage (Fully Typed!)
```typescript
import { api } from '$lib/api';

// TypeScript knows CreateUserRequest shape
const user = await api.users.create({
	email: 'alice@example.com',
	name: 'Alice',
	password: 'secure123'
});

// TypeScript knows user is User type
console.log(user.email); // ✓ Type-safe
console.log(user.invalidField); // ✗ TypeScript error

// List users with typed params
const users = await api.users.list({ limit: 10, offset: 0 });
```

## Optional: OpenAPI Generation

**Using zod-to-openapi** (much easier than manual Swagger)

### Setup
```bash
npm install zod-openapi @asteasolutions/zod-to-openapi
```

### Extend Schemas with OpenAPI Metadata
```typescript
// lib/schemas/users.ts
import { z } from 'zod';
import { extendZodWithOpenApi } from '@asteasolutions/zod-to-openapi';

extendZodWithOpenApi(z);

export const CreateUserSchema = z.object({
	email: z.string().email().openapi({
		example: 'alice@example.com',
		description: 'User email address'
	}),
	name: z.string().min(2).openapi({
		example: 'Alice Smith'
	}),
	password: z.string().min(8).openapi({
		example: 'SecurePass123!',
		description: 'Minimum 8 characters'
	})
}).openapi('CreateUserRequest');

export const UserSchema = z.object({
	id: z.string().uuid(),
	email: z.string().email(),
	name: z.string(),
	createdAt: z.string().datetime()
}).openapi('User');
```

### Generate OpenAPI Spec
```typescript
// scripts/generateOpenApi.ts
import { OpenAPIRegistry, OpenApiGeneratorV3 } from '@asteasolutions/zod-to-openapi';
import { CreateUserSchema, UserSchema } from '../src/lib/schemas/users';

const registry = new OpenAPIRegistry();

// Register schemas
registry.register('CreateUserRequest', CreateUserSchema);
registry.register('User', UserSchema);

// Register paths
registry.registerPath({
	method: 'post',
	path: '/api/users',
	request: {
		body: {
			content: {
				'application/json': {
					schema: CreateUserSchema
				}
			}
		}
	},
	responses: {
		201: {
			description: 'User created',
			content: {
				'application/json': {
					schema: UserSchema
				}
			}
		}
	}
});

const generator = new OpenApiGeneratorV3(registry.definitions);

const docs = generator.generateDocument({
	openapi: '3.0.0',
	info: {
		title: 'My API',
		version: '1.0.0'
	}
});

console.log(JSON.stringify(docs, null, 2));
```

## Testing APIs

### Testing Endpoints
```typescript
// src/routes/api/users/+server.test.ts
import { describe, it, expect, vi } from 'vitest';
import { POST } from './+server';

describe('POST /api/users', () => {
	it('should create user with valid data', async () => {
		const request = new Request('http://localhost/api/users', {
			method: 'POST',
			body: JSON.stringify({
				email: 'test@example.com',
				name: 'Test User',
				password: 'password123'
			})
		});

		const response = await POST({ request } as any);
		const data = await response.json();

		expect(response.status).toBe(201);
		expect(data.success).toBe(true);
		expect(data.data).toHaveProperty('id');
		expect(data.data.email).toBe('test@example.com');
	});

	it('should reject invalid email', async () => {
		const request = new Request('http://localhost/api/users', {
			method: 'POST',
			body: JSON.stringify({
				email: 'invalid-email',
				name: 'Test',
				password: 'password123'
			})
		});

		const response = await POST({ request } as any);
		const data = await response.json();

		expect(response.status).toBe(400);
		expect(data.success).toBe(false);
		expect(data.error.code).toBe('VALIDATION_ERROR');
	});

	it('should reject short password', async () => {
		const request = new Request('http://localhost/api/users', {
			method: 'POST',
			body: JSON.stringify({
				email: 'test@example.com',
				name: 'Test',
				password: '123'
			})
		});

		const response = await POST({ request } as any);
		const data = await response.json();

		expect(response.status).toBe(400);
		expect(data.error.details).toHaveProperty('password');
	});
});
```

### Testing Business Logic
```typescript
// lib/services/users.test.ts
import { describe, it, expect } from 'vitest';
import { createUser, findUser } from './users';

describe('createUser', () => {
	it('should create user successfully', async () => {
		const data = {
			email: 'test@example.com',
			name: 'Test User',
			passwordHash: 'hashed'
		};

		const user = await createUser(data);

		expect(user).toHaveProperty('id');
		expect(user.email).toBe(data.email);
		expect(user.name).toBe(data.name);
	});
});

describe('findUser', () => {
	it('should return null for non-existent user', async () => {
		const user = await findUser('non-existent-id');
		expect(user).toBeNull();
	});

	it('should return user when exists', async () => {
		const created = await createUser({
			email: 'test@example.com',
			name: 'Test',
			passwordHash: 'hashed'
		});

		const found = await findUser(created.id);
		expect(found).not.toBeNull();
		expect(found?.id).toBe(created.id);
	});
});
```
