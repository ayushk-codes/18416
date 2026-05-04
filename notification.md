# Stage 1

## REST API Design — Campus Notification Platform

### Core Actions
The notification platform needs to support fetching notifications, marking them as read, and receiving real-time updates when a student is logged in.

---

### Endpoints

#### GET /notifications
Fetch all notifications for the logged-in student.

**Headers**
```
Authorization: Bearer <token>
```

**Response 200**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "type": "Placement",
      "message": "Infosys drive on 10th May",
      "isRead": false,
      "createdAt": "2026-05-04T10:00:00Z"
    }
  ]
}
```

---

#### GET /notifications/:id
Fetch a single notification by ID.

**Headers**
```
Authorization: Bearer <token>
```

**Response 200**
```json
{
  "id": "uuid",
  "type": "Result",
  "message": "Mid-sem results are out",
  "isRead": false,
  "createdAt": "2026-05-04T10:00:00Z"
}
```

**Response 404**
```json
{ "error": "Notification not found" }
```

---

#### PATCH /notifications/:id/read
Mark a single notification as read.

**Headers**
```
Authorization: Bearer <token>
```

**Response 200**
```json
{ "message": "Notification marked as read" }
```

---

#### PATCH /notifications/read-all
Mark all notifications as read for the logged-in student.

**Headers**
```
Authorization: Bearer <token>
```

**Response 200**
```json
{ "message": "All notifications marked as read" }
```

---

#### GET /notifications/unread/count
Get count of unread notifications — used for the badge on the bell icon.

**Headers**
```
Authorization: Bearer <token>
```

**Response 200**
```json
{ "unreadCount": 5 }
```

---

#### POST /notifications
Create a new notification — used internally by the system or admin.

**Headers**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request Body**
```json
{
  "studentId": "uuid",
  "type": "Placement",
  "message": "Google drive scheduled for 15th May"
}
```

**Response 201**
```json
{
  "id": "uuid",
  "message": "Notification created successfully"
}
```

---

### Real-Time Notifications

Use **WebSockets** for real-time delivery. When a student logs in, they open a persistent WebSocket connection. When a new notification is created for that student, the server pushes it instantly without the client needing to poll.

**Connection**
```
ws://your-server/ws/notifications?token=<jwt>
```

**Server pushes this shape when a new notification arrives**
```json
{
  "event": "new_notification",
  "data": {
    "id": "uuid",
    "type": "Event",
    "message": "Tech fest tomorrow at 5pm",
    "createdAt": "2026-05-04T12:00:00Z"
  }
}
```

As a simpler alternative, **Server-Sent Events (SSE)** can be used if only one-way push is needed, which is lighter than WebSockets.

---

# Stage 2

## Database Design

### Choice: PostgreSQL

PostgreSQL is the right fit here because the data is structured and relational — students have notifications, notifications have types and states. It gives us ACID guarantees, which means we won't lose or corrupt notification records during crashes or concurrent writes. It also supports strong querying with indexes, which matters when data grows.

---

### Schema

```sql
CREATE TABLE students (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TYPE notification_type AS ENUM ('Placement', 'Result', 'Event');

CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  type notification_type NOT NULL,
  message TEXT NOT NULL,
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

### Problems as Data Volume Increases

As the table grows to millions of rows, a few things break down. Queries that filter by student_id do a full sequential scan if there are no indexes, which becomes painfully slow. The table size itself grows large enough that even indexed lookups start competing for memory. Writes slow down because every insert has to update indexes. Backups and migrations take longer.

**Solutions**
- Add a composite index on `(student_id, is_read, created_at)` so the most common query — fetch unread notifications for a student, newest first — is fast.
- Use table partitioning by `created_at` (monthly partitions) so old data is in separate partitions and queries on recent data don't scan old rows.
- Archive notifications older than 6 months to a cold storage table.
- Use a read replica for all SELECT queries to offload the primary DB.

---

### Queries Based on Stage 1 APIs

**Fetch all notifications for a student**
```sql
SELECT id, type, message, is_read, created_at
FROM notifications
WHERE student_id = $1
ORDER BY created_at DESC;
```

**Fetch single notification**
```sql
SELECT id, type, message, is_read, created_at
FROM notifications
WHERE id = $1 AND student_id = $2;
```

**Mark one as read**
```sql
UPDATE notifications
SET is_read = true
WHERE id = $1 AND student_id = $2;
```

**Mark all as read**
```sql
UPDATE notifications
SET is_read = true
WHERE student_id = $1 AND is_read = false;
```

**Unread count**
```sql
SELECT COUNT(*) FROM notifications
WHERE student_id = $1 AND is_read = false;
```

---

# Stage 3

## Query Analysis and Optimization

### The Original Query
```sql
SELECT * FROM notifications
WHERE studentID = 1042 AND isRead = false
ORDER BY createdAt DESC;
```

### Why Is It Slow?

With 50,000 students and 5,000,000 notifications, this query does a full table scan — it reads every row in the table and then filters. There is no index, so the DB has no shortcut. `SELECT *` also fetches every column, including ones the caller probably doesn't need, which increases I/O and memory usage unnecessarily.

### What to Change

Add a composite index that covers the exact filter and sort pattern this query uses:

```sql
CREATE INDEX idx_notifications_student_unread
ON notifications (student_id, is_read, created_at DESC);
```

This tells the DB to jump directly to rows for that student where is_read is false, already sorted — no scan, no sort step.

Also replace `SELECT *` with only the columns you actually need:

```sql
SELECT id, type, message, created_at
FROM notifications
WHERE student_id = 1042 AND is_read = false
ORDER BY created_at DESC;
```

### Likely Computation Cost After Fix

Before the index: O(n) full scan across 5M rows.
After the index: O(log n) to find the starting point, then O(k) where k is only the matching rows for that student. For a student with 100 unread notifications this is essentially instant.

### Is Indexing Every Column Good Advice?

No. Indexing every column is actively harmful. Every index takes up disk space and has to be updated on every INSERT and UPDATE. If you have 10 columns and 10 indexes, every time a new notification is saved the DB has to write to 10 index structures. On a high-write system with 50,000 students getting notifications frequently, this degrades write performance significantly. You should only index columns that appear in WHERE, ORDER BY, or JOIN clauses in your most frequent queries.

### Query: Students Who Got a Placement Notification in the Last 7 Days

```sql
SELECT DISTINCT student_id
FROM notifications
WHERE type = 'Placement'
AND created_at >= NOW() - INTERVAL '7 days';
```

---

# Stage 4

## Caching Strategy

### Problem
Notifications are fetched on every page load for every student. With 50,000 students, this hammers the DB with repeated reads for data that doesn't change every second.

### Solution: Redis Cache

Cache each student's notifications in Redis with a short TTL.

**Strategy**
- On the first fetch for a student, query the DB and store the result in Redis under the key `notifications:<student_id>` with a TTL of 60 seconds.
- On subsequent requests within that 60 seconds, serve from Redis — no DB hit.
- When a new notification is created or one is marked as read for that student, delete their cache key so the next request gets fresh data from the DB.

```python
cache_key = "notifications:" + str(student_id)

cached = redis.get(cache_key)
if cached:
    return json.loads(cached)

data = db.query("SELECT ... FROM notifications WHERE student_id = $1", student_id)
redis.setex(cache_key, 60, json.dumps(data))
return data
```

**Tradeoffs**
- A 60s TTL means a student might see slightly stale data for up to a minute if cache invalidation is missed. For a notification system this is usually acceptable.
- Cache invalidation on write keeps things fresh but adds a Redis write on every notification event.
- If Redis goes down, the system falls back to the DB automatically — it degrades gracefully.

**Other strategies considered**
- Pagination: only fetch 20 notifications at a time instead of all 5M. Reduces payload size significantly.
- Unread count endpoint separately cached: the badge count is fetched most frequently, cache it independently so marking one as read only invalidates the count, not the full list.

---

# Stage 5

## Fixing notify_all for 50,000 Students

### The Problem With the Pseudocode

```
function notify_all(student_ids: array, message: string):
    for student_id in student_ids:
        send_email(student_id, message)
        save_to_db(student_id, message)
        push_to_app(student_id, message)
```

This runs sequentially. For 50,000 students, if each iteration takes even 100ms (network call to email API + DB write + push), that is 5,000 seconds — over an hour. The HR clicks "Notify All" and waits forever. If it crashes halfway through, there is no retry. Some students get notified, others don't.

### Fix: Message Queue with Async Workers

Push each student_id into a message queue (Redis Queue, Celery, RabbitMQ). Multiple worker processes consume from the queue in parallel and handle email + DB + push for each student independently.

```python
def notify_all(student_ids, message):
    for student_id in student_ids:
        queue.enqueue(notify_single_student, student_id, message)

def notify_single_student(student_id, message):
    send_email(student_id, message)
    save_to_db(student_id, message)
    push_to_app(student_id, message)
```

With 20 workers running in parallel, 50,000 jobs complete roughly 20x faster. Each job is independent — if one fails, only that student's notification is retried, not all 50,000. The HR gets an immediate response ("Notifications queued") and the system processes in the background.

---

# Stage 6

## Priority Inbox

### Approach

Notifications are ranked by a combination of type weight and recency. Placement is the most important, so it gets the highest weight. Result is second. Event is lowest. Within the same weight, newer notifications rank higher.

**Weights:** Placement = 3, Result = 2, Event = 1

To balance weight and recency fairly, each notification gets a score:

```
score = weight * 1000000 + (timestamp as unix seconds)
```

The large multiplier ensures that a Placement notification always outranks a Result notification regardless of time, but two Placements are sorted by recency between themselves.

The top 10 by score are returned.

As new notifications come in, we maintain a min-heap of size 10. Each new notification is compared against the smallest item in the heap. If it scores higher, it replaces it. This keeps the top 10 updated in O(log 10) = O(1) effectively, making it efficient even as thousands of notifications stream in.

See `stage6/priority_inbox.py` for the working implementation.