# Validation and Error Handling

Detail for `role-expert-api_designer` — Zod validation and error-handling patterns.

## Validation with Zod

### Why Zod

- TypeScript-first (infers types from schemas)
- Works client/server/shared
- Composable schemas
- Excellent error messages
- Incremental adoption (add as needed)

### Basic Schema
```typescript
import { z } from 'zod';

export const CreateUserSchema = z.object({
	email: z.string().email(),
	name: z.string().min(2).max(100),
	password: z.string().min(8)
});

// Type automatically inferred!
export type CreateUserRequest = z.infer<typeof CreateUserSchema>;
```

### Complex Validation
```typescript
export const UpdateUserSchema = z.object({
	email: z.string().email().optional(),
	name: z.string().min(2).max(100).optional(),
	age: z.number().int().min(18).max(120).optional(),
	preferences: z.object({
		theme: z.enum(['light', 'dark']),
		notifications: z.boolean(),
		language: z.string().length(2) // ISO 639-1
	}).optional()
}).refine(
	(data) => Object.keys(data).length > 0,
	{ message: 'At least one field must be provided' }
);
```

### Custom Validation Rules
```typescript
export const PasswordSchema = z.string()
	.min(8, 'Password must be at least 8 characters')
	.regex(/[A-Z]/, 'Must contain uppercase letter')
	.regex(/[a-z]/, 'Must contain lowercase letter')
	.regex(/[0-9]/, 'Must contain number')
	.regex(/[^A-Za-z0-9]/, 'Must contain special character');

export const StrongPasswordSchema = z.object({
	password: PasswordSchema,
	confirmPassword: z.string()
}).refine(
	(data) => data.password === data.confirmPassword,
	{ message: 'Passwords must match', path: ['confirmPassword'] }
);
```

### Nested Schemas
```typescript
const AddressSchema = z.object({
	street: z.string(),
	city: z.string(),
	country: z.string(),
	postalCode: z.string()
});

const UserSchema = z.object({
	name: z.string(),
	email: z.string().email(),
	address: AddressSchema,
	billingAddress: AddressSchema.optional()
});

type User = z.infer<typeof UserSchema>;
```

### Schema Composition
```typescript
// Base user fields
const BaseUserSchema = z.object({
	email: z.string().email(),
	name: z.string()
});

// Create adds password
const CreateUserSchema = BaseUserSchema.extend({
	password: PasswordSchema
});

// Update makes everything optional
const UpdateUserSchema = BaseUserSchema.partial();
```

## Error Handling Patterns

### Result Types (Expected Failures)
```typescript
// For operations that may legitimately fail
export type Result<T, E = string> =
	| { success: true; data: T }
	| { success: false; error: E };

// Usage in business logic
function findUser(id: string): Result<User, 'not_found' | 'invalid_id'> {
	if (!isValidId(id)) {
		return { success: false, error: 'invalid_id' };
	}

	const user = db.findUser(id);
	if (!user) {
		return { success: false, error: 'not_found' };
	}

	return { success: true, data: user };
}
```

### Error Classes (Unexpected Failures)
```typescript
// For exceptional cases that should be thrown
export class ApiError extends Error {
	constructor(
		public code: string,
		message: string,
		public statusCode: number = 500,
		public details?: Record<string, string[]>
	) {
		super(message);
		this.name = 'ApiError';
	}
}

export class ValidationError extends ApiError {
	constructor(details: Record<string, string[]>) {
		super('VALIDATION_ERROR', 'Validation failed', 400, details);
	}
}

export class NotFoundError extends ApiError {
	constructor(resource: string) {
		super('NOT_FOUND', `${resource} not found`, 404);
	}
}

export class UnauthorizedError extends ApiError {
	constructor(message = 'Authentication required') {
		super('UNAUTHORIZED', message, 401);
	}
}

export class ConflictError extends ApiError {
	constructor(message: string) {
		super('CONFLICT', message, 409);
	}
}
```

### When to Use Each

**Result Types** - Expected failures:
- User not found
- Validation failures
- Business rule violations
- Resource conflicts

**Error Classes** - Exceptional cases:
- Database connection failures
- Configuration errors
- Invalid application state
- Unexpected system errors

### Centralized Error Handler
```typescript
// lib/server/errors.ts
import { json } from '@sveltejs/kit';
import { ZodError } from 'zod';

export function handleApiError(error: unknown) {
	// Zod validation errors
	if (error instanceof ZodError) {
		return json({
			success: false,
			error: {
				code: 'VALIDATION_ERROR',
				message: 'Validation failed',
				details: error.flatten().fieldErrors
			}
		}, { status: 400 });
	}

	// Custom API errors
	if (error instanceof ApiError) {
		return json({
			success: false,
			error: {
				code: error.code,
				message: error.message,
				details: error.details
			}
		}, { status: error.statusCode });
	}

	// Unknown errors - don't expose details
	console.error('Unexpected error:', error);
	return json({
		success: false,
		error: {
			code: 'INTERNAL_ERROR',
			message: 'An unexpected error occurred'
		}
	}, { status: 500 });
}
```
