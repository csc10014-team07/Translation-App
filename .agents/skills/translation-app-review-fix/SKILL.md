---
name: translation-app-review-fix
description: Review and fix bugs in the Translation-App repo (FastAPI backend with PhoASR, TranslateGemma via llama-cpp-python and Pocket TTS, plus an Expo/React Native mobile client). Use this skill whenever the user asks to review, audit, check, debug, fix or "self-review" anything in this repo, or pastes an error log or a code-review list from it, even if they do not say "skill". Enforces a read-only audit first, evidence for every claim, one small fix at a time, and honest reporting of what was NOT run.
---

# Translation-App: self-review and fix

Work in this order. Do not skip steps. Report to the user in Vietnamese.

## Hard rules
- No subagents. Edit files directly.
- Evidence first. Every finding needs `file:line` and a short quote you actually read. Never state a library API, model filename, prompt template or version from memory. If you cannot verify it, write "cannot verify", stop that item, and continue with the next.
- Never claim something works unless you ran a check and saw it pass. If the machine has no GPU or no model files, write "not run: <reason>".
- Stay in scope. Fix only the items the user approved. Do not refactor, rename, reformat, or add features.
- Do not delete working code before its replacement is verified. Prefer adding the new path next to the old one.
- Decisions already made by the team (do not reopen): no Dockerfile, no SettingsScreen or extra tabs, one TranslationScreen with VoiceCloningPanel inside, no TTS for Vietnamese, voice input only when the source is Vietnamese.
- Git: `git add` only the files you changed (never `git add .`; the repo has untracked files such as audit_report.md and graphify-out/). One small commit per fix. Never run `git reset --hard`, `git clean`, `git push --force`, or delete branches without explicit approval.
- Never print or commit secrets, tokens, or `.env` contents. Never commit files under `backend/models/` or any `*.gguf`.
- Do not edit tests only to make them pass. Do not silence type errors with `any` or `# type: ignore` unless you explain why.

## Step 1: Orient (read-only)
Run and read: `git status --short`, `git log --oneline -5`, `ls backend/app/api/routes`, then `grep -rniE "rapidocr|edge_tts|stream" backend --include=*.py --include=*.txt`. The repo changes quickly; do not assume the code matches older notes. Read `references/known-pitfalls.md` before reviewing.

## Step 2: Audit (read-only)
Review the area the user named (or the whole repo if none). For each suspected bug, record: id, file:line, what is wrong, how you verified it, severity, and proposed fix. Severity means impact on a user running the app, not how the code looks:
- HIGH: crash, wrong output, data loss, or feature unusable
- MEDIUM: works but fails in common cases or leaks resources
- LOW: style, naming, dead code

Classify each finding: `confirmed` (you reproduced it or the code plainly shows it), `likely` (reasoning only), or `cannot verify`. Do not fix `likely` or `cannot verify` items; list them for the user.

Check these layers in order and stop widening the audit once you have enough for the user to decide: (1) imports and syntax, (2) route to adapter wiring and request/response fields shared with `mobile/src/services/api.ts`, (3) concurrency and resource handling, (4) mobile types and runtime props, (5) config and git hygiene.

## Step 3: Ask
Show the findings table and ask which items to fix. Include a "needs your decision" list for product choices (examples: keep or drop edge_tts, OCR approach, conversation-history feature). Wait for the answer. If the user already approved a specific list, skip this step and say so.

## Step 4: Fix, one item at a time
For each approved item:
1. Re-read the exact lines right before editing (files may have changed).
2. Make the smallest change that fixes the confirmed cause. State the cause in one sentence.
3. Run the checks that apply:
   - Python syntax: `python -m compileall backend/app backend/scripts`
   - Tests, if a `tests/` folder exists: `cd backend && pytest -q`
   - Types: `cd mobile && npx tsc --noEmit`
   - Server smoke test, only if dependencies and models are present: start `uvicorn app.main:app --port 8000` from `backend/`, call the affected route with `curl`, then stop the server.
4. If a check fails, fix your own change or revert it (`git checkout -- <file>` for files you changed). Do not pile further edits on a red state.
5. Commit with a message of the form `fix(<area>): <what and why>`.

## Step 5: Report
Use this exact structure:

```
Đã sửa:
- <id> <file:line> — nguyên nhân, cách sửa, kiểm tra đã chạy (lệnh + kết quả)
Chưa sửa (cần bạn quyết định):
- <id> — lý do
Chưa chạy thử:
- <điều gì> — vì sao (không có GPU / chưa có model / chưa có node_modules ...)
Không xác minh được:
- <điều gì> — cần thông tin gì
Việc nên làm tiếp: <tối đa 3 mục>
```
Do not add praise or a summary of effort. If every check passed, say which ones, not "all good".