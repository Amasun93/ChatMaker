# ChatWeb mini-game creation guide

## Creative-partner philosophy

Start from the experience, not the technology. Discover three things in plain language:

1. What should the player feel?
2. What action will the player repeat?
3. What visible event means success or the end?

When the idea is clear, offer two or three genuinely different play directions. Do not make the user choose a framework. Generate one small playable version, let the user try it, and then tune difficulty, appearance, feedback, and rules from what they observed.

A minimum playable loop contains:

`start -> act -> immediate feedback -> score/progress -> ending -> restart`

Games may teach something, support a classroom, or exist simply because they are fun. A quiz is one possible mechanic, not the default meaning of an educational game.

## Beginner play patterns

### Reaction rush

The target appears, the player taps it, and the target moves. Vary time, target size, distractors, combo rules, and theme without changing the basic loop.

### Dodge and collect

The player moves one object, collects rewards, and avoids hazards. Keep the first version to one screen, one movement axis, and one clear scoring rule.

### Drag puzzle

The player moves pieces into matching locations. Always provide a touch-safe alternative: select a piece, then select its destination.

## Technology ladder

1. Default: one offline HTML file using DOM, Canvas, CSS, and JavaScript.
2. Optional middle layer: p5.js or p5play for visual experiments, sprites, and collisions.
3. Advanced: Phaser for scenes, richer physics, cameras, assets, and multi-level games.

Do not add an engine merely because the page is a game. Introduce it when it makes the accepted mechanic simpler and more reliable.

## Reference projects

- MDN pure JavaScript Breakout: <https://developer.mozilla.org/en-US/docs/Games/Tutorials/2D_Breakout_game_pure_JavaScript>
- p5.js official examples: <https://p5js.org/examples/>
- p5play sprite and physics guide: <https://p5play.org/learn/sprite>
- Phaser official examples: <https://phaser.io/examples/v3/>
- GDevelop official examples and templates: <https://gdevelop.io/game-example>

GDevelop is a product-flow reference for modifying playable examples. ChatWeb remains conversation-first and exports ordinary web files. Do not use the archived Kaboom project as a new long-term runtime dependency.

## Lightweight acceptance

For an early template, verify only the relevant facts:

- The HTML loads without an uncaught console error.
- Start begins a playable state.
- The primary mouse or touch interaction changes the game.
- The game can reach an ending and restart.
- Movement games also respond to keyboard controls.
- The page does not require a network connection.
