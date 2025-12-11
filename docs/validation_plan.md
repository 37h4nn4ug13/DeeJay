# Time-stretch and Pitch-shift Validation Plan

This document describes how to exercise the new real-time time-stretch and pitch-shift path for quality and stability.

## Goals
- Verify the Rubber Band based processor remains stable across time-stretch and pitch ranges (0.5x–2.5x tempo, ±12 semitones pitch).
- Confirm latency is reported and compensated so recorded audio remains phase-aligned with the dry path.
- Capture subjective notes about quality for transient-heavy and harmonic material.

## Test Matrix
| Material | Tempo Ratios | Pitch Steps | Expectations |
| --- | --- | --- | --- |
| Drum loop (percussive) | 0.5x, 1.0x, 1.5x, 2.0x | -12, 0, +7 | Transients should remain crisp; no flamming after latency compensation. |
| Vocal phrase (legato) | 0.75x, 1.0x, 1.25x | -3, 0, +3, +12 | Minimal formant drift with preservation enabled. |
| Polyphonic keys | 0.5x, 1.0x, 1.8x | -5, 0, +5 | Chords stay in tune without chorusing artifacts. |

## Procedure
1. Build with Rubber Band support (`DEEJAY_ENABLE_RUBBERBAND=ON`) and note reported latency from `LatencyCompensatedProcessor::totalLatencySamples`.
2. Route the processor in an offline render and in a low-latency real-time context to compare.
3. For each test cell, record a dry reference and a processed take, aligning them using the reported latency.
4. Perform null tests (phase inversion against aligned dry) to check compensation correctness.
5. Listen for stutters, warbling, or runaway gain at extreme parameters; log any anomalies.

## Acceptance Criteria
- No crashes or buffer under-runs when tempo/pitch parameters are automated quickly.
- Latency compensation keeps transients aligned to within ±1 sample when compared to dry reference.
- Subjective quality remains musical without excessive metallic artifacts across the matrix.

