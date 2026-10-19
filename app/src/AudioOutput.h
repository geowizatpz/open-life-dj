#pragma once

#include "oldj/Engine.h"

#include <juce_audio_devices/juce_audio_devices.h>

namespace oldj
{

// Bridges the OS audio device to the engine. Lives on the audio thread; keep it thin.
class AudioOutput final : public juce::AudioIODeviceCallback
{
public:
    explicit AudioOutput (Engine& e) : engine (e) {}

    void audioDeviceIOCallbackWithContext (const float* const* inputs, int numInputs,
                                           float* const* outputs, int numOutputs, int numSamples,
                                           const juce::AudioIODeviceCallbackContext& context) override;
    void audioDeviceAboutToStart (juce::AudioIODevice* device) override;
    void audioDeviceStopped() override;

private:
    Engine& engine;
};

} // namespace oldj
