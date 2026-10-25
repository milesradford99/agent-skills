# Originality

Models choose the most predictable option at every step, and preference training pushes them further toward the consensus answer. Without outside pressure, demos converge on the same fonts, gradients and fade-and-slide motion. Variety has to come from outside the model, and distinctiveness has to be spent in one or two places. These methods adapt the repo's `oss-design` skill and Anshu Chimala's "How to turn your AI into a world-class designer" (Lenny's Newsletter, 2026) to video.

Use them for the "random draw" and "extreme" directions in phase 2, and for everything in a video when the user asks for something more unusual.

## 1. Draw from outside the model

Asking a model to "be random" or "be unique" produces output that only sounds random. Use a real source of randomness and build from what it gives you.

- **Vocabulary draw.** Draw 2–3 entries from the vocabulary in `styles.md` (plus the user's interests):
  ```sh
  shuf -n 3 -e "paper" "oscilloscope" "tides" "letterpress" "pinball"
  python3 -c "import random,sys;print(random.sample(sys.argv[1:],3))" paper oscilloscope tides letterpress pinball
  ```
- **Seed string.** Generate a long random string and derive concrete choices from it: palette hue, layout grid, type family, the camera's path, the shape of the signature moment. Never show the string in the video.
  ```sh
  python3 -c "import secrets;print(secrets.token_urlsafe(24))"
  ```
  Put the string in `timeline.meta.seed` too, so the seeded randomness in the render is reproducible.
- Record what was drawn in `progress.md`, so a direction can be explained and re-created.

## 2. Import a mechanism from another domain

The best ambitious briefs bring in something from outside motion design: a game, a physical place, an installation, a craft. The import must bring over a **mechanism** (how that thing behaves or solves a problem), not just its look. Name the mechanism in one line, or drop the analogy.

- "Features as neighbourhoods of an isometric city; the camera tours them like a city builder's zoom-out." Mechanism: zoom levels reveal structure.
- "The product launch as a rocket countdown." Mechanism: escalating checklist with a hard T-0 that the music lands on.
- "A data story drawn by a plotter pen." Mechanism: one continuous stroke, so every chart is built in drawing order.

## 3. Broad, then steered

1. List 6–10 headline-only ideas, one line each with no detail. Include the drawn directions and one deliberate extreme.
2. Let the user react in their own words ("this one, but less playful", "never neon"). Treat dislikes as avoid-list entries.
3. Develop only the picks into 10-second demos, then write the build spec for the chosen one.

Always offer "pick for me", which takes your recommendation and records why.

## 4. One deliberate extreme

One of the three demos breaks a convention on purpose: radical asymmetry, dissonant colour, uncomfortable negative space, no music until the end, a single unbroken shot. Show it at demo depth only; develop it only if the user picks it. It makes the other two directions easier to judge and sometimes wins.

## 5. A critic that names the bar

In addition to the scored review in `review.md`, a direction critic can push a demo past "fine". Give a fresh subagent only the stills or contact sheet and ask it to:

1. name the aesthetic it sees;
2. describe how a top studio would execute that aesthetic;
3. list the biggest gaps between the two, specifically (frame, element, fix);
4. call out anything overdone or obviously AI-generated.

Keep the critic prompt identical across rounds, and don't tell it the target score, so it can't grade toward it. Use concrete references (the user's examples, named studio work) as a moodboard for the critic, never as something to copy. Use the strongest model as critic and a cheaper one to implement.

## 6. Generated plates, used sparingly

Code-drawn scenes default to gradients and geometric shapes, which read as AI-made. When a direction needs real texture or imagery that code can't draw well, a generated image or clip can be a plate inside the code render. It's paid spend, so it's a hard stop.

- Generate each plate once and cache it in `assets/plates/`, logging the model, prompt, seed and date in `licenses.json`. Never regenerate on every render.
- For animated elements, generate a loop on a solid background, then key it out (chroma key or a matting model) and composite it in the page.
- For transitions between stills, keyframe interpolation between two images can produce a clip; the last frame of one clip can seed the next.
- Type, timing, brand marks and the cut stay in code, where they're exact and cheap to change.

## 7. Subtract

AI adds and rarely removes. Restraint is what reads as premium. For every element, layer, effect, sound and second of runtime, ask what breaks if it's cut; if nothing does, cut it. Ask the reviewer for at least one removal per round.

## 8. Remove AI-video tells

Cut anything that's there because it was the generator's first instinct rather than a decision:

- a slideshow structure: card, fade, next card, with a synthetic voice reading the text;
- every element entering with the same fade-and-slide-up;
- uniform easing and timing everywhere, with no holds;
- stock gradients, glows, lens flares, particle dust and bokeh used as filler;
- bouncy springs on serious type;
- the centred title on a dark gradient;
- default title fonts (Inter, Space Grotesk, Poppins) chosen by habit;
- music that ignores the cuts, and whooshes on every move;
- a generic "tech" palette of purple-to-blue;
- motion that is smooth in a style that should step.

If the user chose one of these, it's a decision, not a tell.

## Where distinctiveness goes

Spend the boldness on the signature moment and the overall look. Keep the hook clear, text readable, the brand correct and the end card legible. A distinctive choice that makes the message harder to get is a regression.

Keep failed directions and prompts in `video/recipes/_rejected/` with one line on why. Retry them when a newer model or tool is available.
