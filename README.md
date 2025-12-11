# DeeJay

Minimal C++ audio sandbox built with PortAudio and CMake. The current setup opens a low-latency output stream and renders silence through a simple callback so the audio I/O pipeline can be verified before adding DSP.

## Building

The project uses CMake with a FetchContent build of [PortAudio](https://www.portaudio.com/). On Linux, ensure ALSA development headers are available (e.g., `sudo apt-get install libasound2-dev`). If you already have PortAudio installed, configure with `-DDEEJAY_USE_SYSTEM_PORTAUDIO=ON` to avoid downloading sources.

```bash
cmake -S . -B build
cmake --build build
```

## Running

The `deejay_audio` binary accepts a few switches to experiment with buffer sizes and sample rates:

```bash
./build/deejay_audio --frames 128 --sample-rate 48000 --duration-seconds 2 --channels 2
```

While running, the program logs the requested buffer size, reported latency, and how many frames of silence were rendered.

## Testing / CI

A smoke test is registered with CTest to ensure the binary launches. Continuous builds can be exercised locally by running:

```bash
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build
```

GitHub Actions are configured in `.github/workflows/build.yml` to compile the audio core on every push and pull request.
