#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace deejay {

struct StretchQuality {
    float formantPreservation{0.5f};
    float transientSensitivity{0.5f};
    bool highQuality{true};
};

class TimeStretchPitchProcessor {
public:
    struct Parameters {
        double tempoRatio{1.0};
        double pitchSemitones{0.0};
        StretchQuality quality{};
    };

    struct EndpointDescriptor {
        std::string id;
        std::string label;
        double minimum{0.0};
        double maximum{0.0};
        double defaultValue{0.0};
        bool integer{false};
        std::string description;
    };

    TimeStretchPitchProcessor(double sampleRate, int channelCount, Parameters defaults = {});

    void setParameters(const Parameters &parameters);
    Parameters getParameters() const;

    std::vector<EndpointDescriptor> describeEndpoints() const;

    size_t process(const float *input, size_t frames, std::vector<float> &output);
    size_t getLatencySamples() const;
    void reset();

    int channelCount() const noexcept { return channelCount_; }
    double sampleRate() const noexcept { return sampleRate_; }

private:
    void configureProcessor();

    double sampleRate_{0.0};
    int channelCount_{0};
    Parameters parameters_{};

#ifdef DEEJAY_HAVE_RUBBERBAND
    class RubberBandAdapter;
    std::unique_ptr<RubberBandAdapter> processor_;
#else
    size_t simulatedLatencySamples_{0};
#endif
};

} // namespace deejay

