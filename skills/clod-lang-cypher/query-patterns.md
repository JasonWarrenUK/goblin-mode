# Common Query Patterns

Detail for `Cypher Linguist` — social graph, hierarchy, recommendation, path-finding, and access-control queries.

## Social Graph Patterns

**Followers/Following**:
```cypher
// Get user's followers
MATCH (follower:User)-[:FOLLOWS]->(u:User {id: $userId})
RETURN follower;

// Get who user follows
MATCH (u:User {id: $userId})-[:FOLLOWS]->(following)
RETURN following;

// Mutual follows (friends)
MATCH (a:User {id: $userId})-[:FOLLOWS]->(b:User)
MATCH (b)-[:FOLLOWS]->(a)
RETURN b AS friend;

// Follow suggestions (friends of friends, not already following)
MATCH (u:User {id: $userId})-[:FOLLOWS]->()-[:FOLLOWS]->(suggestion)
WHERE NOT (u)-[:FOLLOWS]->(suggestion)
  AND u <> suggestion
RETURN DISTINCT suggestion
LIMIT 10;
```

**Blocking**:
```cypher
// Create block relationship
MATCH (a:User {id: $userId})
MATCH (b:User {id: $blockUserId})
MERGE (a)-[:BLOCKED]->(b);

// Get all users except blocked
MATCH (u:User)
WHERE NOT (:User {id: $currentUserId})-[:BLOCKED]->(u)
  AND NOT (u)-[:BLOCKED]->(:User {id: $currentUserId})
RETURN u;
```

## Hierarchy Patterns

**Organizational structure**:
```cypher
// Find all reports (direct and indirect)
MATCH (manager:Person {id: $managerId})-[:MANAGES*]->(report:Person)
RETURN report;

// Find direct reports only
MATCH (manager:Person {id: $managerId})-[:MANAGES]->(report:Person)
RETURN report;

// Find manager chain up to CEO
MATCH path = (person:Person {id: $personId})-[:REPORTS_TO*]->(ceo:Person)
WHERE NOT (ceo)-[:REPORTS_TO]->()
RETURN nodes(path);

// Find all people in same department
MATCH (person:Person {id: $personId})-[:MEMBER_OF]->(dept:Department)
MATCH (colleague:Person)-[:MEMBER_OF]->(dept)
WHERE person <> colleague
RETURN colleague;
```

**Category hierarchies**:
```cypher
// Find all subcategories
MATCH (parent:Category {id: $categoryId})-[:PARENT_OF*]->(child:Category)
RETURN child;

// Find path to root category
MATCH path = (cat:Category {id: $categoryId})-[:CHILD_OF*]->(root:Category)
WHERE NOT (root)-[:CHILD_OF]->()
RETURN nodes(path);
```

## Recommendation Patterns

**Collaborative filtering**:
```cypher
// Users who liked similar items
MATCH (u:User {id: $userId})-[:LIKED]->(item:Item)
MATCH (item)<-[:LIKED]-(other:User)
MATCH (other)-[:LIKED]->(recommendation:Item)
WHERE NOT (u)-[:LIKED]->(recommendation)
RETURN recommendation, count(*) AS score
ORDER BY score DESC
LIMIT 10;

// Weighted recommendations
MATCH (u:User {id: $userId})-[r1:LIKED]->(item:Item)
MATCH (item)<-[r2:LIKED]-(other:User)
MATCH (other)-[r3:LIKED]->(recommendation:Item)
WHERE NOT (u)-[:LIKED]->(recommendation)
WITH recommendation,
     sum(r1.weight * r2.weight * r3.weight) AS score
RETURN recommendation
ORDER BY score DESC
LIMIT 10;
```

**Content-based filtering**:
```cypher
// Items similar to liked items
MATCH (u:User {id: $userId})-[:LIKED]->(item:Item)
MATCH (item)-[:HAS_TAG]->(tag:Tag)
MATCH (tag)<-[:HAS_TAG]-(similar:Item)
WHERE NOT (u)-[:LIKED]->(similar)
  AND item <> similar
RETURN similar, count(tag) AS commonTags
ORDER BY commonTags DESC
LIMIT 10;
```

## Path Finding

**Shortest path**:
```cypher
// Shortest path between two users
MATCH path = shortestPath(
  (a:User {id: $userId1})-[:FOLLOWS*]-(b:User {id: $userId2})
)
RETURN path, length(path);

// All shortest paths
MATCH path = allShortestPaths(
  (a:User {id: $userId1})-[:FOLLOWS*]-(b:User {id: $userId2})
)
RETURN path;
```

**Dijkstra's algorithm** (weighted paths):
```cypher
// Find cheapest route
CALL gds.shortestPath.dijkstra.stream('graph', {
  sourceNode: $startNodeId,
  targetNode: $endNodeId,
  relationshipWeightProperty: 'cost'
})
YIELD path, totalCost
RETURN path, totalCost;
```

## Access Control

**Permission hierarchies**:
```cypher
// Check if user has permission
MATCH (u:User {id: $userId})-[:HAS_ROLE]->(role:Role)
MATCH (role)-[:HAS_PERMISSION*0..]->(permission:Permission {name: $permissionName})
RETURN count(permission) > 0 AS hasPermission;

// Get all user permissions (including inherited)
MATCH (u:User {id: $userId})-[:HAS_ROLE]->(role:Role)
MATCH (role)-[:HAS_PERMISSION*0..]->(permission:Permission)
RETURN DISTINCT permission;
```
