# Person A – Repo lead, Database & Integration (Phase 1)

You own `sql/`, `medisentinel/` (shared code) and the repo itself: every pull request
is reviewed and merged by you.

## Done ✓

- [x] Repo set up: structure, `requirements.txt`, `pyproject.toml`, `.env.example`, `.gitignore`, README, CONTRIBUTING
- [x] Schema: 11 tables in BCNF; trigger can be the only writer of alerts; one medicine per prescription line
- [x] Login roles `ms_doctor` / `ms_pharmacist` / `ms_admin` with least-privilege grants (`sql/roles.sql`)
- [x] Shared database functions (`medisentinel/db`): transactions, per-patient lock, parameterized queries
- [x] Shared value lists (`medisentinel/constants.py`)
- [x] Automated tests (`tests/test_db.py`) and setup checker (`tools/check_setup.py`)
- [x] **Week 6 deliverable: [NORMALIZATION.md](../NORMALIZATION.md)**. Read it through, then print it for the manual
- [x] Pushed to https://github.com/Rishi799/MediSentinel

## To do

### Day 1
- [ ] GitHub → *Settings → Branches*: protect `main` (require a pull request). If that needs GitHub Pro,
      get it free with the GitHub Student Developer Pack, or agree as a team: no direct pushes to `main`.
- [ ] Check both teammates accepted the invite, and help each one until `python tools/check_setup.py`
      says *All good* (most problems: PostgreSQL password, `roles.sql` not run, MongoDB service stopped).
- [ ] Review and merge pull requests as they arrive (checklist below).
- [ ] 18:00 sync: everyone pulls `main` and runs the app once.

### Day 2
- [ ] Merge order: B's medication loader before the demo data; C's validation before C's forms.
- [ ] **Integration**: on a fresh `git pull`, run setup → `load_openfda.py` → `load_medications.py`
      → `generate_synthetic.py` → `streamlit run app/Home.py`, and fix anything that breaks between the parts.
- [ ] Lead the demo rehearsal (script in [PHASE1_SPRINT.md](../PHASE1_SPRINT.md)).
- [ ] Tag the release: `git tag v1-partial-demo && git push origin v1-partial-demo`.

## Reviewing a pull request

On GitHub open the pull request → **Files changed**. Before you approve:

1. To try it locally: `git fetch origin` → `git checkout <branch>` → `python -m pytest` → run their script/page.
2. Check:
   - [ ] tests pass and new functions have tests
   - [ ] no `.env`, passwords, `.venv/` or downloaded data in the files
   - [ ] only their own folder changed (`ingestion/` for B, `app/` for C)
   - [ ] SQL uses parameters (`%s`), never f-strings with user input
   - [ ] it does what the task sheet asks
3. **Approve** → **Squash and merge** (one tidy commit per task), then delete the branch.
   If something needs fixing, leave a comment instead; they push fixes to the same branch.
