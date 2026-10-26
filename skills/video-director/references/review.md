# Review

Agents grade their own work too generously, and a reviewer that has seen the producer's reasoning grades the intent, not the screen. Craft is also not value: a beautifully made video can still be dull, confusing or preachy for the person it's for. So review has three parts, each with a fresh agent that sees only the output and its criteria:

1. **The audience pass** asks "is this worth watching, for the viewer it's for?" It runs on the script (phase 2, text only) and on the rough cut (phase 4).
2. **Measured QC** catches technical faults.
3. **The craft reviewer** scores how well it's made (phase 5).

## The audience pass

A fresh subagent plays 2–3 target viewers taken from the brief, at least one of them skeptical or hostile to the piece's stance. It never sees the spec or how the video was made. Use it on the story card and script before building, and on the rough cut's contact sheets and captions afterwards.

For each persona it answers, in that viewer's voice:
- **Stay or scroll:** would I still be watching at 3 s, 30 s and the end? Where exactly would I drop off, and why?
- **What I got:** the takeaways in my own words. Compare these with the story card's takeaways; a takeaway nobody states back hasn't landed.
- **Confused by:** terms, jumps or numbers I couldn't follow.
- **Didn't believe or didn't like:** anything that felt preachy, one-sided, condescending, salesy or untrue, and any claim I'd want a source for.
- **Would I share it, and what would I comment?** The first comment under the video, honestly.
- **Value:** was it worth the time? 1–5, with one sentence.

Then, out of character: the 3 changes that would most raise the value for these viewers, each tied to a beat or timecode.

**Gate:** every takeaway on the story card is stated back by at least one persona, no persona drops off in the first 30 s for a reason the piece can fix, and nothing is flagged as untrue or unsourced. Fix content problems in the script before building; at the rough cut, fix them before the craft review. Show the user the audience read with the story card and the rough cut, briefly.

Prompt template:

```text
You will read <a video script with on-screen words and timings | contact sheets and captions of a rough cut>.
You didn't make it and don't know how it was made. Play each of these viewers in turn, honestly, including
the parts they'd dislike: <persona 1 from the brief>; <persona 2>; <a skeptical persona>.
<paths>
For each viewer: stay or scroll at 3 s / 30 s / end (and where they'd leave); takeaways in their own words;
what confused them; what they didn't believe or didn't like (preachy, one-sided, salesy, untrue, needs a source);
would they share it and what they'd comment; value 1-5 with one sentence.
Then, as yourself: the 3 changes that would most raise the value for these viewers, each with a beat or timecode.
Reply in plain text, under 500 words.
```

For a rough cut, give it the contact sheets and the captions file, not bursts or full-resolution stills: it judges meaning and pacing, not pixels.

## Round order

1. `python3 lib/qc.py <video> <slug>/timeline.json --out <slug>/review/round-N/qc.json`. Fix QC failures before spending a reviewer on them, unless a failure needs a judgment call.
2. `python3 lib/frames.py review <video> <slug>/timeline.json <slug>/review/round-N/pack`. It writes a budgeted pack and prints its image count and approximate tokens:
   - contact sheets with timecodes, about 120 cells in all (2 fps for short pieces, sparser for long ones), for structure and pacing;
   - at most 10 bursts of every native frame in a 0.5 s window, at the key cues first, then cuts, spread across the piece, for motion;
   - at most 6 stills at 1280 px wide at key cues and the end, for type and texture (use `frames.py still` at full resolution only for a frame where small text is in question);
   - a waveform and a spectrogram of the soundtrack, for sound and sync.
3. Launch the reviewer (template below) as a **fresh** subagent, never a fork. Pass only paths: the pack, `qc.json`, `brief.md`, the chosen demo's stills. From round 2, add `frames.py pair <previous> <current> <dir> <timecodes>` images at the 6–8 moments that changed most, instead of a second full pack.
4. Apply the fixes under the iteration rules in `pipeline.md`, re-render, and run the next round.

A pack costs roughly 20–25 images and 40–60k image tokens whatever the length; a 4-minute film no longer costs eight times a 30-second one. The reviewer's text answer is what returns to the main conversation; the producer doesn't open the pack's images itself, except the one or two frames a decision hangs on.

## Rubric

Score each dimension 1–10 against these anchors. Most first renders score 5–7.

| Score | Meaning |
|---|---|
| 5 | Student work: the idea is there, the execution isn't |
| 6 | A decent template: competent and forgettable |
| 7 | Solid professional work |
| 8 | High-end agency work |
| 9 | Award shortlist |
| 10 | The best work in the field |

| Dimension | What it covers |
|---|---|
| Style fidelity | How clearly and accurately the piece expresses its chosen style's signatures (from the spec) |
| Concept and impact | A strong idea, a hook in the opening, a memorable signature moment, an ending that lands, images that explain without narration |
| Motion craft | Timing, easing, spacing, stagger, holds, the behaviour of moving elements, and continuity: beats that transform into each other rather than cut or fade between cards |
| Design and typography | Composition, hierarchy, type, colour, negative space, safe areas, legibility |
| Finish and texture | Lighting, detail, surface treatment, absence of artifacts (banding, aliasing, clipping at edges) |
| Sound and sync | Music, effects, mix and loudness, and how exactly sound lands on picture |
| Technical execution | Output spec, fonts, rendering, QC results |

Rules:
- **Any QC failure caps technical execution at 6.**
- **A score above 8 needs evidence:** a timecode or frame that shows it.
- **Gate on the lowest dimension**, not the average: a weak mix can't hide behind good type.
- **A slideshow structure caps concept and impact at 6 and motion craft at 6**, unless the brief asked for one.
- The reviewer can't see motion between sampled frames or hear the audio. It says so where that limits a judgment, and leans on bursts, the waveform and the spectrogram instead of inventing an opinion.

## Stop rule

- **Pass:** lowest dimension ≥ 7.5 and zero QC failures. Stop and deliver.
- **Default:** 2 rounds. Run a 3rd only if the lowest dimension rose by 0.5 or more in the last round.
- **Regression:** from round 2 the reviewer also compares the two latest versions, unlabeled and in random order. If the new version loses, revert to the better one and stop.
- **Never more than 3 rounds.** Report the remaining fixes as known weaknesses.

## Reviewer prompt template

```text
You are reviewing a finished short video. You did not make it and have no access to how it was made.
Judge only what is on screen and in the soundtrack evidence.

Brief: <path to brief.md>
Chosen direction (stills the user picked): <paths>
Spec excerpt (style rules and avoid list only): <paste those two sections>
QC report: <path to qc.json>
Evidence:
- Contact sheets, 2 fps, timecoded: <paths>
- Bursts, every frame in 0.5 s around each cue and cut: <paths>
- Full-resolution stills: <paths>
- Waveform and spectrogram: <paths>
<From round 2:> Pairs of A and B (random order, unlabeled) side by side at the same timecodes: <paths>

What you can't see: motion between sampled frames, and the actual sound. Say where that limits you.

1. Name the aesthetic you see in one line, and how a top studio would execute it.
2. Score each dimension 1–10 using these anchors: 5 student, 6 decent template, 7 solid professional,
   8 high-end agency, 9 award shortlist, 10 best in field. Most first renders score 5–7. Any QC failure caps
   Technical execution at 6. Any score above 8 must cite a timecode.
   Dimensions: Style fidelity; Concept and impact; Motion craft; Design and typography; Finish and texture;
   Sound and sync; Technical execution.
3. List 5–10 fixes ordered by likely effect on the finished piece. Each fix has: timecode, what is observably
   wrong, why it matters (which dimension, how much), and a concrete change. At least one fix must raise
   concept and impact, not just correct a defect. Removing something is a valid fix; include at least one.
4. Call out anything that reads as generic or AI-made, especially a slideshow structure (cards with fades between
   them, text read by a voice) where the piece should flow continuously.
<From round 2:> 5. Which version, A or B, better serves the brief, and where specifically?

Reply as JSON:
{ "aesthetic": "...", "scores": { "style_fidelity": n, "concept_impact": n, "motion_craft": n,
  "design_typography": n, "finish_texture": n, "sound_sync": n, "technical": n },
  "evidence": { "<dimension>": "timecode and what it shows" },
  "fixes": [ { "t": "00:06.5", "problem": "...", "impact": "...", "dimension": "...", "change": "..." } ],
  "generic": ["..."], "limits": ["..."], "better": "A|B|null", "better_why": "..." }
```

Keep this prompt identical across rounds, and don't tell the reviewer the pass mark, so it can't grade toward it.

## Turning fixes into edits

For each fix, the producer writes one line in `review/round-N/plan.md`: `<timecode> → <shot id> <param path or file> : <change>`. Apply them in order of impact, re-render the smallest unit that shows the fix, then the full render. Skip a fix only with a one-line reason (it conflicts with the user's stated taste, or the spec).

## The scorecard (for delivery)

```text
Review: <N> rounds by a fresh AI reviewer (AI judging AI work; treat scores as a guide, not a verdict)
             round 1   final
Style        6.5       8.0
Concept      6.0       7.5
Motion       7.0       8.0
Design       7.0       8.0
Finish       6.5       7.5
Sound        6.0       7.5
Technical    7.0       8.5
QC           2 fails   pass
Audience     <one line: who stays, the takeaway most stated back, the main remaining objection>
Tokens       <rough session total, and the review share>
Known weaknesses: <the fixes not made, one line each>
```

## Optional cross-check

If a model from another family with native video input is available, it can review the final once as a cross-check on same-family bias. It's spend: ask first.
