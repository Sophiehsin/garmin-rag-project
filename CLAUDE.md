# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Garmin Insight RAG** is a Retrieval-Augmented Generation (RAG) system that processes Garmin fitness wearable data (activities, sleep, personal records) and provides intelligent health insights through an AI assistant. The project is in Phase 2, with foundation work (Tasks 1-6) completed: ZIP parsing, Pydantic models (1,015 lines), SQLModel database schema, timestamp normalization, and unit conversion functions.

**Tech Stack:**
- Backend: FastAPI + Uvicorn
- Database: PostgreSQL + pgvector (for vector embeddings)
- Data Models: Pydantic + SQLModel
- Data Processing: pandas-compatible services
- LLM Integration: Claude (Anthropic), with Gemini support planned
- Testing: pytest + fixtures
- Containerization: Docker + Docker Compose

## Directory Structure

```
garmin-rag-project/
├── app/
│   ├── core/
│   │   ├── config.py          # Environment & app settings (stub)
│   │   ├── database.py        # DB session & connection (stub)
│   │   └── constants.py       # App constants (stub)
│   ├── models/                # Data models
│   │   ├── base.py            # Base model mixins (stub)
│   │   ├── activities.py      # SummarizedActivityModel (283 lines, 45+ fields)
│   │   ├── sleep.py           # SleepDataModel (393 lines, 50+ fields)
│   │   ├── records.py         # PersonalRecordModel (339 lines, 30+ fields)
│   │   └── sql_models.py      # SQLModel schemas: User, SummarizedActivityDB, SleepDataDB, PersonalRecordDB
│   ├── api/
│   │   ├── dependencies.py    # DI for endpoints (stub)
│   │   ├── schemas.py         # Request/response schemas (stub)
│   │   └── routers/           # API endpoint routers (empty, to be implemented)
│   ├── services/
│   │   ├── parser.py          # ZIP parsing, JSON key normalization, timestamp & unit conversion (306 lines)
│   │   ├── calendar.py        # Google Calendar API service (stub)
│   │   └── rag_engine.py      # LangChain RAG pipeline (stub)
│   └── main.py                # FastAPI app initialization (stub)
├── tests/
│   ├── conftest.py            # pytest configuration & fixtures (stub)
│   ├── fixtures/
│   │   ├── garmin_samples.py  # Test data generators
│   │   └── user_fixtures.py   # User fixtures
│   ├── integration/           # Integration tests (empty)
│   ├── test_sql_models.py     # 4 tests for SQLModel schemas (all passing)
│   └── test_parser.py         # 19 tests for parser functions (all passing)
├── scripts/
│   ├── analyze_garmin_zip.py  # ZIP structure analysis tool
│   └── test_db_connection.py  # DB connection tester
├── data/
│   ├── samples/               # Real Garmin sample data (summarizedActivities.json, sleepData.json, etc.)
│   ├── analysis/              # Cached analysis results
│   └── cache/                 # Processing cache
├── note/                      # Documentation & analysis notes
├── docker-compose.yml         # PostgreSQL + pgvector dev environment
├── Dockerfile                 # Containerized app deployment
├── requirements.txt           # Python dependencies
└── .gitignore                 # Excludes .env, credentials, venv, data/

Key Files in root: COMPLETION_CHECKLIST.md, PROJECT_STATUS.md, DATA_PROCESSING_GUIDE.md, TASK_4_5_6_COMPLETE.md
```

## Common Commands

### Setup & Installation
```bash
# Create virtual environment
python3 -m venv rag.venv
source rag.venv/bin/activate  # On Windows: rag.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL + pgvector locally
docker-compose up -d
```

### Running Tests
```bash
# Run all tests
pytest

# Run only parser tests (19 tests)
pytest tests/test_parser.py -v

# Run only SQL model tests (4 tests)
pytest tests/test_sql_models.py -v

# Run a single test
pytest tests/test_parser.py::test_parse_garmin_zip_extracts_three_core_files -v

# Run with coverage
pytest --cov=app tests/

# Run tests matching pattern
pytest -k "timestamp" -v

# Run with detailed output
pytest tests/ -vv --tb=short
```

### Development
```bash
# Start FastAPI dev server (when implemented)
uvicorn app.main:app --reload --port 8000

# Analyze ZIP file structure
python scripts/analyze_garmin_zip.py /path/to/garmin_export.zip

# Test database connection
python scripts/test_db_connection.py
```

## Data Models & Architecture

### Core Models (Pydantic, v2)

Three comprehensive Pydantic models represent Garmin data:

1. **SummarizedActivityModel** (`app/models/activities.py`)
   - Represents a single workout/activity session
   - 45+ fields: activity_id, activity_type, start_time_in_seconds (milliseconds), duration, distance (meters), avg_moving_speed (m/s), max_moving_speed, calories, heart rate metrics, elevation_gain, etc.
   - All numeric fields validated (ge/gt for non-negative/positive)
   - Timestamps in Unix milliseconds (Garmin native format)

2. **SleepDataModel** (`app/models/sleep.py`)
   - Represents a single night's sleep record
   - 50+ fields: calendar_date, sleep_start_timestamp_gmt, sleep_end_timestamp_gmt (ISO 8601), deep/light/rem/awake_sleep_seconds, heart_rate metrics, respiration metrics, SpO2 (0-100%), sleep quality scores (0-100), etc.
   - Optional fields for missing metrics
   - Timestamps in ISO 8601 format with GMT timezone

3. **PersonalRecordModel** (`app/models/records.py`)
   - Represents personal bests/achievements
   - 30+ fields: personal_record_id, personal_record_type, value, record_unit (meter/second/etc.), record_date (text format), linked_activity_id, activity_type, display_order, etc.
   - Supports multiple date formats for record_date

### SQLModel Database Schema (`app/models/sql_models.py`)

SQLModel (SQLAlchemy + Pydantic) provides the database layer:

- **User** table: Minimal user table (id, email) for foreign key relationships
- **SummarizedActivityDB**: Stores activities with composite index on (user_id, start_time_in_seconds) for efficient range queries
- **SleepDataDB**: Stores sleep records with composite index on (user_id, calendar_date)
- **PersonalRecordDB**: Stores personal records with index on (user_id, personal_record_type)

All DB tables include `created_at` and `updated_at` audit fields for tracking.

### Data Processing Pipeline

**app/services/parser.py** (306 lines) handles all data transformation:

1. **ZIP Extraction**: `parse_garmin_zip(zip_path, target_jsons=None)`
   - Extracts 3 core JSON files from Garmin ZIP: summarizedActivities.json, sleepData.json, personalRecord.json
   - Returns normalized dict with snake_case keys

2. **Key Normalization**: `normalize_json_keys(value)` & `camel_to_snake(value)`
   - Recursively converts camelCase field names to snake_case (e.g., activityId → activity_id, startTimeInSeconds → start_time_in_seconds)
   - Handles nested dicts and lists

3. **Timestamp Normalization**: `normalize_timestamp(timestamp_value)`
   - Handles 3 Garmin timestamp formats:
     - Unix milliseconds (Activities): 1715904000000
     - ISO 8601 (Sleep): "2024-05-14T15:41:04.0Z"
     - Text dates (Records): "May 15, 2024", "15-May-2024", "Sat Apr 11 16:00:00 GMT 2026"
   - Returns UTC datetime object; returns None for invalid input

4. **Unit Conversion** (6 bidirectional functions):
   - Distance: meters ↔ kilometers (÷1000 / ×1000)
   - Speed: m/s ↔ km/h (×3.6 / ÷3.6)
   - Elevation: feet ↔ meters (×0.3048 / ÷0.3048)
   - All handle None and invalid input gracefully

## Test Coverage

**23 tests, 100% passing:**

### Parser Tests (19 tests in `tests/test_parser.py`)
- JSON normalization: camelCase → snake_case recursive conversion
- ZIP parsing: Extract 3 core files, identify file names, handle missing files
- Timestamp normalization: Unix ms, ISO 8601, 5 text date formats, None/invalid handling
- Unit conversions: Distance, speed, elevation bidirectional conversions with round-trip validation

### SQL Model Tests (4 tests in `tests/test_sql_models.py`)
- User model fields and defaults
- Activity DB defaults (timestamps, calories)
- Sleep DB defaults (unmeasurable_seconds, null fields)
- Personal record DB fields and relationships

**Key Testing Patterns:**
- Use `tmp_path` pytest fixture for temporary ZIP files
- Test both success and error paths (missing files, invalid input)
- Verify round-trip conversions (convert A→B→A ≈ A)
- Validate all edge cases (None input, zero values, invalid formats)

Real Garmin sample data exists in `data/samples/` but is not yet integrated into tests. Future integration tests should use this real data to validate against actual Garmin data complexities.

## Data Flow & Architecture

```
1. Garmin Export (ZIP)
   ↓ parse_garmin_zip()
2. Extracted JSON files (3 files: activities, sleep, records)
   ↓ normalize_json_keys()
3. Normalized JSON (snake_case keys)
   ↓ Pydantic validation (activities.py, sleep.py, records.py)
4. Validated Pydantic Models
   ↓ SQLModel conversion & database insertion
5. PostgreSQL Database (with pgvector for embeddings)
   ↓ [To be implemented] LangChain RAG Engine
6. Vector Search + LLM Generation
   ↓
7. AI Health Insights (Claude/Gemini)
```

## Implementation Status

**Completed (Tasks 1-6):**
- ✅ ZIP structure analysis and core file identification
- ✅ 3 Pydantic models (1,015 lines total)
- ✅ SQLModel database schema with relationships & indexes
- ✅ ZIP parsing, JSON key normalization, file discovery
- ✅ Timestamp normalization (3 formats → UTC)
- ✅ Unit conversion (6 bidirectional functions)
- ✅ 23 comprehensive tests (all passing)

**Not Yet Implemented:**
- ❌ FastAPI endpoints (router stubs exist)
- ❌ Database connection layer (session management)
- ❌ LangChain RAG pipeline
- ❌ Vector embeddings & similarity search
- ❌ Google Calendar API integration
- ❌ Authentication & authorization
- ❌ API schemas for request/response

## Key Design Decisions

1. **Pydantic + SQLModel**: Single data definition used for both validation and ORM, reducing duplication and ensuring consistency
2. **Native Units**: Store all data in Garmin's native units (milliseconds, meters, m/s) to preserve precision; conversion happens at presentation layer
3. **UTC Timestamps**: All timestamps normalized to UTC for consistency across time zones
4. **Recursive Normalization**: Deeply normalize nested JSON structures to handle Garmin's complex hierarchies
5. **Defensive Input Handling**: All parser functions gracefully handle None, missing, or invalid input

## Debugging & Investigation

**Common Issues & Troubleshooting:**

1. **Test failures**: Check that real data path (`data/samples/`) exists; some integration tests may be skipped without real ZIP files
2. **ZIP parsing**: Run `python scripts/analyze_garmin_zip.py /path/to/zip` to inspect actual ZIP structure before debugging parser
3. **Timestamp errors**: Review `TESTING_AND_CHUNKING_ANALYSIS.md` for notes on different Garmin timestamp formats
4. **Database connection**: Run `python scripts/test_db_connection.py` to verify PostgreSQL + pgvector setup

**Documentation Files:**
- `COMPLETION_CHECKLIST.md`: High-level task completion status
- `PROJECT_STATUS.md`: Detailed implementation statistics
- `DATA_PROCESSING_GUIDE.md`: Deep dive into SQL model design, field constraints, indexing strategy
- `TESTING_AND_CHUNKING_ANALYSIS.md`: Test coverage analysis, real data integration recommendations, Task 7 chunking strategy
- `MODIFICATION_EXAMPLES.md`: Practical examples for extending Pydantic models

