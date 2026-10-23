# One repository, four member branches, one integration coordinator

## Bootstrap once

Arya creates/receives the repository and commits this starter as a reviewed base on main. No remote is assumed and no remote push was performed by generating this package. Replace `<repo-url>` with the actual shared repository URL.

Each member:
```sh
git clone <repo-url>
cd <repository-folder>
git switch main
git pull --ff-only origin main
git switch -c team/arya   # use your own member name
```
Create all four member branches from the same agreed base commit. Never overwrite an existing repository with the ZIP without reviewing the difference.

## Agreed synchronization strategy: MERGE main into member branches

Before a new work block and before review:
```sh
git status                 # commit or deliberately stash local edits first
git fetch origin
git switch team/arya      # your branch
git merge origin/main
# Resolve conflicts with relevant file owners; run tests.
git add <resolved-files>
git commit                # only if conflict resolution requires the merge commit
git push -u origin team/arya
```
If there is no conflict Git may make the merge commit itself; do not create an empty extra commit. Do not rebase or force-push shared branches in this agreed workflow. Use `git merge --abort` if a conflict needs owner discussion; do not blindly choose ours/theirs.

## Small pull requests, not one final integration day

Make story-focused commits such as `BB-05: add allowlisted audit event model`. Push and open a small PR from your team branch to main. Avoid mixing unready stories into a PR; a long-lived member branch's PR contains all unmerged commits. Finish one reviewable change at a time, or agree short-lived feature branches with Arya if simultaneous work is necessary.

Arya reviews other members' PRs; another teammate reviews Arya's own code. Arya retains final merge responsibility. Use ordinary merge commits (not repeated squash/rebase merges) for these long-lived branches; after merge, merge current main back into each member branch. This avoids re-presenting already merged history. Run checks again after conflict resolution.

The review should verify contract/schema approval, actual tests, synthetic fixtures, known defects and post-merge integration. Arya does not silently finish rejected/incomplete member work.

## Suggested protection after CI approval

Require a PR and at least one independent approval for main; prevent force pushes/deletion; require resolved conversations and approved checks. The delivered workflow is MANUAL until D-06 is approved. Enable pull_request (and optionally push on main) triggers, run them and then make the actual named checks required. Do not require an unconfigured or never-triggered status.

Protected branch settings are recommendations, not settings this ZIP has applied. Main should always start and pass agreed smoke tests.
