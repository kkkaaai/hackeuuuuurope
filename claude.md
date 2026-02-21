Workflow Orchestration

1. Plan Mode Default
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions).
- If something goes sideways, stop and re-plan immediately — don’t push forward blindly.
- Use plan mode for verification steps, not just building.
- Write detailed specs upfront to reduce ambiguity.

2. Subagent Strategy
- Use subagents liberally to keep the main context window clean.
- Offload research, exploration, and parallel analysis to subagents.
- For complex problems, throw more compute at it via subagents.
- One task per subagent for focused execution.

3. Self-Improvement Loop
- After any correction from the user, update tasks/lessons.md with the pattern.
- Write rules for yourself that prevent repeating the same mistake.
- Ruthlessly iterate on these lessons until the mistake rate drops.
- Review relevant lessons at the start of each session.

4. Verification Before Done
- Never mark a task complete without proving it works.
- Diff your behavior between main and your changes when relevant.
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, and demonstrate correctness.

5. Demand Elegance (Balanced)
- For non-trivial changes, pause and ask: "Is there a more elegant way?"
- If a fix feels hacky: Knowing everything I know now, implement the elegant solution.
- Skip this for simple, obvious fixes — don’t over-engineer.

6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don’t ask for hand-holding.
- Point at logs, errors, and failing tests — then resolve them.
- Fix failing CI tests without being told how.

7. Task Management
- Plan First — Write a plan to tasks/todo.md with checkable items.
- Verify Plan — Check in before starting implementation.
- Track Progress — Mark items complete as you go.
- Explain Changes — Provide a high-level summary at each step.
- Document Results — Add a review section to tasks/todo.md.
- Capture Lessons — Update tasks/lessons.md after corrections.

8. Core Principles
- Simplicity First: Make every change as simple as possible. Minimal code impact.
- No Laziness: Find root causes. No temporary fixes. Senior developer standards.
- Minimal Impact: Touch only what’s necessary. Avoid introducing bugs.

