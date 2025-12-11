#pragma once

#include "TimeStretchPitchProcessor.h"

#include <vector>

namespace deejay {

class LatencyCompensatedProcessor {
public:
    struct Controls {
        double tempoRatio{1.0};
        double pitchSemitones{0.0};
        int manualLatencySamples{0};
    };

    struct ControlEndpoint {
        std::string id;
        std::string label;
        std::string type; // slider or numeric
        double minimum;
        double maximum;
        double defaultValue;
        std::string description;
    };

    LatencyCompensatedProcessor(double sampleRate, int channelCount);

    void updateControls(const Controls &controls);
    Controls currentControls() const;

    size_t processBlock(const float *input, size_t frames, std::vector<float> &output);
    size_t totalLatencySamples() const;

    std::vector<ControlEndpoint> controlEndpoints() const;

private:
    void refreshPendingLatency();

    TimeStretchPitchProcessor processor_;
    Controls controls_{};
    size_t pendingLatencySamples_{0};
    int channelCount_{0};
};

} // namespace deejay

