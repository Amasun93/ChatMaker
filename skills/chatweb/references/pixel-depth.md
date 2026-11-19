# Pixel depth and camera motion

Use this reference when the visible goal depends on pixel-art volume, a movable camera, or exposing the layers of a pixel object. A flat retro palette, a classroom timer, or a standard reaction game can use the existing ChatWeb directions.

## Choose what the scene needs

| Visible goal | Technique |
| --- | --- |
| Rotate a display object or reveal its construction | Draw pixel cross-sections around one pivot, offset them along the projected vertical axis, and paint from far to near. An exploded view changes the spacing between the same slices. Project the pivot and backdrop consistently so the object stays in place. |
| Bank, pitch, or view a moving object from different elevations | Treat the colored pixels of each slice as occupied cells in a 3D grid. Transform them by the object's pose, project through the camera and draw by camera depth. A lightweight painter's sort works for a small opaque object. Add per-pixel depth only if overlapping geometry needs it. |
| Suggest travel past a landscape | Anchor nearby markers to world positions. Move distant layers more slowly and preserve a horizon. Foreground passes, a small camera zoom, and one event-driven effect can convey speed with a small scene. |

## Build the first playable version

1. Keep the requested motion or play loop. Start with one object, one camera and one action that visibly changes the scene. Add another view when it helps the user explore, navigate or compare.
2. Use a small Canvas 2D drawing buffer, for example 360 × 202, and scale it up with crisp pixel edges. Use `image-rendering: pixelated` for CSS scaling and disable canvas smoothing when scaling images in the drawing buffer. Keep controls and readable text in the DOM at screen resolution.
3. Build original slices from silhouettes and a compact palette. Prepare stable geometry once, skip points behind the near plane, and bound the number of terrain samples and particles. Draw solid terrain, distant details, objects and feedback in a consistent depth order.
4. Advance the scene with elapsed time and clamp long frame gaps. Let the same action state drive the object's pose, camera motion and feedback. Use a time-based damped camera; a pause, restart or camera change must preserve the intended game state.
5. Map the same actions to pointer or touch and keyboard. Show controls before the first action. Provide a visible response to collection, completion and restart. When reduced motion is preferred, suppress extra camera sway or flashes while keeping the steering and stage readable.
6. Use an offline single-file page by default. Where the planner's curated templates cover the action, reuse them. Where projection, input or scene timing requires custom code, keep the rendering and the play state separate inside the same HTML, then preview and verify through ChatWeb.

## Verify the effect

- Open the HTML from disk with network access disabled. Check for console errors and outgoing requests.
- Compare at least two orientations. Check that the silhouette, visible layers and occlusion change as intended and that image scaling keeps the pixels crisp.
- Exercise the core interaction on desktop and at a phone viewport. Check each input path, a result that visibly changes, and reset or restart. For a flight scene, also verify that a camera change leaves progress intact and that touch release clears the held action.
- Capture performance on the intended browser before quoting a frame-rate result. Rendering size, geometry count and screen refresh each affect the result.

## Reference implementation

[Salt Lake Weather Patrol](../assets/pixel-depth-glider.html) is an original, offline Canvas 2D scene with a slice-based glider, projected beacons, two camera poses and one collection loop. Read the rendering and input sections when adapting the technique to a different subject.

Technical sources: [Dash's fighter project](https://remix.ui8.ai/fly), [the third-party fighter-fly implementation](https://github.com/AryanRajMaurya/fighter-fly/tree/25a5401c407177665b5c810a3684c060469ddb80), and [loktar00's MIT-licensed slice examples](https://github.com/loktar00/sprite-stacking/tree/25a6cfdc8b8f142b4cc297dd34bba24841d12213). The bundled example uses original code and artwork.
