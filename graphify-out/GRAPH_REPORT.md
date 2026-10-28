# Graph Report - Translation-App  (2026-10-28)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 277 nodes · 450 edges · 17 communities (9 shown, 8 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d36f1d8d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11

## God Nodes (most connected - your core abstractions)
1. `synthesise_speech()` - 12 edges
2. `react` - 12 edges
3. `expo` - 11 edges
4. `transcribe_audio()` - 10 edges
5. `TranslationScreen()` - 10 edges
6. `@expo/vector-icons` - 10 edges
7. `react-native` - 10 edges
8. `ocr_image()` - 9 edges
9. `dep_model_manager()` - 8 edges
10. `translate_text()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `transcribe_audio()` --uses--> `ASRResponse`  [INFERRED]
  backend/app/api/routes/asr.py → backend/app/schemas/asr.py
- `synthesise_speech()` --uses--> `TTSResponse`  [INFERRED]
  backend/app/api/routes/tts.py → backend/app/schemas/tts.py
- `translate_text()` --uses--> `TranslateRequest`  [INFERRED]
  backend/app/api/routes/translate.py → backend/app/schemas/translate.py
- `translate_text()` --uses--> `TranslateResponse`  [INFERRED]
  backend/app/api/routes/translate.py → backend/app/schemas/translate.py
- `health()` --calls--> `get_vram_info()`  [EXTRACTED]
  backend/app/main.py → backend/app/core/vram_monitor.py

## Import Cycles
- None detected.

## Communities (17 total, 8 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (9): dep_model_manager(), transcribe_audio(), _audio_to_wav_base64(), _is_vietnamese(), synthesise_speech(), get_vram_info(), create_app(), health() (+1 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (46): App(), dependencies, axios@^1.7.0, expo@~51.0.0, expo-av@~14.0.7, expo-file-system@~17.0.1, expo-image-picker@~15.0.7, expo-status-bar@~1.12.1 (+38 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (33): ContextInput(), Props, styles, ImagePickerButton(), Props, styles, InputMode, InputModeSelector() (+25 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (6): translate_text(), ASRResponse, TranslateRequest, TranslateResponse, TTSRequest, TTSResponse

### Community 4 - "Community 4"
Cohesion: 0.14
Nodes (18): API_BASE_URL, apiClient, appendFileToForm(), ASRResponse, HealthResponse, ocrImage(), OCRResponse, saveBase64Audio() (+10 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (16): backgroundColor, adaptiveIcon, expo, android, icon, ios, name, orientation (+8 more)

### Community 6 - "Community 6"
Cohesion: 0.20
Nodes (4): download_gemma_gguf(), download_phoasr(), download_qwen_tts(), main()

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (3): get_settings(), Settings, Config

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (6): compilerOptions, baseUrl, paths, strict, extends, expo/tsconfig.base

## Knowledge Gaps
- **1 isolated node(s):** `expo/tsconfig.base`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 134 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VRAMTracker` connect `Community 7` to `Community 0`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **What connects `expo/tsconfig.base` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07259528130671507 - nodes in this community are weakly interconnected._
- **Why does `react` connect `Community 2` to `Community 1`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05697278911564626 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09407665505226481 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.09420289855072464 - nodes in this community are weakly interconnected._