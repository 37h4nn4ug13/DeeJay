#include "LatencyCompensatedProcessor.h"

#include <algorithm>

namespace deejay {

LatencyCompensatedProcessor::LatencyCompensatedProcessor(double sampleRate, int channelCount)
    : processor_(sampleRate, channelCount), channelCount_(channelCount) {
    refreshPendingLatency();
}

void LatencyCompensatedProcessor::updateControls(const Controls &controls) {
    controls_ = controls;
    processor_.setParameters({controls.tempoRatio, controls.pitchSemitones, {}});
    refreshPendingLatency();
}

LatencyCompensatedProcessor::Controls LatencyCompensatedProcessor::currentControls() const { return controls_; }

size_t LatencyCompensatedProcessor::processBlock(const float *input, size_t frames, std::vector<float> &output) {
    std::vector<float> processed;
    const size_t produced = processor_.process(input, frames, processed);

    output.clear();

    const size_t samplesPerFrame = static_cast<size_t>(channelCount_);
    const size_t pendingSamples = std::min(pendingLatencySamples_, produced * samplesPerFrame);
    if (pendingSamples > 0) {
        output.resize(pendingSamples, 0.0f);
        pendingLatencySamples_ -= pendingSamples;
    }

    output.insert(output.end(), processed.begin(), processed.end());

    // If there is still latency remaining after this block, pad with extra zeros to preserve alignment.
    if (pendingLatencySamples_ > 0) {
        output.resize(output.size() + pendingLatencySamples_, 0.0f);
        pendingLatencySamples_ = 0;
    }

    return produced;
}

size_t LatencyCompensatedProcessor::totalLatencySamples() const {
    return processor_.getLatencySamples() + static_cast<size_t>(std::max(0, controls_.manualLatencySamples));
}

std::vector<LatencyCompensatedProcessor::ControlEndpoint> LatencyCompensatedProcessor::controlEndpoints() const {
    return {
        {"tempo", "Tempo", "slider", 0.5, 2.5, controls_.tempoRatio, "User-facing tempo slider bound to time-stretch ratio."},
        {"pitch", "Pitch", "slider", -12.0, 12.0, controls_.pitchSemitones, "Pitch slider or numeric input in semitones."},
        {"manualLatency", "Manual Latency", "numeric", 0.0, 4096.0, static_cast<double>(controls_.manualLatencySamples),
         "Additional latency compensation in samples, editable via numeric input."}
    };
}

void LatencyCompensatedProcessor::refreshPendingLatency() {
    pendingLatencySamples_ = totalLatencySamples();
}

} // namespace deejay

