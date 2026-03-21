# FundoWallet API Contract

> **Date:** 2026-03-21
> **Status:** Draft — defines what the frontend expects from the backend
> **Base URL:** `https://api.fundowallet.com` (env: `VITE_API_BASE_URL`)

---

## Conventions

### Uniform Response Envelope

**Every** API response uses this structure — no exceptions:

```typescript
interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  meta: PaginationMeta | null;  // present only on paginated endpoints
}
```

#### Success — single resource

```json
{
  "success": true,
  "data": { "id": "std_001", "firstName": "Rudo", "..." : "..." },
  "error": null,
  "meta": null
}
```

#### Success — list (non-paginated)

```json
{
  "success": true,
  "data": [
    { "id": "fee_001", "..." : "..." },
    { "id": "fee_002", "..." : "..." }
  ],
  "error": null,
  "meta": null
}
```

#### Success — paginated list

```json
{
  "success": true,
  "data": [
    { "id": "std_001", "..." : "..." }
  ],
  "error": null,
  "meta": {
    "page": 1,
    "pageSize": 10,
    "totalCount": 156,
    "totalPages": 16
  }
}
```

#### Success — empty action (logout, publish, etc.)

```json
{
  "success": true,
  "data": null,
  "error": null,
  "meta": null
}
```

#### Error

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": {
      "email": ["Email is required"],
      "phone": ["Invalid phone format"]
    }
  },
  "meta": null
}
```

### Error Codes

| HTTP Status | Code | When |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body fails validation |
| 401 | `UNAUTHORIZED` | Missing or expired token |
| 403 | `FORBIDDEN` | Valid token but insufficient permissions |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Duplicate or state conflict |
| 422 | `UNPROCESSABLE_ENTITY` | Valid structure but cannot be processed |
| 500 | `INTERNAL_ERROR` | Server error |

The `details` field is an optional map of field names to validation messages. It is only present for `VALIDATION_ERROR`.

### Authentication

All endpoints except `POST /auth/login` require a Bearer token.

```
Authorization: Bearer <access_token>
```

### Request Headers

| Header | Required | Description |
|---|---|---|
| `Authorization` | Yes (except login) | `Bearer <token>` |
| `Content-Type` | Yes (for POST/PUT/PATCH) | `application/json` |
| `X-Request-ID` | Optional | Client-generated UUID for tracing |

### Standard Pagination

Paginated endpoints accept these query parameters:

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | integer | `1` | Page number (1-based) |
| `pageSize` | integer | `10` | Items per page (max 100) |

### Date Formats

- All timestamps: ISO 8601 with timezone — `2024-01-15T10:00:00Z`
- Date-only fields (dateOfBirth, dueDate): `YYYY-MM-DD` — `2024-01-15`

### ID Format

All resource IDs are server-generated strings (UUID or prefixed like `std_`, `fee_`, `pay_`).

### TypeScript Definitions

```typescript
// These types define the uniform envelope the frontend will parse

interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  meta: PaginationMeta | null;
}

interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[]>;
}

interface PaginationMeta {
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
}
```

---

## 1. Authentication

### `POST /auth/login`

Authenticate a user and receive an access token.

**Permission:** None (public)

**Request:**
```json
{
  "email": "admin@arundelhigh.ac.zw",
  "password": "password123"
}
```

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_001",
      "email": "admin@arundelhigh.ac.zw",
      "phone": "+263 77 234 5678",
      "firstName": "Tendai",
      "lastName": "Moyo",
      "role": "ADMIN",
      "permissions": [
        "school.*", "users.*", "students.*", "fees.*", "invoices.*",
        "payments.*", "reminders.*", "reports.*", "audit.*",
        "roles.*", "permissions.*"
      ],
      "avatarUrl": null,
      "schoolId": "sch_001",
      "isActive": true,
      "createdAt": "2023-01-15T10:00:00Z",
      "lastLoginAt": "2024-01-15T08:30:00Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIs..."
  },
  "error": null,
  "meta": null
}
```

**Error `401`:**
```json
{
  "success": false,
  "data": null,
  "error": { "code": "UNAUTHORIZED", "message": "Invalid email or password" },
  "meta": null
}
```

---

### `GET /auth/me`

Return the currently authenticated user.

**Permission:** Authenticated

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "usr_001",
    "email": "admin@arundelhigh.ac.zw",
    "phone": "+263 77 234 5678",
    "firstName": "Tendai",
    "lastName": "Moyo",
    "role": "ADMIN",
    "permissions": ["school.*", "users.*", "students.*", "..."],
    "avatarUrl": null,
    "schoolId": "sch_001",
    "isActive": true,
    "createdAt": "2023-01-15T10:00:00Z",
    "lastLoginAt": "2024-01-15T08:30:00Z"
  },
  "error": null,
  "meta": null
}
```

---

### `POST /auth/logout`

Invalidate the current access token.

**Permission:** Authenticated

**Request:** Empty body.

**Response `200`:**
```json
{
  "success": true,
  "data": null,
  "error": null,
  "meta": null
}
```

---

## 2. School Profile

### `GET /school`

Get the authenticated user's school profile.

**Permission:** `school.read`

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "sch_001",
    "name": "Arundel High School",
    "address": "23 Doris Johnson Close, Mt Pleasant",
    "city": "Harare",
    "state": "Harare Province",
    "country": "Zimbabwe",
    "phone": "+263 24 2744 567",
    "email": "info@arundelhigh.ac.zw",
    "website": "https://arundelhigh.ac.zw",
    "logoUrl": null,
    "receiptFooter": "Thank you for your payment.",
    "merchantCode": "MRC-ARH-001",
    "billerCode": "BIL-ZW-12345",
    "accountIdentifier": "1234567890",
    "academicTermConfig": {
      "currentTerm": "First Term",
      "currentYear": "2024",
      "terms": [
        { "id": "t1", "name": "First Term", "startDate": "2024-01-09", "endDate": "2024-04-05" },
        { "id": "t2", "name": "Second Term", "startDate": "2024-05-07", "endDate": "2024-08-09" },
        { "id": "t3", "name": "Third Term", "startDate": "2024-09-10", "endDate": "2024-12-06" }
      ]
    },
    "currency": "USD",
    "timezone": "Africa/Harare",
    "createdAt": "2022-08-01T00:00:00Z"
  },
  "error": null,
  "meta": null
}
```

---

### `PATCH /school`

Update the authenticated user's school profile. Partial updates accepted.

**Permission:** `school.update`

**Request (partial):**
```json
{
  "name": "Arundel High School",
  "receiptFooter": "Updated footer text",
  "merchantCode": "MRC-ARH-002"
}
```

**Response `200`:** Same envelope — `data` contains the full updated `School` object.

---

## 3. School Users

### `GET /school/users`

List all users for the authenticated user's school.

**Permission:** `users.read`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "usr_001",
      "email": "admin@arundelhigh.ac.zw",
      "phone": "+263 77 234 5678",
      "firstName": "Tendai",
      "lastName": "Moyo",
      "role": "ADMIN",
      "isActive": true,
      "invitedAt": "2023-01-15T10:00:00Z",
      "lastLoginAt": "2024-01-15T08:30:00Z"
    }
  ],
  "error": null,
  "meta": null
}
```

---

### `POST /school/users`

Invite a new user to the school.

**Permission:** `users.create`

**Request:**
```json
{
  "email": "newuser@arundelhigh.ac.zw",
  "phone": "+263 71 000 0000",
  "firstName": "New",
  "lastName": "User",
  "role": "STAFF"
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `email` | string | Yes | Valid email, unique per school |
| `phone` | string | No | Valid phone format |
| `firstName` | string | Yes | 1-100 chars |
| `lastName` | string | Yes | 1-100 chars |
| `role` | string | Yes | One of: `ADMIN`, `FINANCE`, `STAFF` |

**Response `201`:**
```json
{
  "success": true,
  "data": {
    "id": "usr_005",
    "email": "newuser@arundelhigh.ac.zw",
    "phone": "+263 71 000 0000",
    "firstName": "New",
    "lastName": "User",
    "role": "STAFF",
    "isActive": true,
    "invitedAt": "2024-01-20T10:00:00Z",
    "lastLoginAt": null
  },
  "error": null,
  "meta": null
}
```

**Error `409`:**
```json
{
  "success": false,
  "data": null,
  "error": { "code": "CONFLICT", "message": "A user with this email already exists" },
  "meta": null
}
```

---

### `PATCH /school/users/:id`

Update an existing school user (role, active status).

**Permission:** `users.update`

**Request (partial):**
```json
{
  "role": "FINANCE",
  "isActive": false
}
```

**Response `200`:** Same envelope — `data` contains the updated `SchoolUser` object.

---

## 4. Students

### `GET /students`

List students with filtering, search, and pagination.

**Permission:** `students.read`

**Query Parameters:**

| Param | Type | Description |
|---|---|---|
| `search` | string | Search by firstName, lastName, or studentId (case-insensitive partial match) |
| `grade` | string | Filter by exact grade (e.g. `Form 4`) |
| `status` | string | Filter by status: `ACTIVE`, `INACTIVE`, `GRADUATED`, `TRANSFERRED` |
| `page` | integer | Page number |
| `pageSize` | integer | Items per page |

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "std_001",
      "studentId": "ARH-2024-001",
      "firstName": "Rudo",
      "lastName": "Chikwanha",
      "grade": "Form 4",
      "className": "Science A",
      "status": "ACTIVE",
      "dateOfBirth": "2008-05-12",
      "guardians": [
        {
          "id": "g1",
          "firstName": "Chenai",
          "lastName": "Chikwanha",
          "relationship": "Mother",
          "phone": "+263 77 123 4567",
          "email": "chenai@email.com",
          "isPrimary": true
        }
      ],
      "enrollmentDate": "2020-01-09",
      "balance": 150.00,
      "createdAt": "2020-01-05T10:00:00Z",
      "updatedAt": "2024-01-10T14:30:00Z"
    }
  ],
  "error": null,
  "meta": {
    "page": 1,
    "pageSize": 10,
    "totalCount": 156,
    "totalPages": 16
  }
}
```

---

### `POST /students`

Create a new student with guardians.

**Permission:** `students.create`

**Request:**
```json
{
  "firstName": "Rudo",
  "lastName": "Chikwanha",
  "grade": "Form 4",
  "className": "Science A",
  "dateOfBirth": "2008-05-12",
  "guardians": [
    {
      "firstName": "Chenai",
      "lastName": "Chikwanha",
      "relationship": "Mother",
      "phone": "+263 77 123 4567",
      "email": "chenai@email.com",
      "isPrimary": true
    }
  ]
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `firstName` | string | Yes | 1-100 chars |
| `lastName` | string | Yes | 1-100 chars |
| `grade` | string | Yes | Non-empty |
| `className` | string | Yes | Non-empty |
| `dateOfBirth` | string | No | `YYYY-MM-DD` |
| `guardians` | array | Yes | At least 1; exactly 1 must be `isPrimary: true` |
| `guardians[].firstName` | string | Yes | 1-100 chars |
| `guardians[].lastName` | string | Yes | 1-100 chars |
| `guardians[].relationship` | string | Yes | Non-empty |
| `guardians[].phone` | string | Yes | Valid phone |
| `guardians[].email` | string | No | Valid email |
| `guardians[].isPrimary` | boolean | Yes | |

**Response `201`:** Same envelope — `data` contains the created `Student` (server generates `id`, `studentId`, `enrollmentDate`, `balance`, timestamps).

---

### `PATCH /students/:id`

Update an existing student and replace their guardians.

**Permission:** `students.update`

**Request (partial — only include fields to update):**
```json
{
  "firstName": "Rudo",
  "grade": "Form 5",
  "status": "ACTIVE",
  "guardians": [
    {
      "id": "g1",
      "firstName": "Chenai",
      "lastName": "Chikwanha",
      "relationship": "Mother",
      "phone": "+263 77 123 4567",
      "email": "chenai@email.com",
      "isPrimary": true
    }
  ]
}
```

> When `guardians` is provided, it replaces all existing guardians (full replacement).

**Response `200`:** Same envelope — `data` contains the updated `Student`.

---

### `POST /students/import`

Upload a CSV file for bulk student import.

**Permission:** `students.import`

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | File | Yes | CSV file |

**Response `202`:**
```json
{
  "success": true,
  "data": {
    "id": "imp_001",
    "fileName": "new_students_term1_2024.csv",
    "totalRows": 0,
    "successRows": 0,
    "errorRows": 0,
    "status": "PROCESSING",
    "createdAt": "2024-01-10T09:00:00Z"
  },
  "error": null,
  "meta": null
}
```

---

### `GET /students/imports`

List all import jobs.

**Permission:** `students.import`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "imp_001",
      "fileName": "new_students_term1_2024.csv",
      "totalRows": 45,
      "successRows": 42,
      "errorRows": 3,
      "status": "COMPLETED",
      "errors": [
        { "row": 12, "message": "Invalid date format for date_of_birth" },
        { "row": 23, "message": "Missing required field: guardian_phone" }
      ],
      "createdAt": "2024-01-10T09:00:00Z",
      "completedAt": "2024-01-10T09:02:30Z"
    }
  ],
  "error": null,
  "meta": null
}
```

---

## 5. Fee Structures

### `GET /fees/structures`

List all fee structures for the school.

**Permission:** `fees.read`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "fee_001",
      "name": "Senior Secondary Fees - First Term",
      "term": "First Term",
      "academicYear": "2024",
      "grades": ["Form 4", "Form 5", "Form 6"],
      "lineItems": [
        { "id": "li_001", "name": "Tuition Fee", "amount": 350.00, "description": "Core academic instruction", "isOptional": false },
        { "id": "li_002", "name": "Sports Fee", "amount": 20.00, "description": "Sports facilities", "isOptional": true }
      ],
      "totalAmount": 450.00,
      "currency": "USD",
      "dueDate": "2024-01-20",
      "status": "PUBLISHED",
      "version": 2,
      "createdAt": "2023-12-01T10:00:00Z",
      "publishedAt": "2023-12-15T14:00:00Z"
    }
  ],
  "error": null,
  "meta": null
}
```

---

### `POST /fees/structures`

Create a new fee structure.

**Permission:** `fees.create`

**Request:**
```json
{
  "name": "Senior Secondary Fees - First Term",
  "term": "First Term",
  "academicYear": "2024",
  "grades": ["Form 4", "Form 5", "Form 6"],
  "lineItems": [
    { "name": "Tuition Fee", "amount": 350.00, "description": "Core academic instruction", "isOptional": false }
  ],
  "dueDate": "2024-01-20"
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `name` | string | Yes | 1-200 chars |
| `term` | string | Yes | Non-empty |
| `academicYear` | string | Yes | Non-empty |
| `grades` | string[] | Yes | At least 1 |
| `lineItems` | array | Yes | At least 1 item |
| `lineItems[].name` | string | Yes | Non-empty |
| `lineItems[].amount` | number | Yes | > 0 |
| `lineItems[].description` | string | No | |
| `lineItems[].isOptional` | boolean | Yes | |
| `dueDate` | string | Yes | `YYYY-MM-DD`, must be in the future |

**Response `201`:** Same envelope — `data` contains the created `FeeStructure` (status defaults to `DRAFT`, server generates `id`, `totalAmount`, `currency`, `version`, timestamps).

---

### `PATCH /fees/structures/:id`

Update a draft fee structure. Cannot update published structures.

**Permission:** `fees.update`

**Request:** Same fields as POST, all optional.

**Response `200`:** Same envelope — `data` contains the updated `FeeStructure`.

**Error `409`:**
```json
{
  "success": false,
  "data": null,
  "error": { "code": "CONFLICT", "message": "Cannot update a published fee structure" },
  "meta": null
}
```

---

### `POST /fees/structures/:id/publish`

Publish a draft fee structure.

**Permission:** `fees.publish`

**Request:** Empty body.

**Response `200`:** Same envelope — `data` contains the updated `FeeStructure` with `status: "PUBLISHED"` and `publishedAt`.

**Error `409`:** Already published.

---

### `POST /fees/structures/:id/generate-invoices`

Generate student invoices for a published fee structure.

**Permission:** `invoices.create`

**Request:** Empty body.

**Response `200`:**
```json
{
  "success": true,
  "data": { "count": 45 },
  "error": null,
  "meta": null
}
```

**Error `409`:** Structure is not PUBLISHED, or invoices already generated.

---

## 6. Invoices

### `GET /invoices`

List all invoices. Optional filter by student.

**Permission:** `invoices.read`

**Query Parameters:**

| Param | Type | Description |
|---|---|---|
| `studentId` | string | Filter by student ID |
| `status` | string | `UNPAID`, `PARTIAL`, `PAID`, `OVERDUE` |
| `page` | integer | Page number |
| `pageSize` | integer | Items per page |

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "inv_001",
      "studentId": "std_001",
      "student": {
        "firstName": "Rudo",
        "lastName": "Chikwanha",
        "studentId": "ARH-2024-001",
        "grade": "Form 4",
        "className": "Science A"
      },
      "feeStructureId": "fee_001",
      "feeStructure": {
        "name": "Senior Secondary Fees - First Term",
        "term": "First Term",
        "academicYear": "2024"
      },
      "totalAmount": 450.00,
      "paidAmount": 300.00,
      "balance": 150.00,
      "currency": "USD",
      "dueDate": "2024-01-20",
      "status": "PARTIAL",
      "createdAt": "2024-01-09T10:00:00Z"
    }
  ],
  "error": null,
  "meta": null
}
```

---

## 7. Payments

### `GET /payments`

List payments with filtering and pagination.

**Permission:** `payments.read`

**Query Parameters:**

| Param | Type | Description |
|---|---|---|
| `status` | string | `PENDING`, `SUCCESS`, `FAILED`, `REVERSED`, `DISPUTED` |
| `studentId` | string | Filter by student ID |
| `from` | string | Start date (ISO 8601) |
| `to` | string | End date (ISO 8601) |
| `page` | integer | Page number |
| `pageSize` | integer | Items per page |

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "pay_001",
      "reference": "PAY-2024-001234",
      "studentId": "std_002",
      "student": {
        "firstName": "Tendai",
        "lastName": "Moyo",
        "studentId": "ARH-2024-002",
        "grade": "Form 4"
      },
      "amount": 200.00,
      "currency": "USD",
      "status": "SUCCESS",
      "channel": "ECOCASH",
      "provider": "EcoCash",
      "payerName": "Tapiwa Moyo",
      "payerPhone": "+263 77 234 5678",
      "payerEmail": "tapiwa.moyo@email.com",
      "receiptNumber": "RCP-2024-001234",
      "metadata": {},
      "timeline": [
        { "id": "tl1", "event": "Payment Initiated", "description": "EcoCash payment initiated", "timestamp": "2024-01-12T10:00:00Z" },
        { "id": "tl2", "event": "Payment Successful", "description": "Payment completed", "timestamp": "2024-01-12T10:01:00Z" }
      ],
      "createdAt": "2024-01-12T10:00:00Z",
      "updatedAt": "2024-01-12T10:01:05Z"
    }
  ],
  "error": null,
  "meta": {
    "page": 1,
    "pageSize": 10,
    "totalCount": 42,
    "totalPages": 5
  }
}
```

---

### `GET /payments/:id`

Get a single payment with full timeline.

**Permission:** `payments.read`

**Response `200`:** Same envelope — `data` contains a single `Payment` object (same shape as list item), `meta` is `null`.

---

### `GET /payments/reconciliation`

Get daily reconciliation summaries for a date range.

**Permission:** `payments.reconcile`

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `from` | string | Yes | Start date (`YYYY-MM-DD`) |
| `to` | string | Yes | End date (`YYYY-MM-DD`) |

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "date": "2024-01-14",
      "totalTransactions": 12,
      "successCount": 10,
      "failedCount": 1,
      "pendingCount": 1,
      "totalAmount": 2450.00,
      "successAmount": 2100.00,
      "successRate": 83.3,
      "unmatchedPayments": 0
    }
  ],
  "error": null,
  "meta": null
}
```

---

## 8. Reminders

### `GET /reminders/configs`

List all reminder configurations.

**Permission:** `reminders.read`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "rem_001",
      "name": "7 Days Before Due Date",
      "timing": "BEFORE_DUE",
      "daysOffset": 7,
      "channels": ["SMS", "EMAIL"],
      "audience": "ALL",
      "grades": null,
      "studentIds": null,
      "messageTemplate": "Dear {guardian_name}, this is a reminder that {student_name}'s fees of {amount} is due on {due_date}.",
      "isActive": true,
      "createdAt": "2023-09-01T10:00:00Z"
    }
  ],
  "error": null,
  "meta": null
}
```

---

### `POST /reminders/configs`

Create a new reminder configuration.

**Permission:** `reminders.create`

**Request:**
```json
{
  "name": "7 Days Before Due Date",
  "timing": "BEFORE_DUE",
  "daysOffset": 7,
  "channels": ["SMS", "EMAIL"],
  "audience": "ALL",
  "messageTemplate": "Dear {guardian_name}, reminder about {student_name}."
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `name` | string | Yes | 1-200 chars |
| `timing` | string | Yes | `BEFORE_DUE`, `ON_DUE`, `AFTER_DUE` |
| `daysOffset` | integer | Yes | >= 0 |
| `channels` | string[] | Yes | At least 1; values: `SMS`, `WHATSAPP`, `EMAIL` |
| `audience` | string | Yes | `ALL`, `GRADE`, `CUSTOM` |
| `grades` | string[] | Conditional | Required when `audience` = `GRADE` |
| `studentIds` | string[] | Conditional | Required when `audience` = `CUSTOM` |
| `messageTemplate` | string | Yes | Non-empty, supports placeholders |

**Response `201`:** Same envelope — `data` contains the created `ReminderConfig`.

---

### `PATCH /reminders/configs/:id`

Update a reminder configuration.

**Permission:** `reminders.update`

**Request:** Same fields as POST, all optional.

**Response `200`:** Same envelope — `data` contains the updated `ReminderConfig`.

---

### `GET /reminders/history`

List reminder send history.

**Permission:** `reminders.read`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "rh_001",
      "configId": "rem_001",
      "configName": "7 Days Before Due Date",
      "sentAt": "2024-01-08T08:00:00Z",
      "recipientCount": 156,
      "deliveredCount": 152,
      "failedCount": 4,
      "channels": ["SMS", "EMAIL"]
    }
  ],
  "error": null,
  "meta": null
}
```

---

## 9. Reports

### `GET /reports/overview`

Get a collection/enrolment overview for a date range.

**Permission:** `reports.read`

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `from` | string | Yes | Start date (`YYYY-MM-DD`) |
| `to` | string | Yes | End date (`YYYY-MM-DD`) |

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "totalCollected": 28500.00,
    "outstandingBalance": 8750.00,
    "collectionRate": 76.9,
    "totalStudents": 156,
    "paidStudents": 98,
    "partialStudents": 35,
    "unpaidStudents": 23,
    "collectionByGrade": [
      { "grade": "Form 1", "collected": 3200.00, "outstanding": 800.00 }
    ],
    "collectionTrend": [
      { "date": "2024-01-01", "amount": 1250.00 }
    ],
    "topOverdueStudents": [
      {
        "student": { "firstName": "Nyasha", "lastName": "Dube", "studentId": "ARH-2024-003", "grade": "Form 3" },
        "balance": 300.00
      }
    ]
  },
  "error": null,
  "meta": null
}
```

---

### `GET /reports/outstanding`

Get all invoices with outstanding balances.

**Permission:** `reports.read`

**Query Parameters:** Same as `/reports/overview`.

**Response `200`:** Same envelope — `data` contains an array of `StudentInvoice` where `balance > 0`.

---

### `GET /reports/export`

Download a report as CSV.

**Permission:** `reports.export`

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | Report type: `collections`, `outstanding`, `enrolment` |
| `from` | string | Yes | Start date |
| `to` | string | Yes | End date |

**Response `200`:** `Content-Type: text/csv`, file download.

> This is the one exception where the response body is not JSON — it is a raw CSV file stream. On error, the response falls back to the standard JSON error envelope.

---

## 10. Audit Log

### `GET /audit/logs`

List audit log entries with filtering and pagination.

**Permission:** `audit.read`

**Query Parameters:**

| Param | Type | Description |
|---|---|---|
| `from` | string | Start timestamp (ISO 8601) |
| `to` | string | End timestamp (ISO 8601) |
| `actor` | string | Filter by actor user ID |
| `action` | string | Filter by action type |
| `page` | integer | Page number |
| `pageSize` | integer | Items per page (default 20) |

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "aud_001",
      "actor": { "id": "usr_001", "name": "Tendai Moyo", "email": "admin@arundelhigh.ac.zw" },
      "action": "PUBLISHED_FEE_STRUCTURE",
      "entity": "FeeStructure",
      "entityId": "fee_001",
      "details": { "name": "Senior Secondary Fees - First Term" },
      "ipAddress": "197.221.100.1",
      "userAgent": "Mozilla/5.0...",
      "timestamp": "2024-01-15T14:00:00Z"
    }
  ],
  "error": null,
  "meta": {
    "page": 1,
    "pageSize": 20,
    "totalCount": 87,
    "totalPages": 5
  }
}
```

---

## Endpoint Summary

| Method | Path | Permission | Paginated | Description |
|---|---|---|---|---|
| `POST` | `/auth/login` | Public | No | Login |
| `GET` | `/auth/me` | Authenticated | No | Current user |
| `POST` | `/auth/logout` | Authenticated | No | Logout |
| `GET` | `/school` | `school.read` | No | Get school profile |
| `PATCH` | `/school` | `school.update` | No | Update school profile |
| `GET` | `/school/users` | `users.read` | No | List school users |
| `POST` | `/school/users` | `users.create` | No | Invite user |
| `PATCH` | `/school/users/:id` | `users.update` | No | Update user |
| `GET` | `/students` | `students.read` | Yes | List students |
| `POST` | `/students` | `students.create` | No | Create student |
| `PATCH` | `/students/:id` | `students.update` | No | Update student |
| `POST` | `/students/import` | `students.import` | No | Import CSV |
| `GET` | `/students/imports` | `students.import` | No | List import jobs |
| `GET` | `/fees/structures` | `fees.read` | No | List fee structures |
| `POST` | `/fees/structures` | `fees.create` | No | Create fee structure |
| `PATCH` | `/fees/structures/:id` | `fees.update` | No | Update fee structure |
| `POST` | `/fees/structures/:id/publish` | `fees.publish` | No | Publish structure |
| `POST` | `/fees/structures/:id/generate-invoices` | `invoices.create` | No | Generate invoices |
| `GET` | `/invoices` | `invoices.read` | No | List invoices |
| `GET` | `/payments` | `payments.read` | Yes | List payments |
| `GET` | `/payments/:id` | `payments.read` | No | Get payment detail |
| `GET` | `/payments/reconciliation` | `payments.reconcile` | No | Reconciliation summary |
| `GET` | `/reminders/configs` | `reminders.read` | No | List reminder configs |
| `POST` | `/reminders/configs` | `reminders.create` | No | Create reminder config |
| `PATCH` | `/reminders/configs/:id` | `reminders.update` | No | Update reminder config |
| `GET` | `/reminders/history` | `reminders.read` | No | Reminder send history |
| `GET` | `/reports/overview` | `reports.read` | No | Collection overview |
| `GET` | `/reports/outstanding` | `reports.read` | No | Outstanding invoices |
| `GET` | `/reports/export` | `reports.export` | No | Export CSV |
| `GET` | `/audit/logs` | `audit.read` | Yes | Audit log entries |

**Total: 30 endpoints across 10 resource groups.**

All responses use the uniform `ApiResponse<T>` envelope with `success`, `data`, `error`, and `meta` fields. The only exception is `GET /reports/export` which returns a raw CSV stream on success.
