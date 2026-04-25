# Security and Secrets

## No Secrets in This Repository

This repository must never contain:
- API keys or tokens
- Database passwords (except localhost defaults in docker-compose.yml)
- AWS credentials
- Private keys or certificates
- OAuth client secrets
- Any credential that grants access to external systems

## Local Development Credentials

The Docker Compose stack uses these hardcoded values for **local development only**:

| Service | Credential | Value | Scope |
|---|---|---|---|
| PostgreSQL | User/password | `authplatform/authplatform` | localhost:5432 only |
| LocalStack | AWS keys | `test/test` | localhost:4566 only |
| pgAdmin | Admin email | `admin@authplatform.local` | localhost:5050 only |

These values exist in `docker-compose.yml` and `.env.example`. They provide no access
to any real system. They are safe to commit because LocalStack and local Postgres
accept any credentials.

## Production Credentials

When deploying to AWS:
- Use AWS Secrets Manager or Parameter Store for database credentials
- Use IAM roles for S3/SQS/SageMaker access (no static keys)
- Use environment variables injected by ECS task definitions
- Never hardcode production credentials in source code
- Rotate credentials on a schedule

## What to Check Before Committing

- [ ] No `.env` files (gitignored)
- [ ] No `*.pem`, `*.key`, `*.p12` files (gitignored)
- [ ] No AWS access key IDs or secret keys in source code
- [ ] No database connection strings pointing to real hosts
- [ ] No API tokens or bearer tokens in scripts
- [ ] `docker-compose.yml` only references localhost services

## If a Secret Is Accidentally Committed

1. Do NOT just delete it in a new commit — it remains in git history
2. Rotate the compromised credential immediately
3. Use `git filter-branch` or BFG Repo Cleaner to remove from history
4. Force-push the cleaned history
5. Notify the team
