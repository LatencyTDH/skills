---
name: agent-readiness
description: Framework for evaluating and improving how well a codebase supports autonomous AI development. Use when assessing repository readiness for AI agents, identifying gaps in tooling/documentation/testing, or recommending improvements to make codebases more agent-friendly. Triggers on requests to evaluate agent readiness, improve codebase quality for AI, or assess repository maturity for autonomous development.
---

# Agent Readiness

Evaluate how well a codebase supports autonomous AI development across eight technical pillars and five maturity levels.

## Core Concept

Agent performance problems are often environment problems, not model problems. Missing pre-commit hooks mean waiting minutes for CI feedback instead of seconds. Undocumented environment variables cause guess-and-fail loops. Build processes requiring tribal knowledge block agents entirely.

A codebase with fast feedback loops and clear instructions makes any agent dramatically more effective.

## Eight Technical Pillars

Each pillar addresses a specific failure mode in autonomous development.

### 1. Style & Validation
Linters, type checkers, formatters (ESLint, Biome, TypeScript strict mode, Prettier, Black).
**Without this:** Agent submits code with formatting issues, waits for CI, fixes blindly, repeats.

### 2. Build System
Reproducible builds, clear build commands, dependency management.
**Without this:** Agent cannot verify builds work or understand build failures.

### 3. Testing
Unit tests, integration tests, E2E tests, test runners configured.
**Without this:** Agent cannot verify changes work or detect regressions.

### 4. Documentation
README, CONTRIBUTING, API docs, architecture docs, AGENTS.md.
**Without this:** Agent lacks context for design decisions and conventions.

### 5. Dev Environment
Setup scripts, dev containers, environment variable documentation.
**Without this:** Agent cannot reliably set up or understand the environment.

### 6. Code Quality
Code review processes, CODEOWNERS, branch protection.
**Without this:** Agent changes may bypass quality gates or lack review.

### 7. Observability
Logging, monitoring, error tracking configuration.
**Without this:** Agent cannot diagnose production issues or understand system behavior.

### 8. Security & Governance
Security scanning, dependency auditing, secrets management.
**Without this:** Agent may introduce vulnerabilities or expose secrets.

## Five Maturity Levels

### Level 1: Functional
Basic development possible. Code runs, minimal tooling.

### Level 2: Documented
README exists, basic setup documented, some tests present.

### Level 3: Standardized (Target)
Production-ready for agents. Clear processes defined and enforced. E2E tests exist, docs maintained, security scanning, observability.
**Agent capability:** Routine maintenance—bug fixes, tests, docs, dependency upgrades.

### Level 4: Optimized
Comprehensive CI/CD, extensive testing, thorough documentation, proactive security.
**Agent capability:** Feature development with minimal guidance.

### Level 5: Autonomous
Self-documenting, self-healing, comprehensive automation.
**Agent capability:** Independent feature development and system improvements.

## Evaluation Process

1. **Assess each pillar** - Check for presence and quality of tooling/configuration
2. **Identify gaps** - Note missing or weak areas
3. **Determine maturity level** - Match current state to level definitions
4. **Prioritize improvements** - Focus on highest-impact gaps first

### Key Signals to Check

| Pillar | Key Signals |
|--------|-------------|
| Style & Validation | Linter config, type checking enabled, formatter config, pre-commit hooks |
| Build System | Build scripts documented, CI pipeline exists, dependency lockfile |
| Testing | Test files exist, test command documented, CI runs tests |
| Documentation | README with setup, CONTRIBUTING guide, API docs, architecture docs |
| Dev Environment | Setup script or dev container, .env.example, documented dependencies |
| Code Quality | CODEOWNERS file, branch protection, PR template |
| Observability | Logging configured, error tracking, monitoring setup |
| Security | Security scanning in CI, dependency auditing, secrets not in code |

## Scoring

- Each criterion is binary: pass or fail
- To unlock a level: pass 80% of criteria from that level and all previous levels
- Monorepos: evaluate per-application where applicable

## Recommendations Format

When reporting findings, structure as:

```
## Current Level: [1-5]

### Passing Criteria
- [List what's working well]

### Gaps (Priority Order)
1. [Highest impact gap] - [Why it matters] - [How to fix]
2. [Next gap]...

### Quick Wins
- [Easy fixes that improve agent effectiveness]
```

## Common Quick Wins

1. **Add pre-commit hooks** - Instant feedback vs. CI wait
2. **Document environment variables** - Create .env.example
3. **Add AGENTS.md** - Agent-specific guidance and conventions
4. **Enable strict type checking** - Catch errors earlier
5. **Add test command to README** - Clear verification path
