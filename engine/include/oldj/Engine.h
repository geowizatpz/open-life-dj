#pragma once

#include "oldj/TestTone.h"

#include <juce_audio_basics/juce_audio_basics.h>

#include <atomic>

namespace oldj
{

/*  The audio engine root.

    Threading contract (applies to the whole engine):
      - process() runs on the real-time audio thread: no allocation, no locks,
        no file or console I/O, no waiting on other threads.
      - set*() / get*() may be called from any thread; they only touch atomics.
      - prepare() / release() are called by the audio device while it is stopped.
*/
class Engine
{
public:
    static constexpr float testToneLevel = 0.125f;      // -18 dBFS
    static constexpr double rampSeconds = 0.02;         // click-free on/off and gain changes

    void prepare (double sampleRate, int maxBlockSize);
    void release();

    void process (float* const* outputs, int numChannels, int numSamples) noexcept;

    // --- control, any thread
    void setTestToneEnabled (bool shouldBeOn) noexcept   { toneEnabled.store (shouldBeOn); }
    bool isTestToneEnabled() const noexcept              { return toneEnabled.load(); }

    void setMasterGain (float linearGain) noexcept;
    float getMasterGain() const noexcept                 { return masterGainTarget.load(); }

    // Highest absolute output sample since the last call (for meters); resets to 0.
    float takeMasterPeak() noexcept                      { return masterPeak.exchange (0.0f); }

    double getSampleRate() const noexcept                { return sampleRate.load(); }

private:
    void publishPeak (float blockPeak) noexcept;

    std::atomic<bool> toneEnabled { false };
    std::atomic<float> masterGainTarget { 1.0f };
    std::atomic<float> masterPeak { 0.0f };
    std::atomic<double> sampleRate { 0.0 };

    // audio thread state
    TestTone tone;
    juce::SmoothedValue<float> toneGain { 0.0f };
    juce::SmoothedValue<float> masterGain { 1.0f };
};

} // namespace oldj
