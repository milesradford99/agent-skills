// The title wipes away and a small line settles in, then holds.
import { range } from '../../lib/runtime.js';

export function setup(ctx) {
  ctx.el.innerHTML = `<div class="line">${ctx.params.text}</div>`;
  Object.assign(ctx.el.style, { display: 'grid', placeItems: 'center', background: 'var(--bg)' });
  Object.assign(ctx.el.querySelector('.line').style, { fontSize: '64px', letterSpacing: '0.02em' });
}

export function render(ctx) {
  const wipe = ctx.ease('snap')(range(ctx.t, 0, 0.4));
  ctx.el.style.clipPath = `inset(0 ${(1 - wipe) * 100}% 0 0)`;
  const u = ctx.ease('enter')(range(ctx.t, 0.2, 0.7));
  const line = ctx.el.querySelector('.line');
  line.style.opacity = String(u);
  line.style.transform = `translateY(${(1 - u) * 24}px)`;
}
