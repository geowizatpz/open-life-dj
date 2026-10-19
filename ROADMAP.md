# Open Life DJ — Roadmap

**Principle:** ship a small, rock-solid core that does what a real 4-channel all-in-one player does. Everything beyond the essentials comes later as **plugins**.

**Stack:** C++20 · JUCE 8 (AGPLv3) · CMake + Ninja. Developed on macOS first, with CI building macOS, Windows and Linux from day one.

The core is built so its own features use the same extension points that plugins will use later. Built-in effects, for example, are written against the effect API, so the plugin API is proven long before it opens to others.

---

## Milestone 0 — Foundation
Goal: an empty app that opens a window and makes sound, on all three operating systems.

- [ ] Repo: git, AGPLv3 `LICENSE`, README (with trademark and art-licence notes), `.clang-format`
- [ ] CMake skeleton with JUCE as a submodule; one build for Apple Silicon and Intel Macs
- [ ] Engine and UI split into separate targets (`engine/` has no GUI dependency)
- [ ] Audio output: device selection, buffer size, sample rate (JUCE `AudioDeviceManager`)
- [ ] Real-time safety rules documented: no allocation, locks or file I/O on the audio thread; lock-free queues between UI and engine
- [ ] GitHub Actions: build and test on macOS, Windows and Ubuntu
- [ ] Window shows the static Blender render of the controller

## Milestone 1 — One deck plays
Goal: load a track and control it like a real player.

- [ ] Decode WAV, AIFF, FLAC, MP3 and Ogg
- [ ] Play / pause, CUE (Pioneer-style: set, return, hold-to-preview), seek
- [ ] Tempo fader with ±6 / ±10 / ±16 % / WIDE ranges (varispeed: pitch follows speed)
- [ ] Track overview waveform and a scrolling zoomed waveform on the screen strip
- [ ] Elapsed and remaining time, track title and artist

## Milestone 2 — Mixer
Goal: two decks blended through a real mixer.

- [ ] 2 decks routed into a 4-channel mixer (decks 3 and 4 come in M6)
- [ ] Per channel: trim, 3-band EQ (HI/MID/LOW, kill-capable), COLOR filter (LPF/HPF), channel fader, CUE
- [ ] Crossfader with curve setting
- [ ] Master and booth levels; peak and level meters (channels and master)
- [ ] Headphone cue: split output on a 4-out audio interface, with phones mix and level
- [ ] Limiter on the master output

## Milestone 3 — Library
Goal: find a track fast and load it.

- [ ] Add music folders; scan and watch for changes
- [ ] SQLite database; tag reading (TagLib); artwork
- [ ] Browse, search and sort (title, artist, BPM, key, genre, date added); playlists (crates)
- [ ] Background analysis: BPM, beatgrid, key, waveform cache, loudness (gain normalisation)
- [ ] Load to deck from the browser (the encoder plus a LOAD action)

## Milestone 4 — Beat tools
Goal: everything needed to beatmatch and perform.

- [ ] Beatgrid display and manual grid adjustment
- [ ] SYNC (tempo plus phase), leader/follower deck
- [ ] Key lock / Master Tempo (time-stretching with Signalsmith Stretch)
- [ ] 8 hot cues per track with colours, stored in the library
- [ ] Loops: 4-beat auto loop, loop in/out, reloop, halve/double; beat jump; slip mode
- [ ] Quantize

## Milestone 5 — The hyperreal UI comes alive
Goal: the Blender controller is the interface, and every control works.

- [ ] Blender exporter: a sprite sheet per control (knob filmstrips, fader caps, button and LED states) plus `layout.json`
- [ ] Interactive controls: knob drag/scroll, fader drag, buttons, pads; double-click resets to default
- [ ] Jog wheel: nudge (edge), scratch (top, vinyl mode), search (with SHIFT)
- [ ] LEDs, pads and meters reflect live engine state
- [ ] Jog displays: playhead position ring, cue marker, BPM
- [ ] Window scaling (Retina, HiDPI) and full-screen performance mode

## Milestone 6 — Ready for real gigs
- [ ] 4 decks
- [ ] Built-in Beat FX: echo, delay, reverb, filter, flanger, roll (each built on the internal effect API)
- [ ] MIDI controller support: MIDI learn plus mapping files
- [ ] Record the mix to WAV
- [ ] Settings: audio routing, latency, waveform colours, default tempo range
- [ ] Crash-safe autosave of library and cue data

## v1.0 — Release
- [ ] macOS: signed and notarized DMG · Windows: installer · Linux: AppImage or Flatpak
- [ ] Performance budget met: about 5–10 ms output latency, no dropouts during 2-hour soak tests
- [ ] User manual and contributor guide

---

## After 1.0 — Plugin platform
Open these extension points with a versioned SDK, in this order:

| # | Extension point | Examples | How |
|---|---|---|---|
| 1 | **Audio effects** | Any VST3 / AU / LV2 effect | JUCE can already host these; add an FX-slot UI |
| 2 | **Controller mappings** | Community scripts for any MIDI/HID controller | Scripted (Lua or JS), sandboxed |
| 3 | **Library sources** | Streaming services, DJ-software importers (rekordbox XML, Serato crates) | C++ plugin API |
| 4 | **Analyzers** | Alternative BPM/key detection, cue-point AI | C++ plugin API, runs off the audio thread |
| 5 | **Skins** | Other hardware looks, light themes | Sprite pack + `layout.json` (the same format as M5) |
| 6 | **Deck sources** | Sampler, stems separation, DVS (timecode vinyl) | C++ plugin API |

**Licensing note for plugins:** because the app is AGPLv3, in-process plugins may be considered part of the program. Decide before the SDK ships whether to add a plugin exception, as GPL projects often do, so closed-source plugins are allowed. VST3/AU effects are separate programs and are not affected.

## Not in the core (plugins or later)
Streaming services · stems separation · DVS / timecode vinyl · video · lighting and DMX control · cloud sync · Ableton Link (could become core if requested)
