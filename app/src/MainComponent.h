#pragma once

#include "AudioOutput.h"
#include "oldj/Engine.h"

#include <juce_audio_utils/juce_audio_utils.h>
#include <juce_gui_basics/juce_gui_basics.h>

namespace oldj
{

class MainComponent final : public juce::Component,
                            private juce::Timer,
                            private juce::ChangeListener
{
public:
    explicit MainComponent (juce::PropertiesFile& settings);
    ~MainComponent() override;

    void paint (juce::Graphics&) override;
    void resized() override;

private:
    void timerCallback() override;
    void changeListenerCallback (juce::ChangeBroadcaster*) override;   // device settings changed
    void showAudioSettings();
    void saveAudioState();
    juce::String describeDevice() const;

    juce::PropertiesFile& settings;

    Engine engine;
    AudioOutput output { engine };
    juce::AudioDeviceManager deviceManager;

    juce::Image controllerImage;
    juce::Rectangle<float> controllerArea;

    juce::TextButton audioSettingsButton { "Audio Settings..." };
    juce::ToggleButton testToneButton { "Test tone (-18 dBFS, 440 Hz)" };
    juce::Label statusLabel;
    float meterLevel = 0.0f;   // UI-side decayed peak

    static constexpr int toolbarHeight = 40;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (MainComponent)
};

} // namespace oldj
