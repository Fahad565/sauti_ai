# Deployment Issues

## ISSUE-001: GitHub Push Protection — Twilio Secret in `.env.example`

**Status:** ✅ RESOLVED  
**Date reported:** 2026-07-30  
**Date resolved:** 2026-07-30

### Problem

`git push origin feature/rag-multi-agent` was rejected by GitHub Push
Protection (GH013) because two commits contained a real Twilio Account SID
and Auth Token in `.env.example`:

- `TWILIO_ACCOUNT_SID=AC2fab...` (line 44)
- `TWILIO_AUTH_TOKEN=31281f...` (line 45)

GitHub flagged these as a **Twilio Account String Identifier** secret leak.

### Root Cause

Real Twilio credentials were accidentally committed to `.env.example`
instead of placeholder/empty values. Even though a later commit blanked
them out, the secrets persisted in the git history, which GitHub scans.

### Resolution

1. **Rewrote branch history** with `git filter-branch --tree-filter` on
   all 4 commits (`bbd6c27..HEAD`) to replace the real credentials with
   empty values in every version of `.env.example`.
2. **Purged old refs and objects** — deleted `refs/original/` backup refs,
   expired the reflog, and ran `git gc --prune=now --aggressive` to remove
   the old commit objects entirely from the local repo.
3. **Fixed `.gitignore`** — `.env.example` was incorrectly listed in
   `.gitignore`; changed to `!.env.example` so the template file is always
   tracked (the `!` negation ensures it is not ignored even though `.env`
   is ignored).
4. **Verified** — confirmed all 4 rewritten commits contain no secrets
   via `git show <hash>:.env.example | grep`.

### Prevention

- `.env.example` should only ever contain **empty** or **placeholder**
  values (e.g. `TWILIO_ACCOUNT_SID=your_account_sid_here`).
- Real secrets belong in `.env` (which is git-ignored).
- Consider using `git-secrets` or a pre-commit hook to catch secrets
  before they are committed.

### Next Step

Push the rewritten branch:

```bash
git push origin feature/rag-multi-agent
```

Since the branch was never successfully pushed, no `--force` is needed.