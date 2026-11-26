# Ngôn ngữ Backend hỗ trợ (Translation-App)

> **Nguồn dữ liệu:** chỉ đọc mã nguồn trong `backend/` (không sửa file nào).
> **Đã thử chạy backend chưa?** **Chưa.** Trong môi trường này không có thư mục
> `models/` (weights TranslateGemma/PhoASR/Pocket TTS chưa tải), không có venv
> và `llama_cpp` chưa cài → **không gọi thử được `/api/translate`**.
> Toàn bộ kết luận dưới đây là **suy ra từ việc đọc code**.

Các file đã đọc:

| Nhóm | File |
| --- | --- |
| Dịch | `backend/app/models/translation_adapter.py`, `backend/app/api/routes/translate.py`, `backend/app/schemas/translate.py` |
| ASR | `backend/app/models/asr_adapter.py`, `backend/app/api/routes/asr.py`, `backend/app/schemas/asr.py` |
| Stream | `backend/app/api/routes/stream.py` |
| OCR | `backend/app/models/ocr_adapter.py`, `backend/app/api/routes/ocr.py`, `backend/app/schemas/ocr.py` |
| TTS | `backend/app/models/tts_adapter.py`, `backend/app/api/routes/tts.py`, `backend/app/schemas/tts.py` |
| Test (xác nhận) | `tests/test_translation_api.py`, `tests/test_translation_adapter.py`, `tests/test_tts_api.py`, `tests/test_ocr_adapter.py`, `tests/test_asr_api.py` |

---

## 1. Bảng ngôn ngữ backend nhận được

Cột **“Mã backend”** là **đúng chuỗi** dùng khi gọi API. Backend chấp nhận cả
**mã ISO** (`en`, `vi`, `ja`…) **lẫn tên tiếng Anh** (`English`, `Vietnamese`…)
vì `LANGUAGE_NAMES` map cả hai dạng (xem mục 2).

| Tên (tiếng Việt) | Tên bản ngữ | Mã backend | Dịch TỪ (nguồn) | Dịch SANG (đích) | ASR (nhập giọng nói) | OCR (quét chữ) | TTS (đọc to) | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tiếng Việt | Tiếng Việt | `vi` / `Vietnamese` / `vie` | Có | Có | **Có** (duy nhất) | **Có** | Edge-TTS (`vi-VN-HoaiMyNeural` / `vi-VN-NamMinhNeural`) | Ngôn ngữ gốc của toàn hệ thống: PhoASR chỉ nhận tiếng Việt; OCR nhận diện tiếng Việt bằng dấu; TTS **luôn** dùng Edge-TTS (không voice-clone). |
| Tiếng Anh | English | `en` / `English` | Có | Có | Không | **Có** | Edge-TTS (`en-US-JennyNeural` / `en-US-GuyNeural`); Pocket TTS nếu có audio mẫu | OCR: chữ Latin không dấu → mặc định trả `en`. |
| Tiếng Nhật | 日本語 | `ja` / `Japanese` | Có | Có | Không | **Có** (nhận diện kana) | Edge-TTS (`ja-JP-NanamiNeural` / `ja-JP-KeitaNeural`) | OCR nhận diện nhờ Hiragana/Katakana (`U+3040–30FF`). |
| Tiếng Trung (Giản thể) | 中文 | `zh` / `Chinese` | Có | Có | Không | **Có** (nhận diện CJK) | Edge-TTS (`zh-CN-XiaoxiaoNeural` / `zh-CN-YunxiNeural`) | Mã là `zh`, **không phải** `zh-CN`. OCR nhận nhờ dải CJK `U+4E00–9FFF`. |
| Tiếng Hàn | 한국어 | `ko` / `Korean` | Có | Có | Không | **Không chắc** | Edge-TTS (`ko-KR-SunHiNeural` / `ko-KR-InJoonNeural`) | `detect_language()` **không** có nhánh Hangul → chữ Hàn bị trả về mặc định `en`. |
| Tiếng Pháp | Français | `fr` / `French` | Có | Có | Không | **Không chắc** | Edge-TTS (`fr-FR-DeniseNeural` / `fr-FR-HenriNeural`); Pocket TTS nếu có audio mẫu | Chữ Latin: có dấu thuộc bộ dấu tiếng Việt (é, è, ô, à…) rất dễ bị **nhận nhầm là `vi`**; không dấu → trả `en`. |
| Tiếng Đức | Deutsch | `de` / `German` | Có | Có | Không | **Không chắc** | Edge-TTS (`de-DE-KatjaNeural` / `de-DE-KillianNeural`); Pocket TTS nếu có audio mẫu | Như trên: bị nhận nhầm `vi` (nếu có ä/ö/ü/ß không nằm trong tập dấu Việt → `en`). |
| Tiếng Tây Ban Nha | Español | `es` / `Spanish` | Có | Có | Không | **Không chắc** | Edge-TTS (`es-ES-ElviraNeural` / `es-ES-AlvaroNeural`); Pocket TTS nếu có audio mẫu | Có ñ/á/é/í → dễ nhận nhầm `vi` (é/í/ó nằm trong tập dấu Việt). |
| Tiếng Bồ Đào Nha | Português | `pt` / `Portuguese` | Có | Có | Không | **Không chắc** | Edge-TTS (`pt-BR-FranciscaNeural` / `pt-BR-AntonioNeural`); Pocket TTS nếu có audio mẫu | Có ã/õ/ç/á → dễ nhận nhầm `vi`. |
| Tiếng Nga | Русский | `ru` / `Russian` | Có | Có | Không | **Không chắc** | Edge-TTS (`ru-RU-SvetlanaNeural` / `ru-RU-DmitryNeural`) | Chữ Cyrillic **không** có nhánh nhận diện → trả mặc định `en`. |
| Tiếng Ý | Italiano | `it` / `Italian` | Có | Có | Không | **Không chắc** | Edge-TTS (`it-IT-ElsaNeural` / `it-IT-DiegoNeural`); Pocket TTS nếu có audio mẫu | Chữ Latin có dấu (à/è/ì/ò/ù) → dễ nhận nhầm `vi`. |
| *(Tiếng Hà Lan)* | Nederlands | `nl` / `dutch` | Không | Không | Không | Không | **Chỉ Pocket TTS** (không có voice Edge) | **Không** có trong `LANGUAGE_NAMES` → dịch không được; TTS qua luồng mặc định (không audio mẫu) sẽ **lỗi 400**. Coi như **không hỗ trợ**. |

### Con số tổng hợp

| Hạng mục | Số lượng | Danh sách |
| --- | --- | --- |
| Ngôn ngữ **dịch** (nguồn & đích, `LANGUAGE_NAMES`) | **11** | vi, en, ja, zh, ko, fr, de, es, pt, ru, it |
| **ASR** (nhập giọng nói) | **1** | vi |
| **OCR** nhận diện chắc chắn | **4** | vi, en, ja, zh |
| **TTS** qua Edge-TTS | **11** | vi, en, ja, zh, ko, fr, de, es, pt, it, ru |
| **TTS** qua Pocket TTS (voice-clone) | **7** | en, fr, de, es, pt, it, nl |
| Ngôn ngữ **đích** đọc to được | **11** | như Edge-TTS (mọi ngôn ngữ dịch đều có voice đọc) |

> Lưu ý: `LANGUAGE_NAMES` có **11** ngôn ngữ, nhưng `nl` (Hà Lan) lại chỉ nằm ở
> Pocket TTS → ngôn ngữ này **nửa vời**: TTS có (khi ép `preferred_engine`),
> nhưng dịch thì không. Ngoài ra **không** có `source_language = "auto"**.

---

## 2. Cách backend xử lý mã lạ

### 2.1. Dịch (`/api/translate`) — **KHÔNG kiểm tra danh sách cho phép**

- `schemas/translate.py` chỉ validate `text` và `target_language` **không rỗng**
  (`validate_non_whitespace`). `source_language` mặc định `"vi"`, **không** bị validate.
- `routes/translate.py` cũng chỉ chặn chuỗi rỗng → **không** có allow-list.
  Test `test_translation_api.py` khẳng định điều này: gửi `source_language="en"`
  (không phải tiếng Việt) vẫn được **chấp nhận và chuyển tiếp**.
- `translation_adapter.py → build_prompt()`:

  ```python
  src_name = LANGUAGE_NAMES.get(source_lang.lower(), source_lang)
  tgt_name = LANGUAGE_NAMES.get(target_lang.lower(), target_lang)
  ```

  → Mã **có** trong `LANGUAGE_NAMES` (11 ngôn ngữ + tên tiếng Anh) được đổi thành
  tên tiếng Anh đẹp (`"ja" `→ `"Japanese"`). Mã **lạ** (ví dụ `"xyz"`, `"Klingon"`)
  **không lỗi** — chuỗi gốc được **nhúng nguyên văn** vào prompt:
  `"You are a professional <xyz> to <English> translator…"`.
  → Kết quả phụ thuộc hoàn toàn vào LLM TranslateGemma.
- **Không có `auto`**: nếu gửi `source_language="auto"`, `LANGUAGE_NAMES.get("auto")`
  trả `None` → dùng thẳng chuỗi `"auto"` trong prompt (LLM có thể tự đoán, nhưng
  backend **không** có cơ chế auto-detect riêng).
- **Giới hạn cặp ngôn ngữ của TranslateGemma:** **không tìm thấy** bất kỳ
  ràng buộc/allow-list cặp ngôn ngữ nào trong code. Về mặt kiến trúc, mọi cặp
  nguồn↔đích đều “được phép” miễn LLM hiểu; **chất lượng** phụ thuộc mô hình,
  không phải backend chặn.

### 2.2. ASR (`/api/asr`) — **chỉ tiếng Việt, không đổi được**

- `asr_adapter.py → transcribe_array()`:

  ```python
  generate_kwargs = {"task": "transcribe", "language": "vi"}
  ```

  → `language` **hardcode `"vi"`**, không lấy từ tham số nào; và luôn trả
  `"language": "vi"` trong kết quả.
- `routes/asr.py` **không** nhận tham số `language`; chỉ nhận file upload
  (WAV/MP3/M4A/FLAC/OGG/WebM), giới hạn 100 MB và thời lượng `MAX_AUDIO_DURATION_S`.
- `schemas/asr.py` ghi rõ `language_detected` = mã của bản ghi, và test
  `test_asr_api.py` khẳng định `language_detected == "vi"`.
- **Kết luận:** ASR = **1 ngôn ngữ (tiếng Việt)**. Không có đường cấu hình để
  nhận tiếng Anh/Nhật/Trung/Hàn… bằng `language` param.

### 2.3. WebSocket stream (`/ws/stream`) — `source`/`target` **không** dùng cho ASR

- Thông điệp điều khiển `{"action": "start", "source_lang": …, "target_lang": …}`
  **có** được lưu vào `config` (`stream.py` dòng 411–434) và sau đó được dùng cho
  **dịch + TTS** (`_stream_translation_and_tts`: `target_lang`, `source_lang` →
  `translate_stream(...)`, rồi TTS theo `target_lang`).
- **Nhưng ASR trong stream lại gọi thẳng `asr.transcribe_array(pcm, duration)`**
  (dòng 163–165) — hàm này **hardcode `language="vi"`** và **không nhận**
  `source_lang`. Vậy trường `source_lang` trong thông điệp `start` **không ảnh
  hưởng** tới nhận dạng giọng nói; nó chỉ vào prompt dịch.
  → Nói cách khác: **stream luôn transcribe tiếng Việt**, bất kể client khai báo
  `source_lang` là gì. Chỉ `target_lang` là có hiệu lực thật (dịch + đọc to).

### 2.4. OCR (`/api/ocr`) — nhận diện thô + đoán bằng luật dấu

- `ocr_adapter.py` nạp **RapidOCR CPU mặc định** (`RapidOCR()`, ONNX Runtime,
  0 MB VRAM) → **model mặc định bộ `ch` (Trung + Anh + số)**, hợp với dấu Latinh
  và CJK, **không** đảm bảo cho Hangul/Cyrillic.
- `detect_language(text)` chỉ có **4 nhánh**, theo thứ tự:
  1. Có ký tự dấu tiếng Việt (à á ả … ơ ư đ) → `vi`
  2. Có Hiragana/Katakana → `ja`
  3. Có CJK Unified Ideograph → `zh`
  4. Còn lại → `en`
  - Rỗng/khoảng trắng → `en`.
  - Vậy `detect_language` **chỉ có thể trả về** `vi`, `ja`, `zh`, `en`.
- Hệ quả (đọc mã + test `test_ocr_adapter.py`):
  - **Chắc chắn:** tiếng Việt, Anh, Nhật, Trung.
  - **Không chắc:** Pháp/Đức/Tây Ban Nha/Bồ Đào Nha (Latin) — chữ **có dấu** rơi
    vào tập dấu Việt → **nhận nhầm `vi`**; **không dấu** → `en`.
    **Hàn** (Hangul), **Nga** (Cyrillic) → **bị trả `en`**.
- `routes/ocr.py`:
  - `target_language` **không** bị validate danh sách; nếu client **không** gửi
    thì tự chọn: `detected == "vi" → "en"`, ngược lại `→ "vi"`.
  - `source_language`: nếu client gửi thì **dùng thẳng**; nếu không thì lấy
    `detected_lang`.
  - Nếu `extracted_text` rỗng → `translated_text = ""` (bỏ qua bước dịch).
  - Lỗi dịch Stage 2 → **HTTP 502**; lỗi OCR engine → 503.

### 2.5. TTS (`/api/tts`) — **có** kiểm tra ngôn ngữ, chọn engine theo luật cứng

`tts_adapter.py → synthesize()` chạy theo thứ tự:

1. **`preferred_engine` tường minh?**
   - `pocket_tts`: chỉ hợp lệ nếu `POCKET_TTS_LANG_MAP` có mã
     (en, fr, de, es, pt, it, nl) → ngược lại **`ValueError`**.
   - `edge_tts`: chỉ hợp lệ nếu mã nằm trong `EDGE_VOICES_*` → ngược lại **`ValueError`**.
2. **Tiếng Việt (`vi`/`vietnamese`/`vie`) → luôn Edge-TTS.**
3. **Ngôn ngữ Pocket TTS (`en/fr/de/es/pt/it`) + có `reference_audio` → Pocket TTS (voice-clone).**
4. **Mặc định → Edge-TTS.**
   - Nếu `EDGE_TTS_ENABLED=false` → **`RuntimeError`**.
   - Nếu mã **không** có trong `EDGE_VOICES_*` → **`ValueError`**.

`routes/tts.py` chuyển `ValueError`/`RuntimeError` → **HTTP 400** (xem test:
`test_tts_api.py` kỳ vọng 400 cho ngôn ngữ lạ). Ngôn ngữ trống → **422**.

- **`EDGE_VOICES_FEMALE`/`EDGE_VOICES_MALE`** (11 ngôn ngữ, mỗi mã có cả tên
  tiếng Anh): `vi, en, ja, zh, ko, fr, de, es, pt, it, ru`.
- **`POCKET_TTS_LANG_MAP`** (7): `en, fr, de, es, pt, it, nl`
  (Pocket TTS trước mục đích là voice-cloning tiếng Anh + châu Âu).
- Với mỗi **ngôn ngữ đích** của app (en, zh, ja, ko, fr, de, es, pt, ru, it):
  **tất cả đều đọc to được**, **tối thiểu bằng Edge-TTS**; các ngôn ngữ
  `en/fr/de/es/pt/it` **còn** đọc được bằng Pocket TTS (clone giọng) nếu client
  gửi kèm audio mẫu.
- **`nl` (Hà Lan)** chỉ có Pocket TTS, không có Edge → luồng thường (không
  `preferred_engine`, không audio mẫu) sẽ **lỗi 400**.
- Có test `test_edge_voices_cover_mobile_languages()` chốt rằng `pt, it, ru`
  **bắt buộc** phải có cả voice nam & nữ (khớp danh sách ngôn ngữ app cũ).

---

## 3. Đề xuất danh sách đưa vào app mobile

### 3.1. Ngôn ngữ NGUỒN (“Dịch từ”)

Backend **không** giới hạn nguồn dịch, nhưng **ASR chỉ tiếng Việt** và **OCR
nhận diện chắc chỉ vi/en/ja/zh**. Vì app hiện cố định nguồn = `vi`, đề xuất:

1. **Tiếng Việt (`vi`)** — **mặc định & bắt buộc**; đây là ngôn ngữ duy nhất
   dùng được cho mic (ASR) và là ca OCR chắc chắn nhất.
2. *(Tùy chọn, chỉ khi muốn dịch văn bản từ ngôn ngữ khác)* — thứ tự cũ:
   **English (`en`), 中文 Chinese (`zh`), 日本語 Japanese (`ja`), 한국어 Korean (`ko`),
   Français French (`fr`), Deutsch German (`de`), Español Spanish (`es`),
   Português Portuguese (`pt`), Русский Russian (`ru`), Italiano Italian (`it`)**.

> Khuyến nghị: giữ nguồn = **chỉ Tiếng Việt** cho V2 (đúng thiết kế “Dịch từ
> Tiếng Việt”, tránh hứa hẹn ASR/OCR cho ngôn ngữ không hỗ trợ).

### 3.2. Ngôn ngữ ĐÍCH (“Dịch sang”)

Theo thứ tự app cũ + bổ sung Tiếng Việt (backend **có** dịch sang `vi` được, và
Edge-TTS **có** voice tiếng Việt):

| # | Mã | Hiển thị | Đọc to |
| --- | --- | --- | --- |
| 1 | `en` | English | Edge (+ Pocket nếu có audio mẫu) |
| 2 | `zh` | 中文 (Chinese – Simplified) | Edge |
| 3 | `ja` | 日本語 (Japanese) | Edge |
| 4 | `ko` | 한국어 (Korean) | Edge |
| 5 | `fr` | Français (French) | Edge (+ Pocket) |
| 6 | `de` | Deutsch (German) | Edge (+ Pocket) |
| 7 | `es` | Español (Spanish) | Edge (+ Pocket) |
| 8 | `pt` | Português (Portuguese) | Edge (+ Pocket) |
| 9 | `ru` | Русский (Russian) | Edge |
| 10 | `it` | Italiano (Italian) | Edge (+ Pocket) |
| 11 | **`vi`** | **Tiếng Việt (Vietnamese)** | Edge |

- **So với app hiện tại** (`mobile/src/constants/languages.ts`): app đang có
  `en, zh, ja, ko, fr, de, es, pt, ru, it` — **thiếu `vi`**. Nếu muốn dịch ngược
  về tiếng Việt (ví dụ OCR chữ nước ngoài → tiếng Việt), **thêm `vi` vào
  `TARGET_LANGUAGES`** (thứ tự đề xuất: để cuối, hoặc ngay sau `en` nếu ưu tiên
  nghiệp vụ “dịch về tiếng Việt” mặc định của OCR).
- **Không** đưa `nl` (Hà Lan) vào app: dịch không hỗ trợ, TTS dễ lỗi 400.

---

## 4. Điểm đáng lo (tóm tắt)

1. **ASR chỉ tiếng Việt**, `language` hardcode — đừng hứa “nghe & dịch” cho
   ngôn ngữ nguồn khác.
2. **`source_lang` trong stream không tác động ASR** — chỉ `target_lang` có hiệu lực.
3. **OCR `detect_language` chỉ trả `vi/en/ja/zh`**; **Pháp/Đức/Tây Ban Nha/Bồ Đào
   Nha rất dễ bị nhận nhầm `vi`** (trùng bộ dấu), **Hàn/Nga bị trả `en`**.
4. **Dịch không validate mã** → mã lạ đi thẳng vào prompt LLM (không lỗi, nhưng
   kết quả có thể vô nghĩa). **Không hỗ trợ `auto`**.
5. **TTS có validate**: mã ngoài `EDGE_VOICES_*` (và không thuộc Pocket) → **400**;
   nếu `EDGE_TTS_ENABLED=false` (mặc định `True` trong `core/config.py`) thì đọc to
   bằng Edge sẽ **lỗi**.
6. **`nl` nửa vời** (chỉ Pocket) — nên loại khỏi UI.
7. App **thiếu `vi` trong danh sách đích** dù backend hỗ trợ → cần bổ sung nếu
   muốn dịch về tiếng Việt.
