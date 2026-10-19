#include "oldj/TestTone.h"

#include <cmath>
#include <numbers>

namespace oldj
{

void TestTone::prepare (double newSampleRate) noexcept
{
    sampleRate = newSampleRate > 0.0 ? newSampleRate : 48000.0;
    setFrequency (frequency);
    reset();
}

void TestTone::setFrequency (double hz) noexcept
{
    frequency = hz;
    increment = frequency / sampleRate;
}

float TestTone::nextSample() noexcept
{
    const auto s = std::sin (2.0 * std::numbers::pi * phase);
    phase += increment;
    phase -= std::floor (phase);
    return static_cast<float> (s);
}

} // namespace oldj
