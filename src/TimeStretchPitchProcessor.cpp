#include "TimeStretchPitchProcessor.h"

#ifdef DEEJAY_HAVE_RUBBERBAND
#include <rubberband/RubberBandStretcher.h>
#endif

#include <algorithm>
#include <cmath>

namespace deejay {

namespace {
constexpr double semitonesToRatio(double semitones) {
    return std::pow(2.0, semitones / 12.0);
}
}

#ifdef DEEJAY_HAVE_RUBBERBAND
class TimeStretchPitchProcessor::RubberBandAdapter {
public:
    RubberBandAdapter(double sampleRate, int channelCount, const Parameters &parameters)
        : channelCount_(channelCount) {
        using RubberBand::RubberBandStretcher;

        int options = RubberBandStretcher::OptionProcessRealTime |
                      RubberBandStretcher::OptionPitchHighQuality |
                      RubberBandStretcher::OptionThreadingAuto;

        if (!parameters.quality.highQuality) {
            options |= RubberBandStretcher::OptionPitchHighSpeed;
        }

        if (parameters.quality.transientSensitivity > 0.6f) {
            options |= RubberBandStretcher::OptionTransientsSmooth;
        }

        if (parameters.quality.formantPreservation > 0.6f) {
            options |= RubberBandStretcher::OptionFormantPreserved;
        }

        stretcher_ = std::make_unique<RubberBandStretcher>(sampleRate, channelCount_, options);
        setParameters(parameters);
    }

    void setParameters(const Parameters &parameters) {
        parameters_ = parameters;
        stretcher_->setPitchScale(semitonesToRatio(parameters_.pitchSemitones));
        stretcher_->setTimeRatio(parameters_.tempoRatio);
    }

    Parameters getParameters() const { return parameters_; }

    size_t process(const float *input, size_t frames, std::vector<float> &output) {
        std::vector<const float *> channels(channelCount_);
        for (int ch = 0; ch < channelCount_; ++ch) {
            channels[ch] = input + ch * frames;
        }

        stretcher_->process(channels.data(), frames, false);
        const auto available = static_cast<size_t>(stretcher_->available());

        output.resize(available * static_cast<size_t>(channelCount_));
        std::vector<float *> outputChannels(channelCount_);
        for (int ch = 0; ch < channelCount_; ++ch) {
            outputChannels[ch] = output.data() + static_cast<size_t>(ch) * available;
        }

        stretcher_->retrieve(outputChannels.data(), available);
        return available;
    }

    size_t latency() const { return static_cast<size_t>(stretcher_->getLatency()); }

    void reset() { stretcher_->reset(); }

private:
    int channelCount_;
    Parameters parameters_{};
    std::unique_ptr<RubberBand::RubberBandStretcher> stretcher_;
};
#endif

TimeStretchPitchProcessor::TimeStretchPitchProcessor(double sampleRate, int channelCount, Parameters defaults)
    : sampleRate_(sampleRate), channelCount_(channelCount), parameters_(defaults) {
    configureProcessor();
}

void TimeStretchPitchProcessor::setParameters(const Parameters &parameters) {
    parameters_ = parameters;
#ifdef DEEJAY_HAVE_RUBBERBAND
    if (processor_) {
        processor_->setParameters(parameters_);
    }
#else
    simulatedLatencySamples_ = static_cast<size_t>(sampleRate_ * 0.01); // 10ms placeholder
#endif
}

TimeStretchPitchProcessor::Parameters TimeStretchPitchProcessor::getParameters() const { return parameters_; }

std::vector<TimeStretchPitchProcessor::EndpointDescriptor> TimeStretchPitchProcessor::describeEndpoints() const {
    return {
        {"tempo", "Tempo Ratio", 0.5, 2.5, parameters_.tempoRatio, false, "Time-stretch control exposed to slider and numeric input."},
        {"pitch", "Pitch (semitones)", -12.0, 12.0, parameters_.pitchSemitones, false, "Pitch shift in semitones, mapped to rotary or numeric control."},
        {"formant", "Formant Preservation", 0.0, 1.0, parameters_.quality.formantPreservation, false, "Blend between neutral and formant-preserving processing."},
        {"transient", "Transient Sensitivity", 0.0, 1.0, parameters_.quality.transientSensitivity, false, "Higher values keep percussive edges sharper."}
    };
}

size_t TimeStretchPitchProcessor::process(const float *input, size_t frames, std::vector<float> &output) {
#ifdef DEEJAY_HAVE_RUBBERBAND
    if (!processor_) {
        configureProcessor();
    }
    return processor_->process(input, frames, output);
#else
    const auto samples = frames * static_cast<size_t>(channelCount_);
    output.assign(input, input + samples);
    return frames;
#endif
}

size_t TimeStretchPitchProcessor::getLatencySamples() const {
#ifdef DEEJAY_HAVE_RUBBERBAND
    return processor_ ? processor_->latency() : 0;
#else
    return simulatedLatencySamples_;
#endif
}

void TimeStretchPitchProcessor::reset() {
#ifdef DEEJAY_HAVE_RUBBERBAND
    if (processor_) {
        processor_->reset();
    }
#endif
}

void TimeStretchPitchProcessor::configureProcessor() {
#ifdef DEEJAY_HAVE_RUBBERBAND
    processor_ = std::make_unique<RubberBandAdapter>(sampleRate_, channelCount_, parameters_);
#else
    simulatedLatencySamples_ = static_cast<size_t>(sampleRate_ * 0.01);
#endif
}

} // namespace deejay

