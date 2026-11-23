# Prompt kit: pushing an agent past the average attempt

For the user to paste into any agent. Each prompt is in Chinese, then English. Mix and match: altitude, depth and range stack.

## 一句话开场 / One-liner

> 先别动手。告诉我这件事完成之后接下来会发生什么、谁要据此做什么决定；然后给我三个层级的做法（照我说的做 / 服务真正目标的做法 / 让这件事以后不再需要我的机制），推荐一个，并列出你需要我给你什么权限或数据。

> Before you start: tell me what happens after this is done and who decides what with it. Then give me three rungs (as asked / the outcome it serves / a system that makes this task unnecessary), recommend one, and list the access or data you need from me.

## 高度 / Altitude

> 这件事背后的目标是什么？目标背后的目标又是什么？如果只能做一件事来让那个最终结果持续发生，你会做什么？

> What's the goal behind this task, and the goal behind that? If you could build one thing that keeps that final outcome happening without me, what would it be?

> 别一次修一个问题了。设计一个流程让这类问题持续被发现和修复，告诉我要让你独立做到这点，你缺哪些访问权限。

> Stop fixing these one at a time. Design a loop that keeps finding and fixing this class of problem, and tell me what access you'd need to run it on your own.

## 深度 / Depth

> 我要的是更深的版本，不是更大的版本。改写之前：(1) 这个领域最顶尖的人会做哪些我没要求的事；(2) 他们会从哪份最原始的材料开始，而不是用别人消化过的东西；(3) 他们会用哪些具体方法和工具；(4) 除了你和我，什么能证明结果是对的。然后按这些重写我的需求。

> I want a deeper version of this task, not a bigger one. Before rewriting it: (1) say what a top professional in this field would do here that I'm not asking for; (2) name the rawest material they would start from instead of what has already been digested for me; (3) name the specific methods and tools they would use; (4) say what, other than you or me, would show the result is right. Then rewrite my prompt to ask for exactly that.
>
> (Quoted from Felix Rieseberg's tutorial.)

> 目标不是从 10 秒降到 5 秒，是 200 毫秒。这完全可以做到，继续找办法，别停在第一个能用的方案上。

> The target isn't 5 s, it's 200 ms. It's solvable; keep going past the first thing that works.

> 我们一直以为「X 是因为 Y」。用原始数据试着复现这个结论，告诉我它站不站得住。

> We believe X happens because of Y. Try to reproduce that from the raw data and tell me whether it holds.

> 既然你已经深入数据了，找一个我们还不知道的信号，并在它没见过的数据上证明它有预测力。

> Now that you're deep in the data, find a signal we don't know about yet and show it predicts on data it hasn't seen.

## 广度 / Range

> 把交付物从名词改成动词：它到底要「做」成什么事？据此找出 3–6 个能带来独特方法的领域，每个领域写清楚它贡献的具体方法，而不是模仿它的口吻。加上一个红队。

> Rewrite the deliverable as verbs: what does it actually have to do? From that, name 3–6 fields that bring a distinct method, say exactly which method each contributes (not its voice), and add a red team.

## 让 AI 问我 / Make the agent ask

> 在开始之前，问我最多 3 个只有我能回答、而且最能改变你做法的问题，每个问题附上你的默认答案，我可以只回「按默认」。

> Before starting, ask me at most 3 questions that only I can answer and that would most change your approach. Give your default for each so I can just say "defaults".

> 列一张清单：「给我 X，我就能不需要你地做到 Y」。

> List: "Give me X and I can do Y without you."

## 验证与坚持 / Judge and persist

> 不要给自己打分。告诉我用什么外部方式验证（测试、基准、留出数据、真实环境复现、只看产物的新审稿人），然后跑给我看。

> Don't grade your own work. Tell me the outside check (tests, benchmark, held-out data, a real-environment reproduction, a fresh reviewer who sees only the artifacts), then run it.

> 说「做不到」之前，至少换 3 条路试过，其中一条要改变问题本身（拿更原始的数据、装工具、写模拟器、找我要权限）。

> Before saying it can't be done, try at least 3 routes, one of which changes the problem itself (rawer data, a new tool, a simulator, asking me for access).

> 允许失败。在草稿分支里限时做一个最激进的版本，失败了就告诉我学到了什么。

> You have permission to fail. Time-box the boldest version in a scratch branch, and if it fails, tell me what it taught.
