// Letters snap in one by one, landing on the hook cue; the accent bar grows after.
import { range } from '../../lib/runtime.js';

export function setup(ctx) {
  ctx.el.innerHTML = `<div class="word"></div><div class="bar"></div>`;
  Object.assign(ctx.el.style, { display: 'grid', placeItems: 'center' });
  const word = ctx.el.querySelector('.word');
  Object.assign(word.style, { fontSize: `${ctx.style.type.title_px}px`, fontWeight: 800, letterSpacing: '-0.03em' });
  word.innerHTML = [...ctx.params.text].map(ch => `<span style="display:inline-block">${ch}</span>`).join('');
  Object.assign(ctx.el.querySelector('.bar').style, {
    position: 'absolute', left: '50%', top: '66%', height: '14px', background: 'var(--accent)', transform: 'translateX(-50%)',
  });
}

export function render(ctx) {
  const enter = ctx.ease('enter');
  const stagger = ctx.style.timing.stagger_frames / ctx.meta.fps;
  const letters = ctx.el.querySelectorAll('.word span');
  const land = ctx.params.hit; // cue time, so retiming the cue retimes the shot
  letters.forEach((el, i) => {
    const start = land - 0.3 - (letters.length - 1 - i) * stagger;
    const u = enter(range(ctx.t, start, start + 0.3));
    el.style.transform = `translateY(${(1 - u) * 120}px)`;
    el.style.opacity = String(u);
  });
  const grow = ctx.ease('snap')(range(ctx.t, land, land + 0.5));
  ctx.el.querySelector('.bar').style.width = `${grow * 640}px`;
}
