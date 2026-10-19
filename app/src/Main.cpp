#include "MainComponent.h"

#include <juce_gui_basics/juce_gui_basics.h>

namespace oldj
{

class OpenLifeDJApplication final : public juce::JUCEApplication
{
public:
    const juce::String getApplicationName() override    { return JUCE_APPLICATION_NAME_STRING; }
    const juce::String getApplicationVersion() override { return JUCE_APPLICATION_VERSION_STRING; }
    bool moreThanOneInstanceAllowed() override          { return false; }

    void initialise (const juce::String&) override
    {
        juce::PropertiesFile::Options options;
        options.applicationName = "Open Life DJ";
        options.filenameSuffix = ".settings";
        options.folderName = "Open Life DJ";
        options.osxLibrarySubFolder = "Application Support";
        settings.setStorageParameters (options);

        mainWindow = std::make_unique<MainWindow> (getApplicationName(), *settings.getUserSettings());
    }

    void shutdown() override
    {
        mainWindow = nullptr;
        settings.closeFiles();
    }

    void systemRequestedQuit() override { quit(); }

private:
    class MainWindow final : public juce::DocumentWindow
    {
    public:
        MainWindow (const juce::String& name, juce::PropertiesFile& props)
            : DocumentWindow (name, juce::Colour (0xff0b0b0c), DocumentWindow::allButtons)
        {
            setUsingNativeTitleBar (true);
            setContentOwned (new MainComponent (props), true);
            setResizable (true, true);
            setResizeLimits (960, 560, 10000, 10000);
            centreWithSize (getWidth(), getHeight());
            setVisible (true);
        }

        void closeButtonPressed() override { juce::JUCEApplication::getInstance()->systemRequestedQuit(); }

    private:
        JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (MainWindow)
    };

    juce::ApplicationProperties settings;
    std::unique_ptr<MainWindow> mainWindow;
};

} // namespace oldj

START_JUCE_APPLICATION (oldj::OpenLifeDJApplication)
