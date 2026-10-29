# Contributing

Thanks for helping. This is a small personal project maintained on a best-effort basis, so please read this first.

## What's welcome

- **Bug reports**: a skill told an agent to do something wrong, unsafe or outdated. Include the agent and model you used, what you asked, and what happened.
- **Fact fixes**: a product, tool or platform claim that's out of date, with a link to the current source.
- **Small, focused PRs** that fix one of the above.

For anything larger (a new skill, a new section, a change in a skill's approach), open an issue first so we can agree it fits before you spend time on it.

## What usually gets declined

- Adding general advice the model already follows without being told. Skills stay useful by staying short.
- Turning a recommended default into a mandatory step.
- Tool- or vendor-specific instructions without a fallback for agents that lack them.

A "no" here is about scope, not about you or the quality of the idea.

## AI-assisted contributions

AI assistance is welcome. These skills were written with it. In return:

- Say in the PR how AI was used (the PR template asks).
- You must understand, and be able to explain, every line you submit. Unreviewed generated PRs will be closed.
- PRs opened by autonomous agents without a human behind them will be closed.
- Don't add `Signed-off-by` on someone else's behalf.

## Making a change

1. Edit the skill under `skills/<name>/SKILL.md`, and its `references/` files if it has them.
2. Run the checks:

   ```sh
   python3 scripts/validate_skills.py
   python3 -m unittest discover -s tests
   ```

3. For a behavior change, bump the plugin `version` in `.claude-plugin/marketplace.json` and add an entry under "Unreleased" in `CHANGELOG.md`.
4. Open a PR describing what an agent will now do differently, and why.

Contributions are accepted under the project's [MIT license](LICENSE).
