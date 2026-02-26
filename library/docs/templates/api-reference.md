# API Reference

> **Last Updated**: YYYY-MM-DD  
> **Base URL**: `https://api.example.com`  
> **Version**: v1

---

## Authentication

### Authentication Method

[Describe how to authenticate - API keys, JWT, OAuth, etc.]

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.example.com/endpoint
```

### Getting Credentials

[How to obtain API keys or tokens]

---

## Endpoints

### Resource 1

#### `GET /api/resource1`

**Description**: [What this endpoint does]

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `param1` | string | Yes | [Description] | - |
| `param2` | number | No | [Description] | `10` |
| `filter` | string | No | [Description] | - |

**Example Request**:
```bash
curl -X GET "https://api.example.com/api/resource1?param1=value" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": [
    {
      "id": "123",
      "field1": "value1",
      "field2": "value2"
    }
  ],
  "pagination": {
    "total": 100,
    "page": 1,
    "limit": 10
  }
}
```

**Error Response** (400 Bad Request):
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Parameter 'param1' is required",
    "details": {}
  }
}
```

---

#### `GET /api/resource1/:id`

**Description**: [What this endpoint does]

**Authentication**: Required

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | [Description] |

**Example Request**:
```bash
curl -X GET "https://api.example.com/api/resource1/123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "123",
    "field1": "value1",
    "field2": "value2",
    "createdAt": "2026-01-08T10:00:00Z",
    "updatedAt": "2026-01-08T10:00:00Z"
  }
}
```

**Error Response** (404 Not Found):
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource with id '123' not found"
  }
}
```

---

#### `POST /api/resource1`

**Description**: [What this endpoint does]

**Authentication**: Required

**Request Body**:
```json
{
  "field1": "string",
  "field2": "string",
  "field3": 123
}
```

**Field Descriptions**:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `field1` | string | Yes | [Description] | Max 255 chars |
| `field2` | string | No | [Description] | Min 3 chars |
| `field3` | number | Yes | [Description] | Must be > 0 |

**Example Request**:
```bash
curl -X POST "https://api.example.com/api/resource1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "field1": "value1",
    "field2": "value2",
    "field3": 123
  }'
```

**Success Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "id": "456",
    "field1": "value1",
    "field2": "value2",
    "field3": 123,
    "createdAt": "2026-01-08T10:00:00Z"
  }
}
```

**Error Response** (422 Unprocessable Entity):
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "field1": ["Field is required"],
      "field3": ["Must be greater than 0"]
    }
  }
}
```

---

#### `PATCH /api/resource1/:id`

**Description**: [What this endpoint does]

**Authentication**: Required

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | [Description] |

**Request Body** (partial update):
```json
{
  "field1": "new value"
}
```

**Example Request**:
```bash
curl -X PATCH "https://api.example.com/api/resource1/123" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "field1": "new value"
  }'
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "123",
    "field1": "new value",
    "field2": "value2",
    "updatedAt": "2026-01-08T11:00:00Z"
  }
}
```

---

#### `DELETE /api/resource1/:id`

**Description**: [What this endpoint does]

**Authentication**: Required

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | [Description] |

**Example Request**:
```bash
curl -X DELETE "https://api.example.com/api/resource1/123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Resource deleted successfully"
}
```

**Error Response** (404 Not Found):
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource with id '123' not found"
  }
}
```

---

### Resource 2

[Follow same pattern for additional resources]

---

## Data Models

### Resource1

```typescript
interface Resource1 {
  id: string;
  field1: string;
  field2: string;
  field3: number;
  createdAt: string;  // ISO 8601 timestamp
  updatedAt: string;  // ISO 8601 timestamp
}
```

### Resource2

```typescript
interface Resource2 {
  id: string;
  // ... fields
}
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| `INVALID_PARAMETER` | 400 | Request parameter is invalid |
| `UNAUTHORIZED` | 401 | Authentication credentials missing or invalid |
| `FORBIDDEN` | 403 | User lacks permission for this resource |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist |
| `VALIDATION_ERROR` | 422 | Request body failed validation |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

---

## Rate Limiting

[Describe rate limiting policy]

**Limits**:
- Authenticated users: [X requests per Y time period]
- Unauthenticated users: [X requests per Y time period]

**Headers**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1641024000
```

---

## Pagination

[How pagination works in this API]

**Query Parameters**:
- `page` (number): Page number (default: 1)
- `limit` (number): Items per page (default: 10, max: 100)

**Response Structure**:
```json
{
  "data": [...],
  "pagination": {
    "total": 150,
    "page": 1,
    "limit": 10,
    "pages": 15
  }
}
```

---

## Filtering & Sorting

### Filtering

[How to filter results]

**Example**:
```
GET /api/resource1?filter[field1]=value&filter[field2]=value
```

### Sorting

[How to sort results]

**Example**:
```
GET /api/resource1?sort=field1:asc,field2:desc
```

---

## Webhooks

[If API supports webhooks]

### Webhook Events

| Event | Description |
|-------|-------------|
| `resource1.created` | Triggered when resource1 is created |
| `resource1.updated` | Triggered when resource1 is updated |
| `resource1.deleted` | Triggered when resource1 is deleted |

### Webhook Payload

```json
{
  "event": "resource1.created",
  "timestamp": "2026-01-08T10:00:00Z",
  "data": {
    // Resource data
  }
}
```

---

## SDK & Libraries

[Links to official SDKs or client libraries]

- **TypeScript/JavaScript**: [Link]
- **Python**: [Link]
- **Go**: [Link]

---

## Changelog

### v1.1.0 (YYYY-MM-DD)
- Added [new endpoint]
- Changed [field behavior]
- Deprecated [old endpoint]

### v1.0.0 (YYYY-MM-DD)
- Initial API release
