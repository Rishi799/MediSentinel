# How we work in this repo

Repo lead: **Person A** (reviews and merges every pull request).
Your tasks: [Person B](docs/tasks/PERSON_B.md) · [Person C](docs/tasks/PERSON_C.md) · [Person A](docs/tasks/PERSON_A.md)

## First time

1. Accept the collaborator invite (GitHub email / notifications).
2. Follow **Setup** in the [README](README.md) until `python tools/check_setup.py` says *All good*
   and `python -m pytest` passes.

## For every task

```bash
git checkout main
git pull                              # start from the latest main
git checkout -b feature/<task-name>   # e.g. feature/openfda-ingestion

# ... write code, run it, test it ...
python -m pytest                      # everything must still pass

git add <the files you changed>
git commit -m "Add openFDA label loader"
git push -u origin feature/<task-name>
```

Then on GitHub: **Compare & pull request** → write what you did and how to test it →
**Create pull request**. Person A reviews; fix any comments by committing to the same
branch and pushing again. After it is merged, go back to the top for the next task.

If `main` changed while you were working: `git checkout feature/<task-name>`, then
`git merge main` (or ask Person A for help with conflicts).

## Rules

- **Never push to `main` directly**; always a pull request.
- **Stay in your own folders** (Person B: `ingestion/`; Person C: `app/`). Need something in
  `medisentinel/db/` or `sql/`? Ask Person A; those files are shared by everyone.
- **Never commit** `.env`, passwords, the `.venv/` folder or downloaded data (`data/`).
- Keep pull requests small: one task per pull request.
- Write a test for every function you add (in `tests/`).
- Commit messages say what changed: "Add patient form validation", not "update".
