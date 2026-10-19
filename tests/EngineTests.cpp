#include "oldj/Engine.h"

#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>

#include <array>
#include <cmath>
#include <vector>

namespace
{
constexpr double sampleRate = 48000.0;
constexpr int blockSize = 256;

// Runs the engine for `seconds` and returns the left channel.
std::vector<float> run (oldj::Engine& engine, double seconds)
{
    std::vector<float> out;
    std::array<float, blockSize> left {}, right {};
    std::array<float*, 2> channels { left.data(), right.data() };

    const auto total = static_cast<int> (seconds * sampleRate);
    for (int done = 0; done < total; done += blockSize)
    {
        engine.process (channels.data(), 2, blockSize);
        out.insert (out.end(), left.begin(), left.end());
        REQUIRE (left == right);
    }
    return out;
}

float rms (const std::vector<float>& x, size_t from)
{
    double sum = 0.0;
    for (auto i = from; i < x.size(); ++i)
        sum += double (x[i]) * x[i];
    return float (std::sqrt (sum / double (x.size() - from)));
}

oldj::Engine& prepared (oldj::Engine& e)
{
    e.prepare (sampleRate, blockSize);
    return e;
}
} // namespace

TEST_CASE ("Engine is silent by default")
{
    oldj::Engine engine;
    const auto out = run (prepared (engine), 0.5);

    for (auto s : out)
        REQUIRE (s == 0.0f);

    REQUIRE (engine.takeMasterPeak() == 0.0f);
}

TEST_CASE ("Test tone plays at -18 dBFS and 440 Hz")
{
    oldj::Engine engine;
    prepared (engine).setTestToneEnabled (true);
    const auto out = run (engine, 1.0);

    // steady state after the ramp: sine RMS = peak / sqrt(2)
    const auto steady = size_t (0.1 * sampleRate);
    REQUIRE (rms (out, steady) == Catch::Approx (oldj::Engine::testToneLevel / std::sqrt (2.0f)).epsilon (0.01));

    int upwardCrossings = 0;
    for (auto i = steady + 1; i < out.size(); ++i)
        if (out[i - 1] < 0.0f && out[i] >= 0.0f)
            ++upwardCrossings;

    const auto measuredHz = upwardCrossings / (double (out.size() - steady) / sampleRate);
    REQUIRE (measuredHz == Catch::Approx (440.0).margin (2.0));

    REQUIRE (engine.takeMasterPeak() == Catch::Approx (oldj::Engine::testToneLevel).epsilon (0.01));
    REQUIRE (engine.takeMasterPeak() == 0.0f);   // reading resets the peak
}

TEST_CASE ("Switching the tone on and off is click-free")
{
    oldj::Engine engine;
    prepared (engine).setTestToneEnabled (true);
    auto out = run (engine, 0.2);
    engine.setTestToneEnabled (false);
    const auto tail = run (engine, 0.2);
    out.insert (out.end(), tail.begin(), tail.end());

    // a 440 Hz sine at this level moves at most 2*pi*f/sr*A per sample; a click would jump far more
    const auto maxStep = float (2.0 * 3.14159265 * 440.0 / sampleRate) * oldj::Engine::testToneLevel * 1.05f;
    for (size_t i = 1; i < out.size(); ++i)
        REQUIRE (std::abs (out[i] - out[i - 1]) <= maxStep);

    for (auto i = out.size() - 1000; i < out.size(); ++i)
        REQUIRE (out[i] == 0.0f);
}

TEST_CASE ("Master gain scales and clamps the output")
{
    oldj::Engine engine;
    prepared (engine).setTestToneEnabled (true);

    engine.setMasterGain (0.0f);
    auto out = run (engine, 0.3);
    REQUIRE (rms (out, size_t (0.1 * sampleRate)) == Catch::Approx (0.0f).margin (1e-6));

    engine.setMasterGain (-3.0f);
    REQUIRE (engine.getMasterGain() == 0.0f);
    engine.setMasterGain (100.0f);
    REQUIRE (engine.getMasterGain() == 4.0f);
}

TEST_CASE ("Engine tolerates null output channels and odd block sizes")
{
    oldj::Engine engine;
    prepared (engine).setTestToneEnabled (true);

    std::array<float, 37> left {};
    std::array<float*, 2> channels { left.data(), nullptr };
    engine.process (channels.data(), 2, 37);
    engine.process (channels.data(), 1, 0);

    for (auto s : left)
        REQUIRE (std::isfinite (s));
}
