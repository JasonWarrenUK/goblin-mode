# SvelteKit Routing, Data Loading, Form Actions

Detail for `svelte-ninja`.

## SvelteKit Routing

### File-based Routing
```
src/routes/
├── +page.svelte              # /
├── about/
│   └── +page.svelte          # /about
├── blog/
│   ├── +page.svelte          # /blog
│   └── [slug]/
│       └── +page.svelte      # /blog/:slug
└── (app)/
    ├── dashboard/
    │   └── +page.svelte      # /dashboard
    └── settings/
        └── +page.svelte      # /settings
```

**Route groups** `(app)`: Don't affect URL, useful for layouts

### Dynamic Routes
```svelte
<!-- src/routes/blog/[slug]/+page.svelte -->
<script>
	let { data } = $props();
</script>

<h1>{data.post.title}</h1>
<div>{@html data.post.content}</div>
```
```javascript
// src/routes/blog/[slug]/+page.js
export async function load({ params }) {
	const post = await fetchPost(params.slug);
	return { post };
}
```

### Optional Parameters
```
src/routes/archive/[[year]]/[[month]]/+page.svelte
```

Matches:
- `/archive`
- `/archive/2024`
- `/archive/2024/12`

## Data Loading

### +page.js Load Functions
```javascript
// src/routes/blog/[slug]/+page.js
export async function load({ params, fetch }) {
	const post = await fetch(`/api/posts/${params.slug}`).then(r => r.json());
	
	return {
		post
	};
}
```

**Load function context**:
- `params` - Route parameters
- `fetch` - Enhanced fetch (credentials, relative URLs)
- `url` - URL object
- `route` - Route info
- `parent` - Parent load data

### +page.server.js Server Load
```javascript
// src/routes/dashboard/+page.server.js
import { db } from '$lib/server/database';

export async function load({ locals }) {
	const user = locals.user;
	const stats = await db.query('SELECT * FROM stats WHERE user_id = $1', [user.id]);
	
	return {
		stats
	};
}
```

**Server-only**:
- Access to database
- Access to environment variables
- Runs on server, never exposed to client

### Streaming with Promises
```javascript
// +page.js
export async function load({ fetch }) {
	const quick = fetch('/api/quick').then(r => r.json());
	const slow = fetch('/api/slow').then(r => r.json());
	
	return {
		quick: await quick,  // Wait for this
		slow                  // Stream this
	};
}
```
```svelte
<!-- +page.svelte -->
<script>
	let { data } = $props();
</script>

<div>{data.quick.title}</div>

{#await data.slow}
	<p>Loading...</p>
{:then slow}
	<p>{slow.content}</p>
{/await}
```

## Form Actions

### Basic Form Actions
```javascript
// src/routes/login/+page.server.js
export const actions = {
	default: async ({ request, cookies }) => {
		const data = await request.formData();
		const email = data.get('email');
		const password = data.get('password');
		
		const user = await authenticate(email, password);
		
		if (!user) {
			return { success: false, error: 'Invalid credentials' };
		}
		
		cookies.set('session', user.sessionId, { path: '/' });
		return { success: true };
	}
};
```
```svelte
<!-- src/routes/login/+page.svelte -->
<script>
	import { enhance } from '$app/forms';
	let { form } = $props();
</script>

<form method="POST" use:enhance>
	<input name="email" type="email" required />
	<input name="password" type="password" required />
	<button>Log in</button>
	
	{#if form?.error}
		<p class="error">{form.error}</p>
	{/if}
</form>
```

### Named Actions
```javascript
// +page.server.js
export const actions = {
	create: async ({ request }) => {
		// Handle create
	},
	update: async ({ request }) => {
		// Handle update
	},
	delete: async ({ request }) => {
		// Handle delete
	}
};
```
```svelte
<form method="POST" action="?/create">
	<!-- create form -->
</form>

<form method="POST" action="?/update">
	<!-- update form -->
</form>
```

### Progressive Enhancement
```svelte
<script>
	import { enhance } from '$app/forms';
</script>

<form 
	method="POST" 
	use:enhance={({ formData, cancel }) => {
		// Run before submission
		if (!confirm('Are you sure?')) {
			cancel();
		}
		
		return async ({ result, update }) => {
			// Run after response
			if (result.type === 'success') {
				await update();
				alert('Success!');
			}
		};
	}}
>
	<!-- form fields -->
</form>
```
