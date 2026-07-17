# Anti-Patterns, Migration Strategies, and Portfolio Evidence

Detail for `Data Ontologist`.

## Anti-Patterns

### Don't: Use Document DB for Transactions

```javascript
// ✗ Bad: Complex multi-document transaction in MongoDB
session.startTransaction();
await orders.insertOne({ userId, total });
await inventory.updateOne({ productId }, { $inc: { stock: -1 } });
await session.commitTransaction();
```

**Why**: PostgreSQL designed for this, ACID guarantees stronger.

### Don't: Embed Everything

```javascript
// ✗ Bad: Embedding user data in every post
{
  title: "My Post",
  author: {
    id: "user-123",
    name: "Alice",
    email: "alice@example.com",
    bio: "...",
    avatar: "..."  // Duplicated everywhere!
  }
}
```

**Better**: Store author ID, fetch user data separately.

### Don't: Use Graph for Simple Lookups

```cypher
// ✗ Bad: Using Neo4j for key-value lookup
MATCH (u:User {email: $email})
RETURN u;
```

**Why**: PostgreSQL or MongoDB faster for indexed lookups.

### Don't: Force Relational Patterns into Documents

```javascript
// ✗ Bad: Normalized MongoDB (defeats the purpose)
// users collection
{ _id: "user-123", name: "Alice" }

// posts collection
{ _id: "post-456", authorId: "user-123", title: "..." }

// comments collection
{ _id: "comment-789", postId: "post-456", text: "..." }
```

**Why**: If normalizing this much, use PostgreSQL instead.

## Migration Strategies

### Starting Point

**Begin with PostgreSQL**:
- Authentication
- Core transactional data
- Well-understood entities

**Add MongoDB When**:
- Content becomes varied
- Schema evolution frequent
- Nested data structures emerge

**Add Neo4j When**:
- Relationships become complex
- Traversal queries needed
- Recommendations required

### Data Migration Examples

**PostgreSQL → MongoDB**:

```typescript
// Export from PG
const posts = await supabase.from('posts').select('*');

// Transform and insert to MongoDB
await mongo.collection('posts').insertMany(
  posts.map(post => ({
    _id: post.id,
    ...post,
    metadata: {
      views: post.view_count,
      likes: post.like_count
    }
  }))
);
```

**MongoDB → Neo4j** (relationships):

```typescript
// Get follows from MongoDB
const follows = await mongo.collection('follows').find().toArray();

// Create relationships in Neo4j
await neo4j.run(`
  UNWIND $follows AS follow
  MATCH (follower:User {id: follow.followerId})
  MATCH (followed:User {id: follow.followedId})
  CREATE (follower)-[:FOLLOWS {since: follow.createdAt}]->(followed)
`, { follows });
```

## Portfolio Evidence

**KSBs Demonstrated**:
- **K2**: All Stages of Software Development Lifecycle (architecture decisions)
- **K3**: Roles and Responsibilities (database selection justification)
- **S1**: Analyse Requirements (choosing right tool for problem)
- **S6**: Design and Implement Database Systems (polyglot approach)

**How to Document**:
- Architecture Decision Records (ADRs) explaining database choices
- Diagrams showing which data lives where
- Performance comparisons (before/after changes)
- Migration scripts and sync strategies
- Trade-off analysis documentation
