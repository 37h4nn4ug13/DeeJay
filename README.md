# DeeJay

Audio processing scaffolding focused on time-stretching and pitch shifting.

## Building
```bash
cmake -B build -S . -DDEEJAY_ENABLE_RUBBERBAND=ON
cmake --build build
```
If the Rubber Band Library is unavailable, the code will fall back to a stub implementation so the rest of the engine can still compile.

## Components
- `TimeStretchPitchProcessor`: wraps Rubber Band (or a stub) to provide tempo and pitch control with endpoint descriptors for sliders and numeric inputs.
- `LatencyCompensatedProcessor`: adds latency-aware buffering and exposes UI-friendly control endpoints, including manual latency override.

## Validation
See `docs/validation_plan.md` for the manual test plan covering tempo/pitch sweeps and quality checks.

