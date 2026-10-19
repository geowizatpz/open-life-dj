#pragma once

namespace oldj
{

// Plain sine oscillator used to verify the audio path end to end. Audio-thread only.
class TestTone
{
public:
    void prepare (double sampleRate) noexcept;
    void reset() noexcept { phase = 0.0; }
    void setFrequency (double hz) noexcept;

    float nextSample() noexcept;

private:
    double sampleRate = 48000.0;
    double frequency = 440.0;
    double phase = 0.0;       // 0..1
    double increment = 440.0 / 48000.0;
};

} // namespace oldj
