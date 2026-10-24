---
name: "oss-design"
description: "Proportional product, tech and UI/UX design for software projects, aimed at work that is useful first and distinctive where it counts. Picks a depth tier, generates genuinely different options, lets the user steer by reacting, tests with a fresh agent and a blind critic, and subtracts what doesn't earn its place. Use when designing a feature, a public API or architecture, a CLI's ergonomics, a UI screen or flow, or launch visuals. Works standalone or alongside oss-mentor; for a brand-new idea, wait until the build-or-contribute decision is made."
---

# OSS Design

Models default to the most predictable answer at every step. This skill does two things about that. It keeps the predictable answer wherever users expect convention, and pushes past it only where distinctiveness pays. The user steers by reacting to concrete options. You generate, test and subtract.

## Step 1: pick the tier

Show the tier in one line. If unsure, pick the lower tier and say so; the user can raise it.

| Tier | Examples | What runs |
|---|---|---|
| 0 | Bug fix, refactor, internal change | Nothing beyond the PR description |
| 1 | New flag, option, subcommand or endpoint; README rework; launch visuals for a project with no UI | Three-line brief (job, non-goal, check) plus a usage example or 3 options. No critic loop. |
| 2 | v0.1 core, a new public abstraction, a breaking API change, an app's first screen or flow | The matching track below: A for features, B for architecture or API, C for UI. Run more than one only when the work spans them. |

**Hobby projects** (oss-mentor's hobby profile, or a solo personal tool): the v0.1 core is Tier 1 unless the user asks for more. ADR sections beyond context, decision, alternatives and consequences are optional.

**Which techniques run at which tier:**
- **Tier 1:** broad-then-steered with 3 options, subtraction, and removing unchosen defaults. Run the fresh-agent test if the change affects the README's first five minutes.
- **Tier 2:** everything.
- **Vocabulary draws** apply to UI and identity work only, never to architecture.

**Without oss-mentor**, record taste choices and decisions in `direction.md`, the ADR or the PR description, so they aren't re-argued later.

## Step 2: convention first, then distinctiveness

**Be conventional** wherever users carry expectations from elsewhere:
- navigation, forms and docs structure;
- CLI flags: `--help`, `--version`, `--json`, exit codes, `NO_COLOR`;
- error formats and config precedence (flag > env > file).

**Be distinctive** in at most one or two places: the signature moment, and the identity (name, voice, brand). If a distinctive design slows a user's first success, it's a regression.

## Shared techniques

1. **Broad, then steered.** List headline-only options: 3 at Tier 1, 6–10 at Tier 2. The user reacts in their own words ("this, but less tacky"), and you sharpen only the picks from those reactions. Always offer "pick for me", which takes the recommendation and records why.
2. **Variety from outside the model.** Asking a model to "be unique" produces output that only sounds random. To get real variety:
   - Draw from the vocabulary below with a real RNG and build one direction on each draw. Use `shuf -n 3 -e <entries>` on Linux, or `python3 -c "import random,sys;print(random.sample(sys.argv[1:],3))" <entries>` anywhere. Record what was drawn.
   - Use cross-domain analogies only when they bring over a *mechanism*, meaning how that field solves the problem rather than how it looks. Name the mechanism in one line, or drop the analogy.
   - Include one deliberate extreme at headline depth. Develop it only if the user picks it.
3. **Fresh-agent first-success test.** For anything a user touches, start a fresh agent with only the README or the UI and give it the core job. Record time, steps, stumbles and every error message, then fix the top three. Before v0.1, suggest the user watch 1–3 real people try the quickstart. Real users beat every proxy.
4. **Blind pairwise critic** (Tier 2 only).
   - Give a fresh-context reviewer, ideally the strongest available model, only the artifacts. No code and no history.
   - Show it the current and previous versions, plus 2–3 exemplars the user likes, in random order and unlabeled.
   - Ask it two things: which version better serves the job for the user, and the top 3 defects, each with a fix.
   - Stop when the new version doesn't win, no high-severity defect remains, or after 3 rounds.
   - The critic informs and the user decides. Its taste never overrides a stated preference or a test result.
   - Exemplars are a moodboard: never copy them.
5. **Subtract.** For every element, option, flag, layer or sentence, ask what breaks or who would complain if it were removed. If the answer is "nothing" or "no one", cut it. Prefer native platform components.
6. **Remove unchosen defaults.** Cut anything present because it was the generator's first instinct rather than a decision:
   - Product and tech: over-explaining, generic names, a config option for everything, boilerplate abstractions.
   - Visual, as of 2026: stock gradients and glows, the stock centered hero, decorative blobs standing in for real imagery.
   If the user chose it, it's a decision, not a tell.

**Vocabulary** (extend it with the user's own interests):
- **Materials:** paper, enamel, felt, brushed steel, terrazzo, glass.
- **Eras:** 1970s transit signage, early web, Bauhaus, Swiss modernism, Showa-era packaging.
- **Tools:** field notebook, control panel, slide rule, tape measure, darkroom.
- **Crafts:** bookbinding, letterpress, woodblock, knitting patterns.
- **Game genres:** roguelike, city builder, puzzle box.
- **Rituals:** tea ceremony, morning newspaper, a pit stop.
- **Natural systems:** tides, mycelium, bird migration.

## Track A: product feature (Tier 2)

- **Brief** (one page, committed under `docs/design/` or the PR):
  - **Job:** written as a job story.
  - **Who:** the target user, and one segment we won't serve.
  - **Evidence:** 5–10 real signals, such as issues or discussions on competing projects, forum threads, or the builder's own logged pain. If there are none, mark the brief UNVALIDATED and name the cheapest way to validate it.
  - **The one thing** it must do brilliantly. For the v0.1 core and headline features, also the signature moment.
  - **Non-goals and anti-goals:** the things we'll refuse even when asked.
  - **Cost of yes:** maintenance, API surface, test-matrix growth.
  - **Success signal:** time to first success, repeat use and dependents. Stars measure awareness only.
  - **Acceptance check and rollback criterion.**
- Then cut to the smallest version that still has the one thing. Everything else goes on a "later" list.
- **Decision:** the user approves the brief.

## Track B: tech (Tier 2)

The goal is the best fit and the simplest design. Put distinctiveness in the developer experience; novelty in the internals is a cost.

- **Options.** Give 2–3 genuinely different architectures, including the simplest one that could possibly work. For each, give its shape, tradeoffs, failure modes and dependency count. Add a 10-line usage example written from the user's side.
- **ADR** (`docs/adr/NNNN-title.md`, created on the first ADR):
  - context, the decision, the alternatives rejected, the consequences, and how to reverse it;
  - NFR budgets with a CI check where possible: startup time, memory, install or bundle size;
  - the support matrix;
  - API stability: what's public, the semver and 0.x policy, the deprecation window, a migration path for breaking changes;
  - the error model;
  - telemetry: off by default, and opt-in only if the user decides;
  - for anything that parses untrusted input or touches the network, the filesystem or execution: a threat sketch of assets, inputs and the top 3 abuse cases;
  - the long-term maintainer cost.
- **Spikes beat debate.** Timebox them, delete them afterward, and record the result in the ADR.
- Run the blind critic on the doc only. Its questions: what breaks first, what's over-engineered, and which assumption is unverified.
- **Decision:** the user approves the API shape and any new dependency.

## Track C: UI/UX (Tier 2), and DX for CLIs and libraries

**DX surface.** Every project has one, even with no visual surface:
- command grammar that's consistent;
- help text with examples;
- errors that say what happened, why, and how to fix it;
- stable exit codes;
- `--json` output, and plain output when not writing to a TTY;
- the README's first five minutes, measured by the fresh-agent test.

**Visual work:**
- **Directions.** Track C uses 3 directions, not 6–10. Render 3 distinct directions, using the drawn vocabulary or the user's references, on a design canvas if the environment has one, otherwise as one HTML page. Start with headline reactions before any polish.
- **Direction doc** (`docs/design/direction.md`):
  - mood, palette, type, motion and components;
  - things to avoid;
  - the accessibility spec: the WCAG 2.2 AA target, palette pairs checked for contrast, focus states, a reduced-motion variant, and no meaning carried by color alone.
- **Design flows, not screens.** Cover first run, the core task, and error recovery. Each flow shows its empty, loading, error and long-content states.
- **Accessibility is a gate, not polish.** Before calling it done:
  - run an automated checker (axe or Lighthouse) and show its output;
  - do a keyboard-only walkthrough of the core flow;
  - check accessible names on interactive elements;
  - give the demo GIF alt text and the text of its commands.
- **Media.** Use generated imagery or motion only if the user asks and supplies an API. It must meet the weight and motion budgets. Commit the prompts, check that the generator's terms allow redistribution, and note that the assets are AI-generated. Use a saved design system only for heavy UI, and only where the account has one; otherwise keep the tokens in `direction.md` and the code.
- **Hand-off.**
  - Implement it, render it, and show it side by side with the chosen direction.
  - The repo is the source of truth. Commit the assets: logo SVG, social preview PNG, favicons, and tokens in code.
  - Record the canvas link for later iterations.

## Gotchas

- **The user's taste wins.** A gradient they chose is not a tell. Keep only the accessibility floor, and mention it once. For any visual change, show a contrast check of the worst-case text and background pair. For gradients, check the lowest-contrast stop yourself, because automated checkers report these as "needs review".
- **Don't run Tier 2 for a flag.** Over-designing small changes is the main failure mode of this skill.
- **A critic that has seen the code isn't a critic.** Absolute scores out of 10 are noise; use comparisons.
- **API keys for generation APIs.** Use a dedicated key with a spend limit, stored in a gitignored file you've confirmed with `git check-ignore`. Never print it or pass it to subagents.
- **Strip metadata** (EXIF, location) from user-supplied images before committing them.
- **Originality.** Logos, names and visuals must not imitate another project's or company's marks. Name checks are not trademark clearance.