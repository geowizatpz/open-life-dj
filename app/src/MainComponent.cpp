#include "MainComponent.h"

#include "OldjAssets.h"

namespace oldj
{

namespace
{
    constexpr auto audioStateKey = "audioDeviceState";
}

MainComponent::MainComponent (juce::PropertiesFile& s)
    : settings (s)
{
    controllerImage = juce::ImageCache::getFromMemory (OldjAssets::controller_top_png,
                                                       OldjAssets::controller_top_pngSize);

    addAndMakeVisible (audioSettingsButton);
    audioSettingsButton.onClick = [this] { showAudioSettings(); };

    addAndMakeVisible (testToneButton);
    testToneButton.onClick = [this] { engine.setTestToneEnabled (testToneButton.getToggleState()); };

    addAndMakeVisible (statusLabel);
    statusLabel.setColour (juce::Label::textColourId, juce::Colours::lightgrey);
    statusLabel.setFont (juce::FontOptions (13.0f));

    // Output only for now (2 channels); headphone cueing on 4 outputs arrives in M2.
    const auto saved = settings.getXmlValue (audioStateKey);
    const auto error = deviceManager.initialise (0, 2, saved.get(), true);

    if (error.isNotEmpty())
        statusLabel.setText ("Audio error: " + error, juce::dontSendNotification);

    deviceManager.addAudioCallback (&output);
    deviceManager.addChangeListener (this);

    setSize (1600, 874 + toolbarHeight);
    startTimerHz (30);
}

MainComponent::~MainComponent()
{
    stopTimer();
    deviceManager.removeChangeListener (this);
    deviceManager.removeAudioCallback (&output);
    deviceManager.closeAudioDevice();
}

void MainComponent::paint (juce::Graphics& g)
{
    g.fillAll (juce::Colour (0xff0b0b0c));

    if (controllerImage.isValid())
        g.drawImage (controllerImage, controllerArea, juce::RectanglePlacement::centred);

    // toolbar + master peak meter
    auto bar = getLocalBounds().removeFromBottom (toolbarHeight);
    g.setColour (juce::Colour (0xff161618));
    g.fillRect (bar);

    auto meter = bar.removeFromRight (180).reduced (12, 15).toFloat();
    g.setColour (juce::Colour (0xff2a2a2d));
    g.fillRoundedRectangle (meter, 2.0f);

    const auto db = juce::Decibels::gainToDecibels (meterLevel, -60.0f);
    const auto fill = juce::jmap (db, -60.0f, 0.0f, 0.0f, 1.0f);
    g.setColour (db > -6.0f ? juce::Colour (0xffff5a3c) : juce::Colour (0xff3ce06e));
    g.fillRoundedRectangle (meter.withWidth (meter.getWidth() * fill), 2.0f);
}

void MainComponent::resized()
{
    auto area = getLocalBounds();
    auto bar = area.removeFromBottom (toolbarHeight).reduced (8, 6);

    controllerArea = area.toFloat();

    audioSettingsButton.setBounds (bar.removeFromLeft (140));
    bar.removeFromLeft (12);
    testToneButton.setBounds (bar.removeFromLeft (230));
    bar.removeFromLeft (12);
    bar.removeFromRight (180);
    statusLabel.setBounds (bar);
}

void MainComponent::timerCallback()
{
    const auto peak = engine.takeMasterPeak();
    meterLevel = std::max (peak, meterLevel * 0.85f);   // ~300 ms visual fall-off at 30 Hz

    statusLabel.setText (describeDevice(), juce::dontSendNotification);
    repaint (getLocalBounds().removeFromBottom (toolbarHeight));
}

juce::String MainComponent::describeDevice() const
{
    auto* device = deviceManager.getCurrentAudioDevice();

    if (device == nullptr)
        return "No audio device - open Audio Settings";

    const auto sr = device->getCurrentSampleRate();
    const auto buffer = device->getCurrentBufferSizeSamples();
    const auto latencyMs = sr > 0 ? 1000.0 * (buffer + device->getOutputLatencyInSamples()) / sr : 0.0;

    return device->getName()
         + "   |   " + juce::String (sr / 1000.0, 1) + " kHz"
         + "   |   " + juce::String (buffer) + " samples"
         + "   |   out latency " + juce::String (latencyMs, 1) + " ms"
         + "   |   CPU " + juce::String (deviceManager.getCpuUsage() * 100.0, 1) + " %";
}

void MainComponent::showAudioSettings()
{
    auto selector = std::make_unique<juce::AudioDeviceSelectorComponent> (
        deviceManager, 0, 0, 2, 2, false, false, true, false);
    selector->setSize (520, 420);

    juce::DialogWindow::LaunchOptions options;
    options.content.setOwned (selector.release());
    options.dialogTitle = "Audio Settings";
    options.dialogBackgroundColour = juce::Colour (0xff1c1c1f);
    options.useNativeTitleBar = true;
    options.resizable = false;
    options.launchAsync();
}

void MainComponent::changeListenerCallback (juce::ChangeBroadcaster*)
{
    saveAudioState();
}

void MainComponent::saveAudioState()
{
    if (const auto xml = deviceManager.createStateXml())
        settings.setValue (audioStateKey, xml.get());
    else
        settings.removeValue (audioStateKey);

    settings.saveIfNeeded();
}

} // namespace oldj
