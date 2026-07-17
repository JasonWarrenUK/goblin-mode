# Integration with PostgreSQL/Supabase and Portfolio Evidence

Detail for `Cypher Linguist`.

## Shared Primary Keys

**Use same UUIDs**:
```typescript
// Create in PostgreSQL
const { data: user } = await supabase
  .from('users')
  .insert({
    id: userId,
    email: 'alice@example.com',
    name: 'Alice'
  });

// Create in Neo4j
await neo4j.run(`
  CREATE (u:User {
    id: $userId,
    name: $name
  })
`, { userId, name: user.name });
```

## Data Synchronization

**Event-driven sync**:
```typescript
// PostgreSQL trigger → Sync to Neo4j
supabase
  .from('users')
  .on('INSERT', async (payload) => {
    await neo4j.run(`
      MERGE (u:User {id: $id})
      SET u.name = $name, u.email = $email
    `, payload.record);
  })
  .subscribe();
```

**Batch sync**:
```typescript
// Bulk sync from PostgreSQL to Neo4j
const { data: users } = await supabase
  .from('users')
  .select('*');

await neo4j.run(`
  UNWIND $users AS userData
  MERGE (u:User {id: userData.id})
  SET u.name = userData.name,
      u.email = userData.email
`, { users });
```

## Query Patterns

**Hybrid queries**:
```typescript
// Get user from PostgreSQL
const { data: user } = await supabase
  .from('users')
  .select('*')
  .eq('id', userId)
  .single();

// Get social graph from Neo4j
const result = await neo4j.run(`
  MATCH (u:User {id: $userId})
  MATCH (u)-[:FOLLOWS]->(following:User)
  MATCH (follower:User)-[:FOLLOWS]->(u)
  RETURN
    count(DISTINCT following) as followingCount,
    count(DISTINCT follower) as followerCount
`, { userId });

// Combine results
return {
  ...user,
  social: {
    followingCount: result.records[0].get('followingCount'),
    followerCount: result.records[0].get('followerCount')
  }
};
```

## Portfolio Evidence

**KSBs Demonstrated**:
- **S6**: Design and Implement Database Systems (graph modeling)
- **S1**: Analyse Requirements (choosing graph for relationships)
- **S8**: Create Analysis Artefacts (query optimization)

**How to Document**:
- Schema diagrams showing graph structure
- Query examples with performance comparisons
- Explain why graph chosen over relational
- Document traversal patterns
- Show integration with other databases
