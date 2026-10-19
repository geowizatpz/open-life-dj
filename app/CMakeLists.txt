juce_add_gui_app(OpenLifeDJ
    PRODUCT_NAME "Open Life DJ"
    COMPANY_NAME "Open Life DJ"
    BUNDLE_ID "org.openlifedj.app"
    NEEDS_WEB_BROWSER FALSE
    NEEDS_CURL FALSE)

juce_add_binary_data(oldj_assets
    HEADER_NAME "OldjAssets.h"
    NAMESPACE OldjAssets
    SOURCES
        ${PROJECT_SOURCE_DIR}/assets/controller_top.png)

target_sources(OpenLifeDJ
    PRIVATE
        src/Main.cpp
        src/MainComponent.cpp
        src/AudioOutput.cpp)

target_compile_definitions(OpenLifeDJ
    PRIVATE
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=0
        JUCE_APPLICATION_NAME_STRING="$<TARGET_PROPERTY:OpenLifeDJ,JUCE_PRODUCT_NAME>"
        JUCE_APPLICATION_VERSION_STRING="$<TARGET_PROPERTY:OpenLifeDJ,JUCE_VERSION>")

target_link_libraries(OpenLifeDJ
    PRIVATE
        oldj_engine
        oldj_assets
        juce::juce_audio_utils
        juce::juce_gui_extra
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags)
