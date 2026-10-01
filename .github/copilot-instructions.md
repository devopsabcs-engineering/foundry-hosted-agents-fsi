---
title: Copilot Repository Instructions
description: Repository-wide Git workflow requirements for GitHub Copilot
---

## Feature branch workflow

* Treat `main` as a protected branch. Use it only for read-only analysis.
* Before modifying any file, run `git branch --show-current` to confirm the
  active branch.
* If the active branch is `main`, create and switch to a branch named
  `feature/<short-kebab-case-description>` before the first edit.
* If uncommitted changes already exist on `main`, preserve them when creating
  the feature branch. Never reset, discard, or overwrite them.
* Continue on the current branch only when its name starts with `feature/`.
  Otherwise, create a new `feature/` branch before editing.
* Never commit, push, merge, or rebase development changes directly onto
  `main`.
* Deliver changes through a pull request from the feature branch into `main`
  so that required validation workflows can run.
* Do not commit, push, merge, or create a pull request unless the user asks for
  that operation explicitly.
* An exception to this workflow requires an explicit user instruction that
  names the branch and the operation to perform.