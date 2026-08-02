# Database Schema & Data Models

Documentation of database schema, models, relationships, constraints, indexes, and performance optimization techniques in the Marks Management System.

---

## 🗃️ Entity Relationship Overview

```
+-----------+        +------------+        +-----------+
|   Admin   |        |  Teacher   |        |  Student  |
+-----------+        +------------+        +-----------+
                          |                      |
                          | 1:N                  | 1:N
                          v                      v
                     +------------+        +-----------+
                     |  Subject   |        |   Mark    |
                     +------------+        +-----------+
                          |                      |
                          | 1:N                  |
                          v                      |
                     +------------+              |
                     | Submission |<-------------+
                     +------------+
```

---

## 📋 Table Schemas (Phase 10 Additions)

### 1. `SystemSetting`
- **Purpose**: Key-value store for global settings (Institution Name, export naming templates, email settings).
- **Fields**:
  - `id` (Integer, Primary Key)
  - `key` (String(50), Unique, Not Null)
  - `value` (Text, Nullable)

### 2. `SystemActivityLog`
- **Purpose**: Application audit logs tracking user activity.
- **Fields**:
  - `id` (Integer, Primary Key)
  - `username` (String(100), Indexed, Not Null)
  - `action` (String(200), Indexed, Not Null)
  - `timestamp` (DateTime, Indexed, Not Null, Default: CURRENT_TIMESTAMP)
  - `status` (String(50), Not Null, Default: `'SUCCESS'`)

---

## ⚡ Database Performance & Optimization

To ensure fast search queries and efficient dynamic updates, several custom database indexes are defined.

### Indexed Columns
- `Student.name` (index=True): Speeds up partial searches of student names.
- `Student.batch` (index=True): Accelerates cohort filtering and tabulation register generation.
- `Student.semester` (index=True): Speeds up semester-specific reports.
- `Teacher.name` (index=True): Optimization for faculty global search.
- `Subject.name` (index=True): Optimization for dynamic course search.
- `SystemActivityLog` indexes: `username`, `action`, and `timestamp` fields are indexed to enable rapid lookup of audit trails.
