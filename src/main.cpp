#include <portaudio.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <exception>
#include <iostream>
#include <string>
#include <thread>

namespace
{
struct CallbackData
{
    std::uint64_t framesRendered{};
    int channels{2};
};

int audioCallback(const void* /*input*/, void* output, unsigned long framesPerBuffer, const PaStreamCallbackTimeInfo* /*timeInfo*/, PaStreamCallbackFlags /*statusFlags*/, void* userData)
{
    auto* callbackData = static_cast<CallbackData*>(userData);
    const auto channels = callbackData ? callbackData->channels : 2;

    auto* out = static_cast<float*>(output);
    const auto samples = framesPerBuffer * static_cast<unsigned long>(channels);
    std::fill(out, out + samples, 0.0f);

    if (callbackData)
    {
        callbackData->framesRendered += framesPerBuffer;
    }

    return paContinue;
}

struct SessionConfig
{
    double sampleRate{48'000.0};
    unsigned long framesPerBuffer{128};
    double durationSeconds{2.0};
    int channels{2};
};

SessionConfig parseArgs(int argc, char** argv)
{
    SessionConfig config;

    for (int i = 1; i < argc; ++i)
    {
        const std::string arg = argv[i];
        if ((arg == "--frames" || arg == "-f") && i + 1 < argc)
        {
            config.framesPerBuffer = static_cast<unsigned long>(std::stoul(argv[++i]));
        }
        else if ((arg == "--sample-rate" || arg == "-r") && i + 1 < argc)
        {
            config.sampleRate = std::stod(argv[++i]);
        }
        else if ((arg == "--duration-seconds" || arg == "-d") && i + 1 < argc)
        {
            config.durationSeconds = std::stod(argv[++i]);
        }
        else if (arg == "--channels" && i + 1 < argc)
        {
            config.channels = std::stoi(argv[++i]);
        }
        else if (arg == "--help" || arg == "-h")
        {
            std::cout << "Usage: deejay_audio [options]\n"
                      << "  --frames, -f            Frames per buffer (default: 128)\n"
                      << "  --sample-rate, -r       Sample rate (default: 48000)\n"
                      << "  --duration-seconds, -d  Run time in seconds (default: 2)\n"
                      << "  --channels              Number of output channels (default: 2)\n"
                      << "  --help, -h              Show this message\n";
            std::exit(0);
        }
    }

    return config;
}

void checkPaError(PaError error, const std::string& context)
{
    if (error != paNoError)
    {
        throw std::runtime_error(context + ": " + Pa_GetErrorText(error));
    }
}

} // namespace

int main(int argc, char** argv)
{
    try
    {
        const auto config = parseArgs(argc, argv);
        CallbackData callbackData{};
        callbackData.channels = config.channels;

        checkPaError(Pa_Initialize(), "Failed to initialize PortAudio");

        PaStream* stream = nullptr;
        checkPaError(
            Pa_OpenDefaultStream(&stream, 0, config.channels, paFloat32, config.sampleRate, config.framesPerBuffer, audioCallback, &callbackData),
            "Failed to open default output stream");

        const PaStreamInfo* info = Pa_GetStreamInfo(stream);
        std::cout << "Opening stream with " << config.channels << " channels\n";
        std::cout << "Sample rate: " << config.sampleRate << " Hz\n";
        std::cout << "Requested frames per buffer: " << config.framesPerBuffer << "\n";
        if (info)
        {
            std::cout << "Reported output latency: " << info->outputLatency << " seconds\n";
        }

        checkPaError(Pa_StartStream(stream), "Failed to start stream");

        if (config.durationSeconds > 0.0)
        {
            const auto sleepDuration = std::chrono::duration<double>(config.durationSeconds);
            std::this_thread::sleep_for(std::chrono::duration_cast<std::chrono::milliseconds>(sleepDuration));
        }

        checkPaError(Pa_StopStream(stream), "Failed to stop stream");
        checkPaError(Pa_CloseStream(stream), "Failed to close stream");
        checkPaError(Pa_Terminate(), "Failed to terminate PortAudio");

        std::cout << "Rendered approximately " << callbackData.framesRendered << " frames of silence." << std::endl;
    }
    catch (const std::exception& ex)
    {
        std::cerr << "Error: " << ex.what() << std::endl;
        return 1;
    }

    return 0;
}
