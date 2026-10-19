#include "oldj/Engine.h"

#include <algorithm>
#include <cmath>

namespace oldj
{

void Engine::prepare (double newSampleRate, int /*maxBlockSize*/)
{
    sampleRate.store (newSampleRate);
    tone.prepare (newSampleRate);

    toneGain.reset (newSampleRate, rampSeconds);
    toneGain.setCurrentAndTargetValue (toneEnabled.load() ? 1.0f : 0.0f);

    masterGain.reset (newSampleRate, rampSeconds);
    masterGain.setCurrentAndTargetValue (masterGainTarget.load());
}

void Engine::release()
{
    sampleRate.store (0.0);
}

void Engine::setMasterGain (float linearGain) noexcept
{
    masterGainTarget.store (std::clamp (linearGain, 0.0f, 4.0f));
}

void Engine::process (float* const* outputs, int numChannels, int numSamples) noexcept
{
    for (int ch = 0; ch < numChannels; ++ch)
        if (outputs[ch] != nullptr)
            std::fill_n (outputs[ch], numSamples, 0.0f);

    toneGain.setTargetValue (toneEnabled.load() ? 1.0f : 0.0f);
    masterGain.setTargetValue (masterGainTarget.load());

    if (! toneGain.isSmoothing() && toneGain.getCurrentValue() == 0.0f)
    {
        tone.reset();
        masterGain.skip (numSamples);
        publishPeak (0.0f);
        return;
    }

    float blockPeak = 0.0f;

    for (int i = 0; i < numSamples; ++i)
    {
        const auto s = tone.nextSample() * testToneLevel * toneGain.getNextValue() * masterGain.getNextValue();
        blockPeak = std::max (blockPeak, std::abs (s));

        for (int ch = 0; ch < numChannels; ++ch)
            if (outputs[ch] != nullptr)
                outputs[ch][i] = s;
    }

    publishPeak (blockPeak);
}

void Engine::publishPeak (float blockPeak) noexcept
{
    auto current = masterPeak.load (std::memory_order_relaxed);

    while (blockPeak > current
           && ! masterPeak.compare_exchange_weak (current, blockPeak, std::memory_order_relaxed))
    {
    }
}

} // namespace oldj
