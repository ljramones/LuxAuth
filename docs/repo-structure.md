# Repository Structure

```text
luxuryAuthentication/
│
├── README.md                    Root README
├── CLAUDE.md                    Claude Code guidance
├── .gitignore                   Root gitignore
├── ConceptOfOperation.md        Product/technical concept (whole system)
│
├── docs/
│   ├── repo-structure.md        This file
│   ├── roadmap.md               Development roadmap
│   ├── security-and-secrets.md  Secrets management policy
│   ├── operations/
│   │   ├── microscope-acceptance-runbook.md
│   │   ├── first-real-capture-checklist.md
│   │   └── capture-quality-guide.md
│   └── templates/
│       ├── capture-manifest-template.yaml
│       └── capture-session-metadata-template.yaml
│
├── auth-platform/               Backend (services, ML, data governance)
│   ├── README.md
│   ├── Makefile
│   ├── docker-compose.yml
│   ├── services/                13 FastAPI microservices
│   ├── libs/auth_common/        Shared Python library
│   ├── ml/                      Metric-learning training
│   ├── infra/                   Postgres/LocalStack init
│   ├── scripts/                 CLI tools and smoke tests
│   ├── sample_data/             Synthetic test images
│   └── docs/
│       ├── OverallSystemDesign.md
│       ├── targetArchitecture.md
│       ├── auth-platform-real-testing-readiness-plan.md
│       ├── architecture/        Backend architecture docs
│       └── operations/          Backend-specific ops docs
│
├── iphone-app/                  Future iPhone capture client
│   └── README.md
│
└── android-app/                 Future Android capture client
    └── README.md
```

## Boundary Rules

| Content | Location | Reason |
|---|---|---|
| Backend services, ML, DB schema | `auth-platform/` | Backend-only |
| Backend architecture decisions | `auth-platform/docs/architecture/` | Backend-only |
| Backend batch workflow docs | `auth-platform/docs/operations/` | Backend-only |
| Microscope setup, capture quality | `docs/operations/` | Crosses backend + client boundary |
| Manifest/session templates | `docs/templates/` | Used by backend scripts + future clients |
| Product concept, roadmap | `docs/` or root | Whole-system scope |
| iPhone app code | `iphone-app/` | Client-only |
| Android app code | `android-app/` | Client-only |

The backend does not depend on the mobile apps. The mobile apps depend on the backend APIs.
