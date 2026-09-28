# Integration with PostgreSQL/Supabase

Detail for `clod-stack-cypher`.

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

## Data Synchronisation

**Event-driven sync**: subscribe with `supabase.channel(...).on('postgres_changes', {...}, callback).subscribe()`; full worked example (Supabase → Neo4j + MongoDB) in `clod-role-data_ontologist/integration-and-schema.md` Pattern 4. The Neo4j write here is the same shape:
```typescript
async (payload) => {
  await neo4j.run(`
    MERGE (u:User {id: $id})
    SET u.name = $name, u.email = $email
  `, payload.new);
}
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
