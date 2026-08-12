# Privacy-by-Default Patterns

Detail for `role-expert-api_designer`.

## Principle

APIs should collect, expose, and store the minimum data needed. Privacy is a design constraint, not an afterthought.

## Response Filtering
```typescript
// ✗ Bad: Returning everything from the database
export const GET: RequestHandler = async ({ params }) => {
	const user = await db.users.findUnique(params.id);
	return json({ success: true, data: user }); // Exposes internal fields
};

// ✓ Good: Explicit response shaping
export const GET: RequestHandler = async ({ params }) => {
	const user = await db.users.findUnique(params.id);
	return json({
		success: true,
		data: {
			id: user.id,
			name: user.name,
			avatarUrl: user.avatarUrl
			// No email, no internal IDs, no metadata
		}
	});
};
```

## Request Minimisation
```typescript
// ✗ Bad: Collecting data you don't need
const SignupSchema = z.object({
	email: z.string().email(),
	name: z.string(),
	phone: z.string(),        // Do you actually need this?
	dateOfBirth: z.string(),   // Do you actually need this?
	address: z.string(),       // Do you actually need this?
});

// ✓ Good: Collect only what's required for the feature
const SignupSchema = z.object({
	email: z.string().email(),
	name: z.string(),
});
```

## Sensitive Data Handling
```typescript
// Never log sensitive data
function logApiRequest(req: Request, body: unknown) {
	const sanitised = { ...body };
	delete sanitised.password;
	delete sanitised.token;
	delete sanitised.creditCard;
	console.log('API request:', sanitised);
}

// Never expose internal IDs unnecessarily
// Use public-facing slugs or UUIDs, not sequential database IDs
```

## Auth Scoping
```typescript
// ✗ Bad: Endpoint returns all users' data
export const GET: RequestHandler = async () => {
	const users = await db.users.findMany();
	return json({ success: true, data: users });
};

// ✓ Good: Scoped to authenticated user's data
export const GET: RequestHandler = async (event) => {
	const user = await requireAuth(event);
	const data = await db.users.findByOrganisation(user.organisationId);
	return json({ success: true, data });
};
```

## Data Deletion
```typescript
// Provide clear deletion endpoints
export const DELETE: RequestHandler = async (event) => {
	const user = await requireAuth(event);

	// Delete user data across all stores
	await db.users.delete(user.id);
	await neo4j.run('MATCH (u:User {id: $id}) DETACH DELETE u', { id: user.id });
	await mongo.collection('preferences').deleteOne({ _id: user.id });

	return new Response(null, { status: 204 });
};
```
