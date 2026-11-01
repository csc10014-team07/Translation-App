# Known pitfalls in Translation-App

Each item says how confident the note is. "Verify" means check the current code first; the repo may already have fixed it.

## Run and layout
- Backend entry is `backend/app/main.py`. Run from `backend/`: `uvicorn app.main:app --host 0.0.0.0 --port 8000` (NOT `main:app`). Routes sit under `API_PREFIX` in `app/core/config.py` (default `/api`).
- Dev machine is WSL2 on Windows, GPU RTX 5060 Laptop 8 GB. A phone cannot reach a server inside WSL2 by default; test `http://<host-ip>:8000/health` in the phone browser before blaming the app.
- Model weights live in `backend/models/` and must stay out of git (`/backend/models/`, `*.gguf`). A bare `models/` line in `.gitignore` would also hide `backend/app/models/` (source code). Verify before touching `.gitignore`.

## Model manager and concurrency
- PhoASR and TranslateGemma both stay resident on the GPU. Pocket TTS runs on CPU, one model per language, loaded lazily. Do not reintroduce VRAM eviction or swapping.
- `llama_cpp.Llama` and the ASR model are not known to be thread safe. Routes call them with `run_in_executor`, so each adapter must hold a `threading.Lock` around inference (the translation lock must also cover any image or OCR call). Verify the locks still exist.
- Pocket TTS keeps per-language load and synthesis locks created up front. Do not create locks lazily with check-then-set.

## TranslateGemma (translation) — verify before changing
- The official chat template accepts only `user` and `assistant` roles (no `system`). A user turn carries structured content with `source_lang_code` and `target_lang_code`; assistant turns are plain strings.
- Unknown: whether llama-cpp-python applies the template embedded in the GGUF the same way as Hugging Face. The team's Colab notebook can print the exact prompt string (`--show-prompt`). Compare it with what `translation_adapter.py` builds. If they differ, do not guess: report it. Using `create_completion` with the exact Hugging Face prompt string is one option to propose.
- Use greedy decoding (`temperature=0`). Do not add a system message.
- Practical context is small (about 2K tokens reported by one guide, unverified). Truncate by tokens, not characters, if you add history.

## Pocket TTS (verified against pocket-tts 4.0.1 source)
- API: `TTSModel.load_model(language=...)`, `model.get_state_for_audio_prompt(<voice name or audio path>)`, `model.generate_audio(voice_state, text)`, `model.sample_rate`. `generate_audio` REQUIRES a voice state as first argument.
- Default voice per language: `pocket_tts.default_parameters.get_default_voice_for_language(lang)`.
- Supported languages: english, french, german, portuguese, italian, spanish, dutch. The app exposes six (no Dutch). Unsupported languages must return HTTP 400, never silently fall back to English.
- It ignores any reference transcript; `reference_text` is dead.
- Unknown: whether it can read `.m4a` reference audio. Test with a real phone recording; convert to WAV with ffmpeg if it fails.

## Audio from the phone
- `VoiceRecorder` records with expo-av `HIGH_QUALITY` (usually m4a/aac) but `api.ts` may label uploads as `audio/wav` / `recording.wav`. Verify, and derive extension and mime from the real file URI.
- Decoding m4a on the server needs ffmpeg. Check `shutil.which("ffmpeg")` at startup and warn clearly.
- Whisper handles about 30 s. Reject longer audio with a clear 422 instead of silently truncating.
- Raw PCM buffers must have an even byte length before `np.frombuffer(..., dtype=np.int16)`. Carry the leftover odd byte into the next chunk instead of dropping it. When trimming silence in a VAD, keep a short pre-roll (about 300 ms) so the first consonant is not cut.
- Never `asyncio.create_task` utterance processing without keeping a reference and a queue; results can arrive out of order. Prefer one worker per connection reading from an `asyncio.Queue`.

## Uploads and routes
- Cap every upload size (ASR 100 MB, images 20 MB, TTS reference audio about 20 MB). Read in chunks, not `await file.read()` on the whole body.
- File upload parameters stay as `UploadFile`; do not wrap them in a Pydantic request model.
- CORS does not affect the React Native app; do not spend effort on it.
- Remove hard-coded absolute model paths (`d:/...`, `/content/...`); resolve from settings.

## Mobile (Expo / React Native, TypeScript)
- `@react-navigation/stack` needs `react-native-gesture-handler` installed and `import 'react-native-gesture-handler';` as the first line of `App.tsx`. Verify.
- `API_BASE_URL` must not be `localhost` for a physical phone. Read it from `process.env.EXPO_PUBLIC_API_BASE_URL`.
- Arrays declared `as const` make `.includes(someString)` a type error. Use a helper such as `isTtsSupported(code: string)` built on `.some(...)`.
- TTS availability must use the language of the translation that exists (`translatedLanguage`), not the language currently selected in the picker, and clear stale synthesized audio when a new translation starts.
- Write synthesized audio to a unique cache filename and delete the previous file.
- Expo Go cannot run modules that need native code. A real-time microphone PCM stream for WebSocket "live" mode needs a dev build; `expo-av` does not give raw PCM frames.

## Privacy and claims (matters for the written report)
- Models run on the team's own server, not on the phone. Text still travels from phone to server.
- `edge_tts`, if present, sends text to an online service, needs internet, has no voice cloning, and is unofficial. Flag it; do not remove or keep it without the team's decision.
- Never write performance or quality claims in docs without a measured number from this repo.

## Dead or outdated things to remove only if confirmed unused
`_gpu_lock` leftovers, `unload_to_cpu` / `load_to_gpu` on adapters that no longer swap, `POCKET_TTS_LANGUAGE`, `reference_text` fields, docstrings that still mention Qwen3-TTS, Gemma 3, or VRAM swapping.