# Integration Patterns, Schema Design, and Query Optimisation

Detail for `Data Ontologist`.

## Integration Patterns

### Pattern 1: Shared Primary Keys

Use same IDs across all databases:

```typescript
const userId = generateId();

// Supabase - Auth and profile
await supabase.from('users').insert({
  id: userId,
  email,
  name
});

// Neo4j - Social graph node
await neo4j.run(`
  CREATE (u:User {id: $userId, name: $name})
`, { userId, name });

// MongoDB - User preferences
await mongo.collection('user_preferences').insertOne({
  _id: userId,
  theme: 'dark',
  notifications: {
    email: true,
    push: false
  }
});
```

### Pattern 2: Reference by ID

Store references, fetch as needed:

```typescript
// MongoDB - Blog post
{
  _id: ObjectId("..."),
  title: "My Post",
  authorId: "user-123",  // Reference to PostgreSQL user
  content: "...",
  tags: ["javascript", "svelte"]
}

// Query pattern
const post = await mongo.collection('posts').findOne({ _id });
const author = await supabase
  .from('users')
  .select('*')
  .eq('id', post.authorId)
  .single();
```

### Pattern 3: Embed vs Reference Decision

**Embed when**:
- Data accessed together
- One-to-few relationship
- Child data not shared

```javascript
// Good: Embed comments in post
{
  title: "My Post",
  comments: [
    { text: "Great!", userId: "user-123" }
  ]
}
```

**Reference when**:
- Data accessed independently
- One-to-many or many-to-many
- Child data shared across parents

```javascript
// Good: Reference author
{
  title: "My Post",
  authorId: "user-123"  // Author data in PostgreSQL
}
```

### Pattern 4: Event-Driven Sync

Keep databases in sync via events:

```typescript
// User created in Supabase
supabase.on('INSERT', 'users', async (payload) => {
  const user = payload.record;

  // Create in Neo4j
  await createUserNode(user);

  // Create preferences in MongoDB
  await mongo.collection('user_preferences').insertOne({
    _id: user.id,
    theme: 'light',
    notifications: {}
  });
});
```

### Pattern 5: Aggregate from Multiple Sources

```typescript
async function getUserDashboard(userId) {
  // PostgreSQL - Account info
  const account = await supabase
    .from('users')
    .select('*')
    .eq('id', userId)
    .single();

  // Neo4j - Social metrics
  const social = await neo4j.run(`
    MATCH (u:User {id: $userId})
    OPTIONAL MATCH (u)-[:FOLLOWS]->(following)
    OPTIONAL MATCH (follower)-[:FOLLOWS]->(u)
    RETURN
      count(DISTINCT following) as followingCount,
      count(DISTINCT follower) as followerCount
  `, { userId });

  // MongoDB - Recent content
  const posts = await mongo
    .collection('posts')
    .find({ authorId: userId })
    .sort({ createdAt: -1 })
    .limit(5)
    .toArray();

  return {
    account: account.data,
    social: social.records[0],
    recentPosts: posts
  };
}
```

## Schema Design Patterns

### Relational Schema (Supabase)

**Normalized Structure**:

```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Clear foreign keys
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  total DECIMAL(10,2)
);
```

### Graph Schema (Neo4j)

**Labels and Relationships**:

```cypher
// Node labels
(:User)
(:Organization)
(:Course)

// Typed relationships
(:User)-[:MEMBER_OF {role}]->(:Organization)
(:User)-[:FOLLOWS {since}]->(:User)
(:Course)-[:REQUIRES]->(:Course)
```

### Document Schema (MongoDB)

**Flexible Structure**:

```javascript
// Embedded approach (1-to-few)
{
  _id: ObjectId("..."),
  userId: "user-123",
  title: "My Blog Post",
  content: "...",
  comments: [  // Embedded
    {
      id: "comment-1",
      userId: "user-456",
      text: "Great post!",
      createdAt: ISODate("2024-01-15")
    }
  ],
  tags: ["tutorial", "javascript"],
  metadata: {
    views: 150,
    likes: 23
  }
}

// Reference approach (1-to-many)
{
  _id: ObjectId("..."),
  title: "E-commerce Order",
  userId: "user-123",  // Reference
  items: [
    { productId: "prod-789", quantity: 2 },  // Reference
    { productId: "prod-456", quantity: 1 }
  ],
  total: 149.99
}
```

## Query Optimization

### PostgreSQL Optimization

**Indexes**:

```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at DESC);
```

### Neo4j Optimization

**Constraints and Indexes**:

```cypher
CREATE CONSTRAINT user_id_unique
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE INDEX user_email
FOR (u:User) ON (u.email);
```

### MongoDB Optimization

**Indexes**:

```javascript
// Single field
db.posts.createIndex({ authorId: 1 });

// Compound index
db.posts.createIndex({ authorId: 1, createdAt: -1 });

// Text search
db.posts.createIndex({ title: "text", content: "text" });

// Embedded field
db.posts.createIndex({ "metadata.views": -1 });
```

**Query Patterns**:

```javascript
// Efficient: Uses index
db.posts.find({ authorId: userId }).sort({ createdAt: -1 });

// Inefficient: Full collection scan
db.posts.find({ "comments.text": /keyword/ });

// Better: Index comment text separately or use aggregation
```
