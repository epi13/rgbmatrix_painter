# Poor Louis Farms LED display

- All display animations and previews must be true 128×128 pixel assets. Do not create or present enlarged concept images or previews. Preserve the established Poor Louis Farms branding and artwork unless the user explicitly requests a change.
- Read [the LED matrix workflow](docs/led-matrix-workflow.md) for the Pi connection, native animation commands, deployment checks, and recovery.
- Use the existing `poor-louis-farms.service` on `mncs-pi.local`. Preserve the installed GPIO mapping, panel order, driver, and system configuration. Use `deploy/matrixctl` for seasonal changes and keep the Halloween renderer as the fallback.
- Validate the actual asset before deployment. Report which checks ran on the Pi and whether someone saw the physical display. Keep SSH credentials out of the repository and conversation.
