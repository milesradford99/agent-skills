# Styles

Each style is a set of signatures you can check against a frame, numbers to put in `style.json` and the spec, and a failure list for the avoid list. **Sourced** styles come from published Claude motion-graphics libraries (Awesome Claude's style rules, the mg-styles-15 prompts and rubric, as of 2026-10). **Craft default** styles are working knowledge with no published spec yet; treat their numbers as starting points and check them on stills.

Frame rate is part of the style. Smooth 60 fps tweening is the most common way a handmade style ends up looking like a template.

## Sourced

### Isometric world
- **Signatures:** true 2:1 isometric (30° lines), no perspective; parts build in stagger (tiles, then buildings, then life); layered parallax; camera pull-back reveal.
- **Numbers:** stagger of 2–4 frames per element; parallax 1 : 0.8 : 0.6 (foreground : mid : back); overshoot of 6–10% on growth; 4–6 colour palette with one accent.
- **Fails when:** perspective creeps in, everything appears at once, or there are too many colours.

### Swiss / kinetic typography
- **Signatures:** 12-column grid; one typeface family; hard snaps; big scale contrast; text as the image.
- **Numbers:** easing `cubic-bezier(.7,0,.2,1)`; moves of 8–14 frames; holds of at least 12 frames for reading; minimum type size 48 px at 1080p.
- **Fails when:** there's overshoot or springs, a second typeface, centred everything, or words animate faster than they can be read.

### Hand-drawn / line boil
- **Signatures:** animated on twos; 3 jitter variants of each line cycling; smear frames instead of motion blur; paper texture.
- **Numbers:** 24 fps time base held 2 frames (12 drawings/s); boil cycle of 3 variants; line wobble of 1–2 px at 1080p.
- **Fails when:** lines are perfectly smooth, tweening is continuous, or every line boils in sync.

### Flat vector
- **Signatures:** geometric shapes; no gradients or shadows, or one flat shadow; bold colour blocks; shape-morph transitions.
- **Numbers:** 3–5 colours; corner radius consistent across elements; ease-out cubic on entrances; stagger of 3 frames.
- **Fails when:** gradients and glows creep in, or stroke widths and radii are inconsistent.

### Line animation
- **Signatures:** a single stroke drawing itself; stroke-dashoffset reveals; line continuity across cuts (one line becomes the next scene).
- **Numbers:** one stroke weight; draw speed constant in px/s; caps rounded or square, never mixed.
- **Fails when:** lines pop on instead of drawing, or several weights are used.

### 3D render
- **Signatures:** physically lit materials; a deliberate lens (35–85 mm equivalent); depth of field on hero shots; soft contact shadows.
- **Numbers:** 24–30 fps; 1–3 key lights; one hero material; motion blur at a 180° shutter.
- **Fails when:** lighting is flat, the scene is all plastic, objects float without contact shadows, or the camera is static.

### Morphing / shape transitions
- **Signatures:** every transition is one shape becoming the next; matched silhouettes; continuous motion through the cut.
- **Numbers:** morphs of 12–20 frames; ease in-out; point counts matched before interpolation.
- **Fails when:** shapes cross-fade instead of morphing, or they twist mid-morph.

### Collage / cut paper
- **Signatures:** torn edges; photo cut-outs; visible paper grain and shadows; stop-motion steps.
- **Numbers:** 12 fps steps; a 1–3° random rotation per frame (seeded); a drop shadow 2–6 px offset.
- **Fails when:** motion is smooth, edges are vector-clean, or the layout is perfectly aligned.

### Pixel art
- **Signatures:** drawn at low resolution and scaled up with nearest-neighbour; limited palette; sprite animation; the camera snaps to whole pixels.
- **Numbers:** draw at 320×180 and scale ×6 to 1920×1080; 8–12 fps sprite animation; a palette of 16–32 colours; no anti-aliasing.
- **Fails when:** pixels are blurry or scaled to non-integer multiples, sub-pixel motion appears, or the palette is too large.

### Liquid / fluid motion
- **Signatures:** metaball or SDF blobs; viscous follow-through; colour that bleeds at the edges; organic transitions.
- **Numbers:** 30–60 fps; slow-in, slow-out with long tails; 2–4 colours.
- **Fails when:** it looks like a generic lava lamp, or motion doesn't respond to the music.

### Kinetic captions (social)
- **Signatures:** word-by-word reveal in time with speech; active word highlighted; bold sans; safe-area placement.
- **Numbers:** 2–4 words visible at a time; highlight change on the word onset (within 1 frame); text in the middle 60% of the frame; minimum 64 px at 1080×1920.
- **Fails when:** captions drift from speech, sit under the platform UI, or are too long to read.

## Craft defaults (no published spec yet)

| Style | Signatures | Numbers to start from | Fails when |
|---|---|---|---|
| Glitch / datamosh | RGB channel split, block displacement, scanlines, hard cuts on beats | Glitch bursts of 2–6 frames on hits only; channel offset 4–12 px | Glitching all the time; it reads as broken, not intended |
| Grain / risograph | 2–3 spot colours, misregistration, halftone, heavy grain | 12 fps; offset of 2–4 px between layers; seeded grain per frame | Clean digital gradients; grain that doesn't move |
| Claymation look | Thumbprint texture, squash and stretch, boiling surfaces, stop-motion steps | 12 fps; seeded surface jitter; soft key light | Smooth tweens; plastic sheen |
| Y2K / chrome | Chrome type, lens reflections, bubble shapes, gradient skies | Environment-mapped reflections; slow rotation | Applying chrome to everything; low-res reflections |
| Brutalist | Raw grid, system fonts, harsh contrast, abrupt cuts | No easing (linear or cuts); one or two colours | Polished easing; decorative flourishes |
| Cel-shaded anime | Flat cel shading with 2-tone shadows, speed lines, impact frames, smears | 24 fps on twos with ones for fast action; impact frames of 1–2 frames | Soft gradients on characters; no impact frames |
| Paper cutout | Layered paper planes, parallax, shadows between layers | 12 fps; 3–5 layers with parallax ratios | Flat layers with no shadow |
| Documentary / Ken Burns | Slow pans and zooms on stills, archival grain, lower thirds | Zoom of 5–10% over 4–8 s; linear or very gentle easing | Fast zooms; zooming into faces' edges |
| Data-viz explainer | One chart idea per beat, axis-first builds, annotation callouts | Hold every number for at least 1.5 s; one highlight colour | Animating every bar at once; unlabeled axes |
| Trailer / cinematic | Letterbox, slow push-ins, title cards on black, silence before the hit | 24 fps; title cards held 1.5–2.5 s; a drop to silence of 0.3–0.8 s before the title | Wall-to-wall music; no breath |
| UGC / talking-head | Jump cuts on breaths, punch-in zooms, burned-in captions | Punch-in of 10–15% every 3–6 s; captions as above | Dead air left in; captions out of sync |

## Direction vocabulary

Draw from these with a real RNG (see `originality.md`) and extend them with the user's own interests.

- **Materials:** paper, enamel, felt, brushed steel, terrazzo, glass, ice, clay, neon tube, cardboard.
- **Eras:** 1970s transit signage, early web, Bauhaus, Swiss modernism, Showa-era packaging, 1960s space-race, 90s arcade attract mode.
- **Tools and instruments:** field notebook, control panel, slide rule, oscilloscope, darkroom, planetarium projector, mechanical calculator.
- **Crafts:** bookbinding, letterpress, woodblock, knitting patterns, stained glass, origami, embroidery.
- **Games and toys:** roguelike, city builder, puzzle box, pinball, flip book, zoetrope, marble run.
- **Rituals:** tea ceremony, morning newspaper, a pit stop, a rocket countdown, a magic trick reveal.
- **Natural systems:** tides, mycelium, bird migration, crystal growth, aurora, erosion.
- **Film grammar:** one-take tracking shot, split screen, title sequence, silent-film intertitles, nature documentary.
