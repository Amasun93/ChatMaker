# Premium micro-interactions

Use this page only when the user asks for a polished, Apple-like, high-end or animation-rich result. Motion should clarify an action or state change, not become a decorative obstacle.

## Reference source

Amicro is an MIT-licensed React and Motion component collection with copy-to-code CLI and shadcn registry delivery:

- Official site: https://amicro.vercel.app/
- Official repository: https://github.com/Subhan-code/Amicro--Micro-transitions-
- Package: `@subhanhq/amicro`
- Reviewed source tree: `52b9915287499165a47590989cf586263a0bef1f`

The library requires React 18/19, Tailwind and Motion. Its CLI is useful for an existing compatible React project, but it is not the beginner default for ChatWeb.

## What ChatWeb should absorb

- Press feedback: a short spring compression and release confirms that a button received the touch.
- State morphing: let the icon, label and color move together when an action changes from ready to working, success or failure.
- Staggered reveal: introduce related items in a short sequence so the user sees hierarchy; stop after the initial reveal.
- Card depth: use arc, stack or cover-flow movement only when the user is comparing choices, steps or time states.
- Text reveal: use restrained word or line reveals for an opening message, never for long instructions or rapidly changing data.
- Data feedback: animate the changed value or chart mark, while leaving labels and scales stable.

Prefer `transform` and `opacity` animations. Keep touch targets at least 44 px, make every hover interaction work by touch or click, and provide `prefers-reduced-motion` behavior that preserves the same state information without movement.

## Delivery choice

For a beginner, classroom tool or one-file hardware page, recreate the selected interaction with native HTML, CSS and JavaScript so the result opens directly and remains offline-capable.

For an existing React project that already accepts Tailwind and Motion, a selected Amicro component may be added after checking its current registry entry and dependencies. Do not run `init`, `add`, npm, shadcn or another installer silently. If substantial upstream code is copied, retain the MIT attribution required by its license.

Use one or two signature interactions per page. A page with spring buttons, magnetic cursor effects, 3D cards, animated text and continuous background motion all at once is harder to understand and usually feels less premium.
