# Security policy

These skills are instructions that coding agents follow, often with shell access and the user's GitHub identity. A flaw here can make an agent do something harmful, so security reports are taken seriously.

## What counts as a vulnerability

- Wording that could lead an agent to leak secrets, run untrusted code, publish, merge or change settings without the user's explicit approval.
- Gaps that let text from issues, PRs, web pages or other repos steer an agent (prompt injection).
- Unsafe CI or release guidance (for example, workflow triggers that expose secrets to forks).

## How to report

Please **don't open a public issue**. Report privately through GitHub's [private vulnerability reporting](https://github.com/milesradford99/agent-skills/security/advisories/new).

Include the skill, the passage, and a scenario showing what an agent could be led to do.

This is a personal project, so responses are best effort. I aim to acknowledge reports within a week. Fixes ship as a new version noted in the [CHANGELOG](CHANGELOG.md), with credit if you'd like it.

## Supported versions

Only the latest release is supported.
