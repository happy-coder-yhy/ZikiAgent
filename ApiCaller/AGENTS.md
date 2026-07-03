# Repository Guidelines

## Project Structure & Module Organization
This repository is an early-stage Python automation project for a data collection platform driven by Apifox-defined backend APIs.

- `modules/`: primary business modules. `modules/api_caller.py` is the current entry point for wrapping platform API calls.
- `utils/`: shared request and helper utilities such as request serialization and common helpers.
- `docs/`: reference material, including Postman API description `docs/data-rbac API.openapi.json` and `docs/data-manager.openapi.json`.
- `readme.md`: project overview and current TODO list.

Keep new runtime code in `modules/` or `utils/`. Put static API references, flow notes, and screenshots under `docs/`.

## Build, Test, and Development Commands
No formal build system exists yet. Use lightweight Python checks while developing:

- `python -m py_compile modules/api_caller.py`: syntax-check a core module.
- `python -m py_compile modules/*.py utils/*.py`: quick validation before a commit.
- `python -m pytest`: run tests once a `tests/` directory is added.

If you add runnable scripts, prefer placing them in `modules/` and document the exact invocation in `readme.md`.

## Coding Style & Naming Conventions
Use Python 3 with 4-space indentation and PEP 8 naming:

- `snake_case` for functions, variables, and file names.
- `PascalCase` for classes such as `APICaller`.
- Keep modules focused: API request orchestration in `modules/`, reusable helpers in `utils/`.

Add short docstrings to public classes and functions. Avoid hardcoding secrets, base URLs, cookies, or user tokens in source files.

注释要求：
- 每个函数头需写明功能、输入/输出参数（名称、类型、含义）。
- 函数内部关键步骤建议用简洁注释说明逻辑。

## Testing Guidelines
不需要编写Mock Server进行测试，可以直接与测试用的服务平台进行交互测试：
* base_url: http://pre.zikirobo.com:30080/ 
    * organization: agent
    * username: admin
    * password: 1qaz@WSX1

当需要连续测试API请求时，显示连续两条API请求之间的间隔>2秒，且只串行测试，不连续进行测试

## Commit & Pull Request Guidelines
Git history is not available in this workspace, so use a simple, consistent convention:

- Commit format: `type: short summary` such as `feat: add dataset upload request wrapper`.
- Keep commits scoped to one workflow or module.

PRs should include a brief purpose statement, affected paths, manual verification steps, and sample request/response payloads when API behavior changes.

## Security & Configuration Tips
Treat the Postman API files in `docs/` as interface contracts, not places for runtime credentials. Store environment-specific values in local configuration files or environment variables, and keep those files out of version control.

## Think before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Complete The Tasks Listed in TODO.md
- 每次启动时，或任务结束后，先检查 TODO.md中是否还有未完成的任务
- 若存在未完成任务，继续调用TDD Skill进行功能开发
- 当出现错误时中止，等待下一步指令
