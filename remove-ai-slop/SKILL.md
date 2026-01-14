---
name: remove-ai-slop
description: Remove code slop. Use when cleaning up AI-generated code.
---

Check the changes you've made in this session, and remove all AI generated slop introduced.

This includes:

- Extra comments that a human wouldn't add or is inconsistent with the rest of the file (useful doc comments are good to keep)
- Extra defensive checks or try/catch blocks that are abnormal for that area of the codebase (especially if called by trusted / validated codepaths)
- Casts to any to get around type issues
- Variables that are only used a single time right after declaration, preferring inlining the rhs (if inlining isn't too messy).
- Any other style that is inconsistent with the file

Report at the end with only a 1-3 sentence summary of what you changed
