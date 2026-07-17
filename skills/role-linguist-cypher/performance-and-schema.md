# Performance Optimization and Schema Design

Detail for `Cypher Linguist`.

## Indexes and Constraints

**Unique constraints** (automatically create index):
```cypher
// Unique user ID
CREATE CONSTRAINT user_id_unique
FOR (u:User) REQUIRE u.id IS UNIQUE;

// Unique email
CREATE CONSTRAINT user_email_unique
FOR (u:User) REQUIRE u.email IS UNIQUE;
```

**Regular indexes**:
```cypher
// Index on property
CREATE INDEX user_name_index
FOR (u:User) ON (u.name);

// Composite index
CREATE INDEX user_location_index
FOR (u:User) ON (u.city, u.country);

// Full-text search
CREATE FULLTEXT INDEX user_search_index
FOR (u:User) ON EACH [u.name, u.bio, u.email];
```

**Use indexes**:
```cypher
// Full-text search
CALL db.index.fulltext.queryNodes('user_search_index', 'Alice')
YIELD node, score
RETURN node, score;
```

## Query Optimization

**Use PROFILE to analyze**:
```cypher
PROFILE
MATCH (u:User {id: $userId})-[:FOLLOWS*1..3]->(friend)
RETURN friend;
```

**Optimization tips**:

**1. Start with most specific nodes**:
```cypher
// ✗ Bad: Starts with all users
MATCH (u:User)-[:FOLLOWS]->(friend:User {id: $friendId})
RETURN u;

// ✓ Good: Starts with specific user
MATCH (u:User)-[:FOLLOWS]->(friend:User)
WHERE friend.id = $friendId
RETURN u;
```

**2. Limit relationship depth**:
```cypher
// ✗ Bad: Unbounded traversal
MATCH (u:User {id: $userId})-[:FOLLOWS*]->(friend)
RETURN friend;

// ✓ Good: Bounded traversal
MATCH (u:User {id: $userId})-[:FOLLOWS*1..3]->(friend)
RETURN friend;
```

**3. Use LIMIT early**:
```cypher
// ✓ Good: Limit before expensive operations
MATCH (u:User)
RETURN u
ORDER BY u.createdAt DESC
LIMIT 10;
```

**4. Avoid Cartesian products**:
```cypher
// ✗ Bad: Creates cartesian product
MATCH (a:User), (b:User)
WHERE a.city = b.city
RETURN a, b;

// ✓ Good: Connect via relationship or property
MATCH (a:User)-[:LIVES_IN]->(city:City)<-[:LIVES_IN]-(b:User)
RETURN a, b;
```

## Batch Operations

**Bulk create**:
```cypher
// Create many nodes efficiently
UNWIND $users AS userData
MERGE (u:User {id: userData.id})
SET u.name = userData.name, u.email = userData.email;

// Create many relationships
UNWIND $follows AS follow
MATCH (a:User {id: follow.followerId})
MATCH (b:User {id: follow.followedId})
MERGE (a)-[:FOLLOWS {since: follow.since}]->(b);
```

**Use APOC for batching**:
```cypher
// Process in batches of 1000
CALL apoc.periodic.iterate(
  "MATCH (u:User) RETURN u",
  "SET u.processed = true",
  {batchSize: 1000}
);
```

## Schema Design

### Modeling Guidelines

**Nodes**: Represent entities
```cypher
(:User)
(:Post)
(:Comment)
(:Tag)
```

**Relationships**: Represent connections
```cypher
(:User)-[:POSTED]->(:Post)
(:User)-[:COMMENTED]->(:Comment)
(:Comment)-[:ON]->(:Post)
(:Post)-[:TAGGED]->(:Tag)
```

**Properties**: Store attributes
```cypher
// On nodes
User {id, name, email, createdAt}

// On relationships
FOLLOWS {since, strength}
LIKED {rating, timestamp}
```

### When to Use Relationships vs Properties

**Use relationship when**:
- Connection between entities
- Need to query traversals
- Connection has properties
- Many-to-many relationship

```cypher
// ✓ Good: Relationship
(user:User)-[:LIKED {rating: 5}]->(post:Post)
```

**Use property when**:
- Simple value
- Doesn't need traversal
- One-to-one relationship
- Rarely queried independently

```cypher
// ✓ Good: Property
(:User {email: 'alice@example.com'})
```

### Multiple Labels

**Use multiple labels for**:
- Shared behaviour
- Polymorphism
- Categorization

```cypher
// User can be both Person and Developer
CREATE (p:Person:Developer {name: 'Alice'})

// Query specific type
MATCH (d:Developer)
RETURN d;

// Query any person
MATCH (p:Person)
RETURN p;
```
