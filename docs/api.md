# Exam Haiti Agent API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication

All admin endpoints require Bearer token authentication.

**Header:**
```
Authorization: Bearer <ADMIN_PASSWORD>
```

**Response (401):**
```json
{
  "detail": "Invalid password"
}
```

---

## Public Endpoints

### GET /
Health check endpoint.

**Response:**
```json
{
  "name": "Exam Haiti Agent",
  "version": "0.1.0",
  "status": "running"
}
```

### GET /health
Simple health check.

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Admin Endpoints

All admin endpoints require authentication. Replace `<ADMIN_PASSWORD>` with your actual password.

### POST /admin/ingest
Upload and ingest a PDF file.

**Endpoint:** `POST /api/v1/admin/ingest`

**Content-Type:** `multipart/form-data`

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| file | File | Yes | PDF file to upload |

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/ingest \
  -H "Authorization: Bearer <ADMIN_PASSWORD>" \
  -F "file=@/path/to/exam.pdf"
```

**Success Response (200):**
```json
{
  "status": "success",
  "pdf_path": "data/pdfs/exam.pdf",
  "chunks": 42,
  "total_in_collection": 104
}
```

**Error Responses:**
- `401`: Invalid password
- `500`: Processing error

---

### GET /admin/chunks
Get chunks from Chroma vector store.

**Endpoint:** `GET /api/v1/admin/chunks`

**Query Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| exam_id | string | No | all | Filter by exam ID |
| limit | int | No | 20 | Max items to return |
| offset | int | No | 0 | Pagination offset |

**Example:**
```bash
curl "http://localhost:8000/api/v1/admin/chunks?limit=10" \
  -H "Authorization: Bearer <ADMIN_PASSWORD>"
```

**Success Response (200):**
```json
{
  "chunks": [
    {
      "content": "Question content...",
      "metadata": {
        "exam_file": "Chimie_2020_LLA",
        "chunk_type": "question_fillin",
        "subject": "Chimie",
        "year": 2020,
        "serie": "LLA",
        "section": "PARTIE A",
        "question_number": "1",
        "topic_hint": "hydrocarbures"
      },
      "chunk_index": 0
    }
  ],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

---

### GET /admin/graph/nodes
Get nodes from Neo4j graph.

**Endpoint:** `GET /api/v1/admin/graph/nodes`

**Query Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| type | string | No | all | Node type (Exam, Question, Section, Concept, Topic, Formula, Passage, Instruction) |
| limit | int | No | 50 | Max items to return |

**Example:**
```bash
curl "http://localhost:8000/api/v1/admin/graph/nodes?type=Concept&limit=10" \
  -H "Authorization: Bearer <ADMIN_PASSWORD>"
```

**Success Response (200):**
```json
{
  "nodes": [
    {
      "id": "Chimie_2020_LLA_Q1",
      "type": "Question",
      "properties": {
        "number": "1",
        "chunk_type": "question_fillin",
        "topic_hint": "hydrocarbures",
        "content": "Les hydrocarbures saturés...",
        "exam_subject": "Chimie",
        "exam_year": 2020
      }
    }
  ],
  "count": 10
}
```

---

### GET /admin/graph/stats
Get graph statistics.

**Endpoint:** `GET /api/v1/admin/graph/stats`

**Example:**
```bash
curl "http://localhost:8000/api/v1/admin/graph/stats" \
  -H "Authorization: Bearer <ADMIN_PASSWORD>"
```

**Success Response (200):**
```json
{
  "nodes": {
    "Exam": 2,
    "Question": 51,
    "Section": 12,
    "Concept": 35,
    "Topic": 24,
    "Formula": 6,
    "Passage": 3,
    "Instruction": 2
  },
  "relationships": {
    "has_entity": 117,
    "has_question_in_exam": 31,
    "has_question": 24,
    "next": 23,
    "has_section": 13,
    "has_passage": 5,
    "has_instruction": 2
  }
}
```

---

### POST /admin/graph/sync
Sync from Chroma to Neo4j.

**Endpoint:** `POST /api/v1/admin/graph/sync`

**Query Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| llm | bool | No | false | Enable LLM-enhanced extraction |

**Example:**
```bash
# Rule-based sync
curl -X POST "http://localhost:8000/api/v1/admin/graph/sync" \
  -H "Authorization: Bearer <ADMIN_PASSWORD>"

# LLM-enhanced sync
curl -X POST "http://localhost:8000/api/v1/admin/graph/sync?llm=true" \
  -H "Authorization: Bearer <ADMIN_PASSWORD>"
```

**Success Response (200):**
```json
{
  "status": "success",
  "exams_synced": 2,
  "total_chunks": 62,
  "mode": "llm_enhanced"
}
```

---

### GET /admin/exams
List all exams from Chroma.

**Endpoint:** `GET /api/v1/admin/exams`

**Example:**
```bash
curl "http://localhost:8000/api/v1/admin/exams" \
  -H "Authorization: Bearer <ADMIN_PASSWORD>"
```

**Success Response (200):**
```json
{
  "exams": [
    {
      "exam_id": "Chimie_2020_LLA_Dioxyde",
      "subject": "Chimie",
      "year": 2020,
      "serie": "LLA",
      "chunk_count": 20,
      "pdf_path": "data/pdfs/Chimie_020_LLA_Dioxyde.pdf"
    }
  ],
  "total": 2
}
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid password"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message here"
}
```

### 503 Service Unavailable
```json
{
  "detail": "Neo4j is not enabled"
}
```

---

## Usage Examples

### JavaScript/Fetch
```javascript
const API_BASE = 'http://localhost:8000/api/v1';
const ADMIN_PASSWORD = 'your_password_here';

const headers = {
  'Authorization': `Bearer ${ADMIN_PASSWORD}`
};

// Get chunks
async function getChunks(limit = 20) {
  const res = await fetch(`${API_BASE}/admin/chunks?limit=${limit}`, { headers });
  return res.json();
}

// Upload PDF
async function uploadPDF(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/admin/ingest`, {
    method: 'POST',
    headers,
    body: formData
  });
  return res.json();
}

// Run graph sync
async function syncGraph(llm = false) {
  const res = await fetch(`${API_BASE}/admin/graph/sync?llm=${llm}`, {
    method: 'POST',
    headers
  });
  return res.json();
}
```

### Python
```python
import requests

API_BASE = 'http://localhost:8000/api/v1'
ADMIN_PASSWORD = 'your_password_here'

headers = {'Authorization': f'Bearer {ADMIN_PASSWORD}'}

# Get chunks
def get_chunks(limit=20):
    r = requests.get(f'{API_BASE}/admin/chunks?limit={limit}', headers=headers)
    return r.json()

# Upload PDF
def upload_pdf(file_path):
    with open(file_path, 'rb') as f:
        r = requests.post(
            f'{API_BASE}/admin/ingest',
            headers=headers,
            files={'file': f}
        )
    return r.json()

# Run graph sync
def sync_graph(llm=False):
    r = requests.post(
        f'{API_BASE}/admin/graph/sync?llm={llm}',
        headers=headers
    )
    return r.json()
```

---

## Environment Variables

Required for admin API:

| Variable | Description |
|----------|-------------|
| `ADMIN_PASSWORD` | Password for admin endpoints |
| `OPENAI_API_KEY` | Required for PDF ingestion |
| `NEO4J_ENABLED` | Set to `true` for graph features |
| `NEO4J_URI` | Neo4j connection URI |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
