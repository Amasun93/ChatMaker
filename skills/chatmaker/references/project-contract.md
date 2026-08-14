# ChatMaker Project Contract

## Choose the smallest route

- Hardware-only effect: use ChatDuino.
- Browser-only interaction: use ChatWeb.
- Browser controls or displays hardware: define the request/response contract, then use both.

## Define acceptance before building

Write one observable acceptance statement for each subsystem. Example: “pressing the phone button sends `POST /led` with `{\"on\": true}`” is a web-device contract; “the physical LED turns on and stays on after the response” is a separate physical acceptance statement.

## Keep the user in the creative role

Let the user judge the idea, feeling, and visible result. Handle frameworks, libraries, build tools, and validation internally unless a technical choice changes the user's outcome. When the user has only a direction, narrow it with one or two questions and offer two or three curated concepts.

## Completion language

Name the evidence obtained and the gate still open. Use `planned`, `unverified`, `verified`, or `failed`; never use “done” to hide a mixture of those states.
