---
name: "more-ambitious"
description: "Pushes a task past the average first attempt along three axes from Felix Rieseberg's tutorial: altitude (the goal beyond the goal), depth (an expert's raw material, instruments and outside judge) and range (methods from other fields). It shows the user an ambition ladder with a recommended rung, asks at most 3 questions only they can answer, lists the access that would unlock more, then builds with hard targets and outside validation, never self-grading. Use when the user says be more ambitious, think bigger, go further, don't settle, push harder, 更激进, 更有野心, 别保守, 多探索, 往深里做, or invokes /more-ambitious; also when the agent is about to settle for the obvious version of a task the user cares about. Not for one-line fixes or tasks whose exact spec the user has fixed."
---

# More ambitious

Agents settle. Given a task, a model executes the user's best guess at how to get the outcome, at the level of the average attempt it has seen. "Try harder" or "be creative" changes the vocabulary, not the method. What changes the method is a specific hard goal, access to the raw material, instruments a top professional would use, and a judge that isn't the model.

This skill works on three axes (a fourth, speed, is just doing the same work faster):

- **Altitude:** climb from the task to the outcome it serves, and from there to a system that makes the task unnecessary.
- **Depth:** do the task the way the best person in the field would, with their raw material, methods and tools, until even they might learn something.
- **Range:** bring in methods from fields the task doesn't obviously need.

Reply in the user's language. Keep the overhead proportional: the ladder and questions fit in one message.

## Step 0: is it worth it?

- **Skip** for a one-line fix, a lookup, or a task where the user has fixed the exact spec ("just rename this"). At most, offer the next rung in one line after doing what was asked.
- **Altitude is weak for creative work** (a poem, a logo, a story). Use depth and range there.
- **A good sign altitude pays:** people will hold a meeting, make a decision or repeat this task every week/month.

## Step 1: build the ladder

Write the goal beyond the goal. Ask: when this is done, what happens next, and who decides what? Then lay out 3 rungs:

| Rung | What it is | Example (crash bug) | Example (quarterly review deck) |
|---|---|---|---|
| L0 | The task as asked | Fix this crash | Fill the template with this quarter's numbers |
| L1 | The outcome the task serves | Find and fix the class of bug, with a regression test | Say what changed, why, and the 3 most urgent decisions with for/against |
| L2 | A system that keeps the outcome without the user | Keep the app crash-free: pull crash reports, map versions to commits, reproduce on each OS, verify fixes | Design a better early-warning mechanism than a quarterly deck, show on past data that it would have caught problems sooner, run it beside the old process for a quarter |

For each rung, note: what it delivers, what it needs (data, access, machines, money), how it will be judged from outside, and rough cost. L2 almost always requires changing the workflow, usually by granting access; say exactly what.

## Step 2: depth pass

Answer these four before planning the work (adapted from the tutorial):

1. What would a top professional in this field do here that the user isn't asking for?
2. What is the rawest material they would start from, instead of what's already been digested (summaries, dashboards, screenshots)?
3. Which specific methods and tools would they use? If you're reaching for a markdown table, the expert probably reaches for a database, a statistical model, a profiler, a simulator or a proper renderer. Install it.
4. What, other than you or the user, would show the result is right?

Then add the levers that make depth real:

- **An unreasonable target, stated as reasonable.** Load in 10 s? Aim for 200 ms. 5 % better? Aim for 2×. Write the number down and measure against it. Specific hard goals beat "do your best".
- **Challenge what the user believes.** Pick the belief the plan rests on ("churn is an onboarding problem") and try to reproduce it from the raw data. Report whether it holds.
- **Produce new knowledge.** Once deep in the data, look for the blind spot: an earlier signal, a cheaper path, a cause nobody named. Show it works on data it hasn't seen.

## Step 3: range pass

- **Nouns to verbs.** Rewrite the deliverable as what it has to do. A quarterly review isn't "a deck"; it's "getting busy people to believe a story about cause and effect and decide under uncertainty in 30 minutes". The verbs point at the fields that can help.
- **Assemble the crew.** If the result had to be extraordinary, who would you bring? Name 3–6 fields, and for each one the concrete *method* it contributes, not its voice. For the deck: an analyst (cohort analysis), a journalist (finding the one story the data supports), an editor (cutting), a short seller and a forensic accountant as the red team (hunting for what's hidden or overstated). Do what a short seller does to research a position; never write "like a short seller".
- If subagents are available and the task is large, give each field its own agent with the raw material and its method, then merge. Otherwise run the methods in sequence yourself.

## Step 4: pull more from the user

The user often holds what unlocks the higher rungs and doesn't know it's needed. Send one message, the ambition card:

1. **The ladder** (3 rungs, one line each) with the **recommended rung** and why.
2. **Up to 3 questions only the user can answer**, each with your default, so a one-word reply works. Pick from:
   - What happens after this is done? Who reads it, and what do they decide?
   - What number or result would make you say "wow"? (Offer your unreasonable target as the default.)
   - Which belief behind this plan would hurt most if it were wrong?
   - What has been tried already, and why did it stop?
   - What can I break, spend or take time on? (Budget, risk.)
3. **The access list:** "Grant me X and I can do Y without you." Name each item: a data export, a log source, an API key, a test machine, a staging environment, a connector, permission to install tools.
4. **"Go with your pick"** as an explicit option.

If the user replies tersely or not at all in an unattended run, take the recommended rung, do only reversible work, and list the questions again in the report.

When the user asks how to push agents themselves, hand them `references/prompts.md` (a bilingual prompt kit). If it's missing, give them the four depth questions and the ladder from this file.

## Step 5: build

- **Floor first.** Deliver L0 (or prove the higher rung covers it) before climbing, unless the user waived it. Ambition never costs the user the thing they asked for.
- **Hard target, measured.** Keep the written target in view and report the measured number, not "improved".
- **"Impossible" is homework.** Before declaring something blocked, try at least 3 different routes, at least one of which changes the problem: get rawer data, install a tool, write a simulator or a harness, ask for access. Then report what was tried.
- **Real instruments over prose.** Run code, query real data, build the prototype, render the thing. A plan or a description is not the result.
- **Permission to fail cheaply.** Spike risky ideas in a scratch branch or directory with a time box. A failed experiment with a clear finding is progress; keep going.
- **Outside judge, always.** Tests, benchmarks, held-out data, a reproduction in the real environment, a fresh-context reviewer given only the artifacts, or a real user. Never grade your own work.
- **Checkpoint between rungs.** Show the evidence for the current rung. Ask before the next one if it needs new access, money, or anything outward-facing.

## Step 6: report

- The rung reached, and the evidence from the outside judge.
- The measured result against the target.
- What failed and what it taught.
- The next rung, and what it would need from the user.
- A durable workflow, if there is one: what to automate or grant so the user doesn't have to hand over this task again.

## Guardrails

- **Ambition is not unasked scope creep.** Climbing a rung is the user's choice; the ladder exists so they can make it quickly.
- **Irreversible, public or paid actions** (deploys, emails, posts, purchases, deletions, settings changes) need the user's explicit yes for that exact action, whatever the rung.
- **No fake ambition.** Never fabricate data, results or benchmarks to make a bold claim. A bold idea that failed is reported as failed.
- **No role-play theater.** Personas that change the tone but not the method make the transcript weirder and the result no better.
- **Respect the budget.** If the user gave a time or cost limit, the ladder fits inside it.

## Gotchas

- **Asking more than 3 questions** turns the card into homework for the user. Default everything you can.
- **Running the full ladder on a small task** is this skill's main failure mode. Step 0 exists for that.
- **The access list is the lever people miss.** Most "the agent wasn't ambitious enough" moments are really "the agent couldn't see the logs".
- **A model that helped build the result is not its judge**, even in a new turn. Use a fresh context or a tool.

## Facts as of 2026-11 (re-verify before relying on them; update the date when you do)

- Models still can't be trusted to judge their own work; the tutorial (October 2026) insists on outside validation, ideally a tool the model can run for immediate feedback.
- Models handle higher abstraction better as they get more capable, but a bare goal such as "go make money" still doesn't work for most businesses on its own.
- All three axes assume the agent has a computer where it can install software, plus access to relevant data (MCP connectors or other means).

## Source

Adapted from Felix Rieseberg, "How to be more ambitious: A tutorial for humans with models" (13 October 2026), https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/ . The ladder card, the question bank and the build rules are this skill's own.
