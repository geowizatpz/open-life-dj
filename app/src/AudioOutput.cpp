#include "AudioOutput.h"

namespace oldj
{

void AudioOutput::audioDeviceIOCallbackWithContext (const float* const*, int,
                                                    float* const* outputs, int numOutputs, int numSamples,
                                                    const juce::AudioIODeviceCallbackContext&)
{
    engine.process (outputs, numOutputs, numSamples);
}

void AudioOutput::audioDeviceAboutToStart (juce::AudioIODevice* device)
{
    engine.prepare (device->getCurrentSampleRate(), device->getCurrentBufferSizeSamples());
}

void AudioOutput::audioDeviceStopped()
{
    engine.release();
}

} // namespace oldj
