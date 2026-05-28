# Changelog

## v1.0.0 (2026-05-28)

### Features
- Real-time OCR screen capture + translation overlay for Overwatch chat
- Dual translation engine: Volcengine (primary) + Baidu (fallback)
- Transparent click-through overlay with fade animation
- Input helper for Chinese → target language translation
- System tray icon with pause/resume
- Global hotkeys (Ctrl+T manual translate, Ctrl+Shift+T input helper, Ctrl+M move overlay, Ctrl+Q exit)
- First-run setup wizard with region selector
- Settings window for translation/display configuration
- Smart message filtering: system messages, scoreboard, kill feed, ultimate prompts
- Multi-language system message detection (CN/EN/JP/KR)
- Translation result LRU cache with disk persistence
- Fuzzy message deduplication (handles OCR instability)
- DPI scaling awareness
- Multi-monitor support
- Window handle dynamic ROI (auto-detects Overwatch window)
- Frame rate adaptation (lowers scan rate when game not focused)
- Config hot reload (5s file watcher)
- Performance monitoring with threshold-based logging

### Technical
- OCR: Otsu adaptive binarization + median filter denoise + scale to fixed height
- HTTP: Session connection pooling for translation APIs
- Cache: blake2b hash + TTL + LRU + fuzzy SequenceMatcher dedup
- PyInstaller packaging support
- GitHub Actions CI (ruff lint + pytest)
- Unit tests for parser, cache, and config modules

### Anti-Cheat Compliance
- Pure screen capture via GDI BitBlt (same as OBS/Discord)
- No memory reading, DLL injection, or DirectX hooks
- Overlay uses standard PyQt6 transparent window
- Hotkeys use Windows standard WH_KEYBOARD_LL API

### Known Limitations
- Windows 10/11 only (requires WinRT OCR API)
- Requires Windows OCR language packs for target languages
- May need administrator privileges if game runs as admin
- Color mask filtering not yet implemented
- No TTS (text-to-speech) support
