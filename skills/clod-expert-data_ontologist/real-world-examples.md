# Real-World Examples

Detail for `Data Ontologist` — four worked examples of polyglot persistence splits.

## Example 1: Social Application (WorkWise)

**Supabase (PostgreSQL)**:
- User authentication and profiles
- Organization/company records
- Subscription billing
- Audit logs

**Neo4j**:
- Social connections (followers, following)
- Content interactions (likes, shares)
- Recommendation engine
- Activity feed generation

**MongoDB**:
- User-generated posts/content
- Comments and nested discussions
- Rich media metadata
- Activity logs with flexible structure

**Why All Three?**:
- Auth needs ACID (Supabase)
- Social graph needs traversal (Neo4j)
- Posts need flexible schema (MongoDB)
- User lookups fast in PG
- "People you may know" fast in Neo4j
- Content queries flexible in MongoDB

## Example 2: Learning Platform (Rhea)

**Supabase (PostgreSQL)**:
- User accounts and enrollment
- Payment transactions
- Progress tracking (completion %)
- Subscriptions

**Neo4j**:
- Course prerequisites and dependencies
- Learning path recommendations
- Skill relationships
- "What should I learn next?" queries

**MongoDB**:
- Course content (lessons, modules)
- Rich lesson materials (videos, exercises, notes)
- Student submissions and feedback
- Curriculum templates

**Why All Three?**:
- Enrollment is transactional (Supabase)
- Prerequisites are graph traversal (Neo4j)
- Course content is nested documents (MongoDB)
- Payment requires ACID (PG)
- Learning paths require traversal (Neo4j)
- Lessons have varying structures (MongoDB)

## Example 3: E-commerce Platform

**Supabase (PostgreSQL)**:
- User accounts
- Order transactions
- Inventory counts
- Payment records

**Neo4j**:
- Product recommendations
- "Customers who bought X also bought Y"
- Similar products

**MongoDB**:
- Product catalog with varying attributes
- User reviews and ratings
- Shopping cart state
- Product images and metadata

**Why All Three?**:
- Orders need transactions (Supabase)
- Recommendations need graph (Neo4j)
- Products have varying specs (MongoDB)
- Inventory atomic updates (PG)
- "Similar items" fast in graph
- Product attributes flexible in documents

## Example 4: Content Platform (CMS)

**Supabase (PostgreSQL)**:
- User authentication
- User roles and permissions
- Subscription management

**MongoDB**:
- Articles, blog posts, pages
- Media library
- Draft versions
- Comments and nested discussions
- SEO metadata

**Neo4j** (Optional):
- Content relationships
- Tag networks
- Content recommendations

**Why This Mix?**:
- Users need auth (Supabase)
- Content varies by type (MongoDB)
- Articles have nested comments (MongoDB)
- Permissions are relational (PG)
- Tags can be graphed (Neo4j optional)
