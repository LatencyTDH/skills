# Claude Skills

A collection of reusable skills and knowledge bases for Claude AI assistants. Each skill is a focused set of guidelines, principles, or domain expertise that can be referenced when building applications or solving problems.

## What are Skills?

Skills are markdown documents that contain structured knowledge, best practices, and guidelines for specific domains. They help maintain consistency and quality across projects by codifying important principles and patterns.

## Available Skills

| Skill | Description |
|-------|-------------|
| [design-principles](./design-principles/SKILL.md) | Minimal design system inspired by Linear, Notion, and Stripe. |
| [humanizer](./humanizer/SKILL.md) | Remove signs of AI-generated writing from text. |
| [lyft-receipts](./lyft-receipts/SKILL.md) | Fetch Lyft ride history and receipts via web session cookies. |
| [remove-ai-slop](./remove-ai-slop/SKILL.md) | Strip AI filler words and phrases from responses. |
| [skill-creator](./skill-creator/SKILL.md) | Guide for creating new skills. |
| [uber-receipts](./uber-receipts/SKILL.md) | Fetch Uber ride history and trip data via web session cookies. |

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
