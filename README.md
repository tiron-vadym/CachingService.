# FastAPI Caching Microservice & CLI

A high-performance asynchronous caching microservice built with **FastAPI**, **SQLModel**, and **Pydantic Settings**, accompanied by a programmatic CLI testing tool.

---

## Overview

The service generates payloads by interleaving two lists of strings after applying an external "transformer function". To optimize performance and resource usage, the service:
1. **Minimizes external calls**: Caches each unique transformed string in the database so identical strings are never transformed twice.
2. **Reuses payload identifiers**: If a payload for the exact same input lists was previously generated, its existing identifier is reused without any redundant external calls or duplicate database records.
3. **Database Flexibility**: Uses **SQLModel** / **SQLAlchemy 2.0** with asynchronous drivers, supporting **SQLite** (`aiosqlite`) by default and **PostgreSQL** (`asyncpg`) with simple configuration.
4. **Programmatic CLI**: Includes `cache-cli` built with **Pydantic Settings** for parsing, validation, and benchmarking.

---

## Architecture & How It Works

```
                     +----------------------------------------+
                     |            Client / CLI                |
                     +-------------------+--------------------+
                                         |
                                         | HTTP POST /payload
                                         v
                     +----------------------------------------+
                     |         FastAPI Microservice           |
                     |  - Validates equal length lists        |
                     |  - Computes deterministic input hash   |
                     +-------------------+--------------------+
                                         |
                         +---------------+---------------+
                         | Payload already generated?    |
                         +---------------+---------------+
                               YES /           \ NO
                                  /             \
             Reuse existing payload ID           Query DB Cache for
             (0 transformer calls)               known transformed strings
                                                        |
                                          Transform uncached strings only
                                          (Save new cache entries)
                                                        |
                                          Interleave transformed strings
                                                        |
                                          Save PayloadRecord & Return ID
```

---

## Endpoints

### 1. Create or Reuse Payload
- **Method**: `POST /payload`
- **Request Body**:
  ```json
  {
    "list_1": ["first string", "second string", "third string"],
    "list_2": ["other string", "another string", "last string"]
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": "e4b6c8d1-1234-5678-9abc-def012345678",
    "message": "Payload generated and stored successfully"
  }
  ```
  *(If repeated with identical input, returns the same `id` with `"Payload already exists; reused existing identifier"`).*

### 2. Read Payload Output
- **Method**: `GET /payload/{id}`
- **Response** (`200 OK`):
  ```json
  {
    "output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
  }
  ```

### 3. Health Check
- **Method**: `GET /health`
- **Response** (`200 OK`):
  ```json
  {
    "status": "healthy",
    "database": "connected"
  }
  ```

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

### 1. Clone & Set Up Virtual Environment

```bash
git clone <repo_url>
cd cashing-service

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies and editable CLI package
pip install -r requirements-dev.txt
pip install -e .
```

### 2. Environment Configuration

Copy `.env.example` to `.env` if custom configuration is needed:

```bash
cp .env.example .env
```

Available environment variables:
- `DATABASE_URL`: Connection string (default: `sqlite+aiosqlite:///./cache_service.db`)
- `TRANSFORMER_DELAY_SECONDS`: External service simulated latency (default: `0.05`)
- `ENVIRONMENT`: `development` | `production` | `test`
- `HOST`: Server bind address (default: `0.0.0.0`)
- `PORT`: Server bind port (default: `8000`)

---

## Running the Server

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API documentation (Swagger UI) is available at:
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

---

## CLI Tool (`cache-cli`)

The CLI tool allows programmatic testing and benchmarking of the caching service. It uses **Pydantic Settings** to parse and sanitize command-line arguments.

### Syntax

```bash
cache-cli [-h|--host URL] [-r|--repeat N] [-i|--input FILE|-] [-j|--json JSON] [-o|--output FILE|-] [--help]
```

### Arguments

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-h`, `--host URL` | Points to the caching microservice server | `http://localhost:8000` |
| `-r`, `--repeat N` | Indicates number of iterations to perform | `1` |
| `-i`, `--input FILE\|-` | Input JSON file path (`-` for stdin) | `None` |
| `-j`, `--json JSON` | Input argument directly in JSON format | `None` |
| `-o`, `--output FILE\|-` | Output destination file path (`-` for stdout) | `-` |
| `--help` | Displays help message and exits | |

### CLI Examples

#### Example 1: Direct JSON input to stdout
```bash
cache-cli --json "{\"list_1\": [\"first string\", \"second string\", \"third string\"], \"list_2\": [\"other string\", \"another string\", \"last string\"]}"
```
**Output:**
```
FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING
```

#### Example 2: Repeated runs to observe cache speedup
```bash
cache-cli --repeat 3 --json "{\"list_1\": [\"apple\", \"banana\"], \"list_2\": [\"cherry\", \"date\"]}"
```
**Stderr output:**
```
[Iteration 1/3] ID: 52a1fd80-... | Elapsed: 104.52ms | Payload generated and stored successfully
[Iteration 2/3] ID: 52a1fd80-... | Elapsed: 3.12ms | Payload already exists; reused existing identifier
[Iteration 3/3] ID: 52a1fd80-... | Elapsed: 2.89ms | Payload already exists; reused existing identifier
```
*(Notice the significant latency reduction from 104ms to ~3ms on subsequent requests!)*

#### Example 3: Read from file and save to output file
```bash
# Save payload to a file
echo '{"list_1": ["alpha"], "list_2": ["beta"]}' > input.json

# Run CLI
cache-cli --input input.json --output result.txt

# Inspect output
cat result.txt
```

#### Example 4: Pipe JSON via stdin
```bash
cat input.json | cache-cli --input -
```

---

## Running Tests

Run the full pytest suite with test coverage reporting:

```bash
pytest -v --cov=app --cov=cli
```

All 33 tests cover:
- External transformer simulation, call counters, and delay behavior.
- Database models and timezone handling.
- Payload hashing, deduplication within requests, and string interleaving.
- Cache hit/miss optimization and payload ID reusability.
- FastAPI endpoints (POST `/payload`, GET `/payload/{id}`, GET `/health`, error cases).
- CLI argument parsing, JSON resolution (file, stdin, CLI string), benchmarking, and error handling.

---

## Docker & Docker Compose

### Using Docker

Build the Docker image:
```bash
docker build -t caching-service .
```

Run the container:
```bash
docker run -p 8000:8000 caching-service
```

### Using Docker Compose

```bash
# Start service in background
docker compose up -d

# View logs
docker compose logs -f

# Check health status
docker compose ps

# Stop service
docker compose down
```

---

## License

MIT License.
