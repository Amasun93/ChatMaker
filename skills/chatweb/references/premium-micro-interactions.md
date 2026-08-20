# Premium micro-interactions

Use this page for every clear ChatWeb build. Automatically choose effects that fit the content so the first preview already feels polished and surprising. Motion should clarify an action or state change, not become a decorative obstacle.

## Reference source

Amicro is an MIT-licensed React and Motion component collection with copy-to-code CLI and shadcn registry delivery:

- Official site: https://amicro.vercel.app/
- Official repository: https://github.com/Subhan-code/Amicro--Micro-transitions-
- Package: `@subhanhq/amicro`
- Reviewed source tree: `52b9915287499165a47590989cf586263a0bef1f`

The library requires React 18/19, Tailwind and Motion. Its CLI is one implementation option for a compatible React project; the user should not have to choose or operate that stack.

## What ChatWeb should absorb

- Press feedback: a short spring compression and release confirms that a button received the touch.
- State morphing: let the icon, label and color move together when an action changes from ready to working, success or failure.
- Staggered reveal: introduce related items in a short sequence so the user sees hierarchy; stop after the initial reveal.
- Card depth: use arc, stack or cover-flow movement only when the user is comparing choices, steps or time states.
- Text reveal: use restrained word or line reveals for an opening message, never for long instructions or rapidly changing data.
- Data feedback: animate the changed value or chart mark, while leaving labels and scales stable.

Prefer `transform` and `opacity` animations. Keep touch targets at least 44 px, make every hover interaction work by touch or click, and provide `prefers-reduced-motion` behavior that preserves the same state information without movement.

## Delivery choice

The default first preview combines three restrained layers:

1. one main visual effect that establishes the work's personality;
2. one immediate response to the user's primary action;
3. one result, success or state-transition effect.

ChatWeb ships three flagship one-file treatments for the most common beginner scenes:

- `editorial-signal`: a spatial-glass classroom poll with ambient depth, spring press feedback and a count halo/burst.
- `device-console`: a mission-console hardware simulation with a signal scope, physical control feedback and a disconnected/connected state lock.
- `reaction-rush`: a stage-like timed interaction with spotlight atmosphere, target feedback and a score/end-state change.

When `direction_id` is omitted or set to `auto`, `chatmaker-web` chooses the first curated flagship for the requested project kind. Existing direction IDs remain valid. The output stays native, offline and single-file; these treatments are methods learned from premium micro-interactions, not copied React components.

Choose them from the content. A classroom draw can use a card shuffle, spring selection and brief celebration. A hardware controller can use a live glow, physical press and clear state morph. A presentation page can use layered depth, text reveal and a focused section transition.

For a beginner, classroom tool or one-file hardware page, recreate the selected interaction with native HTML, CSS and JavaScript so the result opens directly and remains offline-capable.

For a React project that supports Tailwind and Motion, a selected Amicro component may be added after checking its current registry entry and dependencies. Use the CLI only when it materially helps the accepted work, not merely to decorate a simple page. If substantial upstream code is copied, retain the MIT attribution required by its license.

Use one or two signature interactions per page. A page with spring buttons, magnetic cursor effects, 3D cards, animated text and continuous background motion all at once is harder to understand and usually feels less premium.
