# Planventure API

A Flask REST API for planning trips. Users register, log in with JWT authentication, and manage their own trips (destination, dates, coordinates and a day-by-day itinerary). Data is stored with SQLAlchemy (SQLite by default).

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Authentication](#authentication)
- [API reference](#api-reference)
- [Data models](#data-models)
- [Error format](#error-format)
- [Testing the API](#testing-the-api)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)

## Features

- User registration with email validation and password rules
- Login with short-lived access tokens and long-lived refresh tokens (JWT)
- `@auth_required` decorator for protecting routes
- Full CRUD for trips, scoped to the authenticated user
- Default day-by-day itinerary template generated from the trip dates
- Salted PBKDF2-SHA256 password hashing
- CORS configured for a React frontend (`/api/*`)

## Tech stack

| Area | Package |
|---|---|
| Web framework | Flask 2.3.3 |
| ORM | Flask-SQLAlchemy 3.1.1 |
| Auth | Flask-JWT-Extended 4.6.0 |
| CORS | Flask-CORS 4.0.0 |
| Email validation | email-validator 2.1.0 |
| Environment | python-dotenv 1.0.0 |
| Migrations (optional) | Flask-Migrate 4.0.5 |

## Project structure

```
planventure-api/
├── app.py            # App factory (create_app), config, CORS, blueprint registration
├── extensions.py     # Shared db (SQLAlchemy) and jwt (JWTManager) instances
├── models.py         # User and Trip models
├── security.py       # hash_password() / verify_password()
├── auth.py           # JWT helpers: generate and validate tokens
├── middleware.py     # @auth_required decorator and JWT error handlers
├── auth_routes.py    # /api/auth/* routes
├── trip_routes.py    # /api/trips/* routes
├── itinerary.py      # generate_default_itinerary()
├── init_db.py        # Creates the database tables
├── requirements.txt
└── .sample.env       # Example environment file
```

Do not add an `__init__.py` to this folder. The modules use absolute imports such as `from extensions import db`, and an `__init__.py` makes `flask run` treat the folder as a package, which breaks them.

## Getting started

### Prerequisites

- Python 3.8 or higher
- Git
- An API client such as [Bruno](https://www.usebruno.com/) or `curl`

### Setup

1. Go to the API folder:
   ```powershell
   cd planventure-api
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create your environment file from the sample and fill in the values (see [Configuration](#configuration)):
   ```powershell
   copy .sample.env .env          # macOS/Linux: cp .sample.env .env
   ```
5. Create the database tables:
   ```bash
   python init_db.py
   ```
6. Start the development server:
   ```bash
   flask run --debug
   ```

The API is now available at `http://127.0.0.1:5000`.

`db.create_all()` (used by `init_db.py`) only creates missing tables. It does not alter existing ones. If you change a model, either delete the SQLite file and re-run `init_db.py` (this loses data) or use Flask-Migrate.

## Configuration

Settings are read from environment variables (loaded from `.env`). All have development defaults, but you must set real secrets in production.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-me` | Flask secret key |
| `JWT_SECRET_KEY` | `dev-jwt-secret-change-me` | Key used to sign JWTs |
| `JWT_ACCESS_MINUTES` | `15` | Access token lifetime in minutes |
| `JWT_REFRESH_DAYS` | `30` | Refresh token lifetime in days |
| `DATABASE_URL` | SQLite file `planventure.db` next to `app.py` | SQLAlchemy database URL |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated list of allowed frontend origins |
| `FLASK_DEBUG` | `false` | Enables debug mode when started with `python app.py` |

Example `.env`:

```
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me-too
DATABASE_URL=sqlite:///planventure.db
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
FLASK_DEBUG=true
```

Restart the server after changing `.env`. Add `.env` to `.gitignore`.

### CORS

CORS applies to `/api/*` only. Allowed methods are `GET`, `POST`, `PUT`, `PATCH`, `DELETE` and `OPTIONS`, and allowed headers are `Content-Type` and `Authorization`. Credentials (cookies) are not enabled because tokens are sent in a header.

## Authentication

The API uses JWT Bearer tokens.

1. Call `POST /api/auth/register` or `POST /api/auth/login`. The response contains an `access_token` and a `refresh_token`.
2. Send the access token on protected requests:
   ```
   Authorization: Bearer <access_token>
   ```
3. Only access tokens are accepted on protected routes. A refresh token is rejected with `401`.

Protected routes return `401` for a missing, invalid or expired token, or if the user no longer exists.

### Protecting your own routes

```python
from flask import g, jsonify
from middleware import auth_required

@bp.route("/example")
@auth_required
def example():
    return jsonify({"email": g.current_user.email})
```

The authenticated user is available as `g.current_user`. Put `@auth_required` below the `@route` decorator, so the route registers the protected function.

## API reference

Base URL: `http://127.0.0.1:5000`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | No | Welcome message |
| `GET` | `/health` | No | Health check with UTC timestamp |
| `POST` | `/api/auth/register` | No | Create an account |
| `POST` | `/api/auth/login` | No | Log in |
| `GET` | `/api/auth/me` | Yes | Current user |
| `GET` | `/api/trips` | Yes | List your trips |
| `POST` | `/api/trips` | Yes | Create a trip |
| `GET` | `/api/trips/<id>` | Yes | Get a trip |
| `PUT` | `/api/trips/<id>` | Yes | Replace a trip (required fields must be sent) |
| `PATCH` | `/api/trips/<id>` | Yes | Update some fields |
| `DELETE` | `/api/trips/<id>` | Yes | Delete a trip |

### `POST /api/auth/register`

Request:
```json
{ "email": "a@example.com", "password": "secret123" }
```

Rules:
- Email must be a valid address (syntax only, no DNS lookup). It is stored in lowercase, up to 255 characters.
- Password must be 8 to 128 characters and contain at least one letter and one number.

Responses:
- `201`: the new user plus `access_token` and `refresh_token`
- `400`: validation errors
- `409`: email already registered

```json
{
  "message": "User registered successfully",
  "user": { "id": 1, "email": "a@example.com", "created_at": "...", "updated_at": "..." },
  "access_token": "...",
  "refresh_token": "..."
}
```

### `POST /api/auth/login`

Request:
```json
{ "email": "a@example.com", "password": "secret123" }
```

Responses:
- `200`: the user plus `access_token` and `refresh_token`
- `400`: missing email or password, or a body that is not a JSON object
- `401`: `{"error": "Invalid email or password"}`. The same message is used for an unknown email and a wrong password.

### `GET /api/auth/me`

Returns `{"user": {...}}` for the authenticated user.

### Trips

All trip routes only see trips owned by the authenticated user. A trip that does not exist or belongs to someone else returns `404`.

#### `POST /api/trips`

Request:
```json
{
  "destination": "Lisbon, Portugal",
  "start_date": "2026-12-01",
  "end_date": "2026-12-07",
  "coordinates": { "latitude": 38.7223, "longitude": -9.1393 },
  "itinerary": { "day1": ["Arrive and check in", "Alfama walk"] }
}
```

| Field | Required | Rules |
|---|---|---|
| `destination` | Yes | Non-empty string, at most 255 characters |
| `start_date` | Yes | `YYYY-MM-DD` |
| `end_date` | Yes | `YYYY-MM-DD`, not before `start_date` |
| `coordinates` | No | Object with `latitude` (-90 to 90) and `longitude` (-180 to 180). You can also send `latitude` and `longitude` as top-level fields |
| `itinerary` | No | JSON object or array. If omitted, a [default template](#default-itinerary-template) is generated |

Response `201`:
```json
{
  "trip": {
    "id": 1,
    "user_id": 1,
    "destination": "Lisbon, Portugal",
    "start_date": "2026-12-01",
    "end_date": "2026-12-07",
    "coordinates": { "latitude": 38.7223, "longitude": -9.1393 },
    "itinerary": { "day1": ["Arrive and check in", "Alfama walk"] },
    "created_at": "...",
    "updated_at": "..."
  }
}
```

#### `GET /api/trips`

Returns `{"trips": [...]}` ordered by start date. There is no pagination yet.

#### `GET /api/trips/<id>`

Returns `{"trip": {...}}` or `404`.

#### `PUT /api/trips/<id>` and `PATCH /api/trips/<id>`

`PUT` requires all required fields. `PATCH` accepts any subset of fields. Both return `{"trip": {...}}`, `400` on validation errors, or `404`. On `PATCH`, the `end_date >= start_date` check also uses the dates already stored.

Example `PATCH` body:
```json
{ "end_date": "2026-12-09", "itinerary": { "day1": ["Arrive and check in"] } }
```

#### `DELETE /api/trips/<id>`

Returns `204` with an empty body, or `404`.

### Default itinerary template

When a trip is created without an `itinerary`, `generate_default_itinerary()` builds one entry per day from `start_date` to `end_date` (inclusive, at most 366 days):

```json
{
  "destination": "Lisbon, Portugal",
  "total_days": 2,
  "days": [
    { "day": 1, "date": "2026-12-01", "title": "Day 1", "activities": [], "notes": "" },
    { "day": 2, "date": "2026-12-02", "title": "Day 2", "activities": [], "notes": "" }
  ]
}
```

## Data models

### User (`users`)

| Column | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `email` | String(255) | Unique, indexed, not null |
| `password_hash` | String(255) | PBKDF2-SHA256 hash with the salt embedded |
| `created_at` | DateTime | UTC |
| `updated_at` | DateTime | UTC, refreshed on update |

A user has many trips. Deleting a user deletes their trips.

### Trip (`trips`)

| Column | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `user_id` | Integer | Foreign key to `users.id`, indexed |
| `destination` | String(255) | Required |
| `start_date` | Date | Required |
| `end_date` | Date | Required |
| `latitude` | Float | Optional |
| `longitude` | Float | Optional |
| `itinerary` | JSON | Defaults to `{}` at the model level |
| `created_at` | DateTime | UTC |
| `updated_at` | DateTime | UTC, refreshed on update |

Database constraints: `end_date >= start_date`, latitude between -90 and 90, longitude between -180 and 180.

## Error format

Errors are JSON. Validation errors include per-field details:

```json
{
  "error": "Validation failed",
  "details": { "email": "Email is required" }
}
```

| Status | Meaning |
|---|---|
| `400` | Invalid body or validation failure |
| `401` | Missing, invalid or expired token, or wrong credentials |
| `404` | Resource not found (or owned by another user) |
| `405` | Method not allowed on that path |
| `409` | Email already registered |

## Testing the API

PowerShell with `curl.exe`:

```powershell
# Register
curl.exe -X POST http://127.0.0.1:5000/api/auth/register -H "Content-Type: application/json" -d '{\"email\":\"a@example.com\",\"password\":\"secret123\"}'

# Log in and keep the token
$token = (curl.exe -s -X POST http://127.0.0.1:5000/api/auth/login -H "Content-Type: application/json" -d '{\"email\":\"a@example.com\",\"password\":\"secret123\"}' | ConvertFrom-Json).access_token

# Create a trip from a JSON file
curl.exe -X POST http://127.0.0.1:5000/api/trips -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d "@trip.json"

# List trips
curl.exe http://127.0.0.1:5000/api/trips -H "Authorization: Bearer $token"

# Delete a trip
curl.exe -X DELETE http://127.0.0.1:5000/api/trips/1 -H "Authorization: Bearer $token"
```

`trip.json`:
```json
{
  "destination": "Lisbon, Portugal",
  "start_date": "2026-12-01",
  "end_date": "2026-12-07",
  "coordinates": { "latitude": 38.7223, "longitude": -9.1393 }
}
```

Calling the API from React:

```js
fetch("http://127.0.0.1:5000/api/trips", {
  headers: { Authorization: `Bearer ${token}` },
});
```

## Troubleshooting

- **`ModuleNotFoundError: No module named 'extensions'`**: make sure there is no `__init__.py` in `planventure-api` and run `flask` from inside that folder.
- **Import errors for `flask`, `flask_jwt_extended` or `email_validator`**: activate the virtual environment and run `pip install -r requirements.txt`.
- **`404` on `/auth/register`**: auth routes live under `/api/auth`.
- **`405` when opening a route in the browser**: most routes need `POST`, `PUT`, `PATCH` or `DELETE`, not `GET`.
- **CORS error in the browser**: add your frontend origin to `CORS_ORIGINS` and restart the server.
- **Missing table errors**: run `python init_db.py`.

## Security notes

- Set strong, unique values for `SECRET_KEY` and `JWT_SECRET_KEY` before deploying. The defaults are for development only.
- Never commit `.env`.
- Add rate limiting or lockout to the register and login routes before exposing the API publicly.
- Registration returns `409` for an existing email, which reveals that the address is registered.
- Restrict `CORS_ORIGINS` to your real frontend URL in production.
