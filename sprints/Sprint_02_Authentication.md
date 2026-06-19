# Sprint 02 - Authentication

## Portfolio context

Replace the Sprint 01 session placeholder with real API authentication. The
platform is API-only, so clients authenticate with email and password and receive
a token for subsequent requests.

This sprint should be completed after the local foundation and before AWS upload
workflows depend on a stable user identity. Later sprints assume every media
item belongs to an authenticated user.

## User story

As a user, I want to register, log in, and log out securely so only I can
create upload requests and view my media.

## Architecture focus

```text
API Client
   |
   | POST /auth/register
   | POST /auth/login
   v
FastAPI Auth Routes
   |
   +--> PostgreSQL: users (email, password_hash)
   |
   +--> JWT access token (stateless) or session record (optional)
   |
   v
Protected routes (/uploads, /media)
   |
   +--> Authorization: Bearer <token>
```

## Build scope

- Replace `POST /auth/session` with explicit auth endpoints:
  - `POST /auth/register` — create user with email + password
  - `POST /auth/login` — verify credentials and return access token
  - `POST /auth/logout` — invalidate session or document client-side token discard
  - `GET /auth/me` — return the current authenticated user
- Extend the `users` table:
  - `password_hash`
  - `updated_at` if not already present
- Add password hashing (for example `bcrypt` or `argon2`).
- Issue signed JWT access tokens with expiry.
- Add settings for auth secrets and token lifetime:
  - `JWT_SECRET`
  - `JWT_ALGORITHM`
  - `JWT_EXPIRE_MINUTES`
- Update `get_current_user()` to validate JWT instead of raw `user_id`.
- Return proper HTTP status codes:
  - `409` when registering an existing email
  - `401` for invalid login or missing/invalid token
- Remove or deprecate the Sprint 01 `POST /auth/session` placeholder.
- Add Alembic migration for auth-related schema changes.
- Add unit and integration tests for register, login, logout, and protected routes.
- Document auth flow in the root `README.md` with `curl` examples.

## API contract (target)

### Register

`POST /auth/register`

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

### Login

`POST /auth/login`

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user_id": "uuid"
}
```

### Authenticated requests

```http
Authorization: Bearer <jwt>
```

## AWS topics prepared

| Topic | How this sprint prepares it |
| --- | --- |
| ECS Fargate | API validates auth the same way locally and in AWS. |
| RDS PostgreSQL | User credentials live in the same metadata database. |
| IAM | Keeps user auth in the application layer before AWS service auth. |
| Secrets Manager | JWT secret can move to AWS secrets in a later sprint. |
| ALB | Public API endpoints remain stateless behind the load balancer. |

## Acceptance checks

- New user can register with email and password.
- Duplicate registration returns `409`.
- Login with valid credentials returns a JWT.
- Login with invalid credentials returns `401`.
- Protected endpoints reject missing or invalid tokens.
- `GET /auth/me` returns the logged-in user.
- Logout behavior is documented and tested (server-side or client-side).
- Integration tests cover register → login → upload → list media.
- Sprint 01 placeholder session endpoint is removed or replaced.

## Portfolio proof

Show:

- `curl` examples for register and login
- JWT used on `POST /uploads` and `GET /media`
- database row with `password_hash` (never plain text)
- test output for auth and protected-route flows

## Result

The API has production-style authentication. Every later sprint can rely on real
user identity instead of the Sprint 01 session placeholder.
