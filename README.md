# Claude Skills

A collection of reusable skills and knowledge bases for Claude AI assistants. Each skill is a focused set of guidelines, principles, or domain expertise that can be referenced when building applications or solving problems.

## What are Skills?

Skills are markdown documents that contain structured knowledge, best practices, and guidelines for specific domains. They help maintain consistency and quality across projects by codifying important principles and patterns.

## Available Skills

### 🎨 [Design Principles](./design-principles/SKILL.md)

Enforces precise, minimal design system inspired by Linear, Notion, and Stripe. Use this skill when building dashboards, admin interfaces, or any UI that needs Jony Ive-level precision - clean, modern, minimalist with taste. Every pixel matters.

**Key Topics:**
- Design direction and personality selection
- 4px grid system and spacing
- Typography hierarchy
- Depth and elevation strategies
- Color systems and contrast
- Dark mode considerations
- Anti-patterns to avoid

## Structure

Each skill follows a consistent structure:

```
skill-name/
  └── SKILL.md
```

Skills use frontmatter metadata:

```yaml
---
name: skill-name
description: Brief description of what this skill covers
---
```

## Usage

These skills are designed to be referenced by Claude AI assistants when working on relevant projects. They provide context-aware guidance and ensure consistent application of best practices.

## Contributing

To add a new skill:

1. Create a new directory named after your skill
2. Add a `SKILL.md` file with frontmatter metadata
3. Document the skill's principles, guidelines, and best practices
4. Follow the existing structure and formatting conventions

## License

This repository contains skills and knowledge bases for use with Claude AI assistants.
