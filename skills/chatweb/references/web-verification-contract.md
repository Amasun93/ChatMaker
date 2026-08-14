# Web Verification Contract

Verify and report these outcomes independently:

1. All expected files load.
2. The page has no uncaught console errors.
3. The primary control can be operated by mouse and touch-sized targets.
4. Loading, disconnected, success, and failure states are visibly distinguishable.
5. The local preview binds to localhost unless LAN access was explicitly requested.
6. A simulated hardware page says `模拟` visibly and begins disconnected.
7. For a real hardware claim, the browser exchanged a real request with the device; a simulation toggle is not evidence.
8. A physical effect was confirmed separately from the browser response.

Record the page title, viewport, primary control before and after interaction, touch-target dimensions, console error count, and exact preview host. Keep `generated`, `browser_interaction`, `hardware_connectivity`, and `physical_effect` as separate results.

Capture screenshots only after the relevant state has fully loaded. If a screenshot exposes a visual defect, fix it and capture a fresh image before delivery.

