# Contributing to SmartGlass AI Agent

Thanks for your interest in improving SmartGlass AI Agent! We operate entirely through pull requests created with GitHub's web interface. This workflow keeps contributions reviewable, reproducible, and automatically validated by CI.

## 🚀 Contribution Workflow

1. **Find or create an issue.** Start from an existing issue or open a new one describing the problem, motivation, and acceptance criteria.
2. **Edit files in the browser.** Use GitHub's **Edit this file** button (or the web editor) to make your changes. GitHub will fork the repository for you if necessary.
3. **Propose changes.** Add a clear summary, include testing or validation notes, and click **Propose changes**.
4. **Open the pull request.** Review the diff, ensure the base branch is correct, and submit the PR. Each PR should focus on a single, reviewable topic.
5. **Let CI run.** Wait for the automated checks to finish. Inspect logs, generated artifacts, and previews linked from the checks page.
6. **Incorporate feedback.** Address review comments and failing checks by editing the files again through the web UI. GitHub will append commits to the same PR.
7. **Merge or hand off.** Once approvals and passing checks are in place, maintainers will merge the PR.

## ✅ Pull Request Checklist

- [ ] Issue reference or clear problem statement in the PR description
- [ ] Summary of changes and impact
- [ ] Notes on testing or validation steps (even "not applicable" if no runtime code changed)
- [ ] Screenshots or artifact links when UI or documentation rendering is affected
- [ ] Passing status checks (or documented rationale for any required override)

## 🧪 Continuous Integration

All pull requests trigger automated checks. Typical jobs include linting, documentation builds, and sample inference runs. If a job fails:

- Open the failing check to read the logs and download artifacts.
- Update your changes or configuration through the web editor.
- Re-run the job using the **Re-run** button after pushing a fix.

## 🧭 Review Expectations

- Changes are reviewed by code owners or designated maintainers (see `CODEOWNERS`).
- Reviewers aim to respond within two business days.
- Please keep discussions on the PR thread to maintain a clear audit trail.

## 📚 Additional Guidance

- Follow PEP 8 and include type hints where practical for Python changes.
- Prefer documentation updates alongside code changes when behavior or usage shifts.
- Reference reproducible steps or data sources for benchmarks and experiments.

Thank you for helping build SmartGlass AI Agent! Every contribution—no matter how small—improves the experience for future collaborators.
