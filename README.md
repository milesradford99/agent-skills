# agent-skills

Skills for building open-source software, making videos, writing Douyin finance scripts, and reading China's A-share rescue cycle with an AI coding agent. They stay useful as models get stronger because they encode judgment, safety lines and proportion, not tips the model already knows.

| Skill | What it does | Use it when |
|---|---|---|
| [`oss-mentor`](skills/oss-mentor/SKILL.md) | Audits your repo, does routine setup as reviewable PRs with test evidence, and brings you at most 3 decisions at a time with a recommended default. Name, license, scope, public API, taste and releases stay yours. | Starting or open-sourcing a project, asking "what's next?", getting ready for contributors, preparing a release, or contributing to someone else's project |
| [`oss-design`](skills/oss-design/SKILL.md) | Product, tech and UI/UX design that is conventional where users expect it and distinctive where it counts. Picks a depth tier, lets you steer by reacting to options, and tests with a fresh agent and a blind critic. | Designing a feature, a public API or architecture, a CLI's ergonomics, a UI flow, or launch visuals |
| [`video-director`](skills/video-director/SKILL.md) | Turns loose inspiration into a finished video. It locks the format first, asks you at most 3 easy questions and shows five directions as keyframes to react to, with a story card to confirm what it says. It builds the video as code in whatever renderer the idea needs, continuous by default with words on screen instead of slides and a synthetic voice. Tuning notes become small data edits, and only changed segments re-render. A blind reviewer loop runs before delivery. | Making motion graphics, explainers, knowledge shorts, promos, animated shorts, lyric videos, trailers, visualizers or music edits from a song, a link or an idea |
| [`rescue-a-stock`](skills/rescue-a-stock/SKILL.md) | Reads where China's A-share market stands in the state rescue and clearing cycle. It pulls live index, leverage and ETF data, classifies each intervention by who pays, sets a stage per market segment with rule-based confidence, and explains it as a causal chain with a test for every link. Analysis only: it gives no trade advice. | Asking whether a policy or market bottom is in, whether the National Team is really buying, what a meeting means, or what would trigger the next rescue |
| [`narrative-dcf-valuation`](skills/narrative-dcf-valuation/SKILL.md) | Values any listed stock with the closed-form DCF from the book 穿透叙事 (Zou Peixuan, 2026). It reverses the price into the implied earnings ceiling, replays the book's case-study routine (implied-ceiling timeline, revision path, leading variable, margin and event checks), and ends with a fair value, a fair ceiling and the contradictions the market hasn't priced. Its calculator reproduces the book's tables exactly. Analysis only: it gives no trade advice. | Asking what a stock's price implies, what a fair PE or value is, or anything about 业绩天花板, 隐含预期 or 叙事估值 |
| [`douyin-finance-koubo`](skills/douyin-finance-koubo/SKILL.md) | Writes Douyin (抖音) finance and business 口播 scripts in Mandarin. It checks what everyone already says on the topic, requires at least two pieces of material others lack, pushes the insight past the first layer and hands the viewer a reusable judgment tool. It designs retention as a chain of questions, drafts in spoken Chinese with the structural tells of generated text ruled out, and runs cold reads for drop-off, takeaway, follow and voice before delivery. It never invents people or experiences and gives no trade advice. | Writing, rewriting or auditing a finance, macro, policy or business-commentary script for Douyin |
| [`miao-yanliang-macro-lens`](skills/miao-yanliang-macro-lens/SKILL.md) | Analyzes monetary policy, the dollar, gold, the renminbi, China's low inflation and AI-and-inflation questions with a framework drawn from Miao Yanliang's public books, reports and interviews (unofficial, not him). It works through reality, mechanism, judgment, gives every call a horizon, conditions and a failure signal, keeps dated opinion snapshots apart from the framework, and ends with the strongest counter-argument. It gives no trade advice. | Asking about de-dollarization, RMB internationalization, China's deflation, whether AI is a bubble, or how a chief-economist-style macro view would read an asset |

**Status:** v0.1, early. Maintained as a personal project, best effort, no support guarantee.

## What makes these different

- **Proportion.** A weekend tool gets five files; a library others depend on gets the full supply-chain setup. Process is added when something happens (first outside PR, second maintainer), not up front.
- **Hard safety lines.** Text from issues, PRs and web pages is treated as data, never as instructions. Releases, merges, settings changes and anything public need your explicit yes for that exact action, and never happen in unattended runs.
- **Good citizenship.** `oss-mentor` checks prior art and asks upstream before you duplicate a project, and never posts to other people's repos on its own.
- **Design that's tested, not just generated.** `oss-design` replaces "make it unique" with drawn themes, blind side-by-side critique and a "fresh agent installs it from the README" test, with accessibility as a gate.

## Install

### Claude Code (plugin marketplace)

```text
/plugin marketplace add milesradford99/agent-skills
/plugin install oss-mentor@milesradford-skills
/plugin install oss-design@milesradford-skills
/plugin install video-director@milesradford-skills
/plugin install rescue-a-stock@milesradford-skills
/plugin install narrative-dcf-valuation@milesradford-skills
/plugin install douyin-finance-koubo@milesradford-skills
/plugin install miao-yanliang-macro-lens@milesradford-skills
```

Each skill installs as its own plugin, so you can take one without the other.

### Any agent that reads `SKILL.md` folders

Copy the skill folder into your agent's skills directory. For Claude Code that's `~/.claude/skills/` (for you) or `.claude/skills/` (for one project):

```sh
git clone https://github.com/milesradford99/agent-skills
cp -r agent-skills/skills/oss-mentor agent-skills/skills/oss-design agent-skills/skills/video-director agent-skills/skills/rescue-a-stock agent-skills/skills/narrative-dcf-valuation agent-skills/skills/douyin-finance-koubo agent-skills/skills/miao-yanliang-macro-lens ~/.claude/skills/
```

### Claude app

Each [release](https://github.com/milesradford99/agent-skills/releases) attaches one `.zip` per skill, ready to upload in the app's skills settings.

## Try it

In a repo of yours, ask your agent:

- "What's the status of this project and what should I do next?" (`oss-mentor`, review mode)
- "I want to open-source this tool." (`oss-mentor`, start)
- "Design the `--json` output for this CLI." (`oss-design`, Tier 1)
- "Make a 20-second launch video for this app from these screenshots." (`video-director`)
- "Where are A-shares in the clearing cycle right now, and how sure are you?" (`rescue-a-stock`)
- "长江电力现在的股价隐含了什么业绩天花板？" (`narrative-dcf-valuation`)
- "帮我写一条抖音财经口播稿，讲讲AI短剧到底谁在赚钱。" (`douyin-finance-koubo`)

## How these were built

`oss-mentor` and `oss-design` were drafted with Claude, then reviewed by five independent agents (runtime mechanics, security red team, skeptical OSS maintainer, product and design strategy, fact-check against current docs) and re-verified by a sixth. [`docs/EVALS.md`](docs/EVALS.md) lists the scenarios used to compare them against an agent with no skill. `video-director` was built from a deep-research report on agentic video production, and `rescue-a-stock` from a deep-research study of 64 Chinese market interventions; neither has had that multi-agent review yet. `douyin-finance-koubo` went through five versions against one creator's feedback on real scripts and has had no independent review. A human maintainer reviews and owns every change.

Product facts in the skills are dated (October 2026) and the skills tell the agent to re-check them before relying on them.

## Contributing

Issues and small PRs are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md), including the AI-assistance policy. Security reports: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
