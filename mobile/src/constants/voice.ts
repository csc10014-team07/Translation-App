/**
 * Hằng số thời lượng ghi âm / nghe giọng nói, suy ra từ backend.
 *
 * ⚠️  Các giá trị dưới đây là **ảnh chụp** của cấu hình backend mặc định.
 *     Backend cho phép đổi MAX_AUDIO_DURATION_S qua biến môi trường
 *     (xem backend/app/core/config.py dòng 58).
 *     Nếu server đổi giá trị này, hằng số ở đây sẽ lệch.
 *     Xem ghi chú "Đề xuất" ở cuối file để biết cách đọc giá trị lúc chạy.
 */

// ──────────────────────────────────────────────
// Hằng số backend gốc
// ──────────────────────────────────────────────

/**
 * Khoảng an toàn trừ hao (giây) để app dừng trước khi chạm đúng ngưỡng
 * của backend. Tránh race condition khi gói cuối cùng đến muộn.
 *
 * Nguồn: quy ước mobile, không lấy từ backend.
 */
export const VOICE_SAFETY_MARGIN_S = 1;

/**
 * Giới hạn cho chế độ **ghi file rồi gọi POST /api/asr** (giây).
 *
 * Khớp với `settings.MAX_AUDIO_DURATION_S` mặc định = 30.0 giây.
 * Vượt quá → backend trả HTTP 422 với message:
 *   "Audio exceeds maximum duration of {MAX_AUDIO_DURATION_S} seconds."
 *
 * Nguồn: backend/app/core/config.py dòng 58  (MAX_AUDIO_DURATION_S = 30.0)
 *         backend/app/api/routes/asr.py dòng 92-96 (kiểm tra duration > ...)
 */
export const VOICE_FILE_MAX_DURATION_S = 30;

/**
 * Giới hạn do APP đặt cho cả phiên nghe trực tiếp (giây).
 *
 * Backend chỉ cắt **mỗi câu** 30 s (khi đạt
 * `_max_utterance_bytes = MAX_AUDIO_DURATION_S × 16000 × 2` byte, stream.py
 * dòng 340-343), KHÔNG giới hạn tổng thời gian phiên WebSocket.
 *
 * Chọn 30 s để:
 *  - khớp chế độ ghi file (VOICE_FILE_MAX_DURATION_S = 30),
 *  - khớp ô nhập tối đa 500 ký tự (INPUT_MAX_LENGTH trong constants/limits.ts).
 *
 * Cả hai chế độ tự dừng ở 29 s (30 trừ hao VOICE_SAFETY_MARGIN_S = 1 s).
 *
 * Nguồn: backend/app/api/routes/stream.py dòng 340-343 (_max_utterance_bytes)
 *         backend/app/core/config.py dòng 58  (MAX_AUDIO_DURATION_S = 30.0)
 */
export const VOICE_LIVE_MAX_DURATION_S = 30;

/**
 * Còn bấy nhiêu giây thì hiện cảnh báo cho người dùng
 * (ví dụ: "Còn 5 giây, sắp tự dừng").
 *
 * Nguồn: quy ước UX, không lấy từ backend.
 */
export const VOICE_WARNING_REMAINING_S = 5;

/**
 * Thời gian chờ sự kiện cuối từ backend sau khi app dừng ghi (ms).
 *
 * Câu nói cuối có thể dài tới ~29 s và cần vài giây để ASR xử lý;
 * backend dọn hàng đợi tối đa 30 s (`VADSettings.stop_drain_timeout_s`,
 * stream.py dòng 55). Chọn 8000 ms: đủ nhận asr_final của câu cuối
 * mà không treo màn hình lâu. Hết thời gian chờ vẫn dùng chữ đã có.
 */
export const VOICE_FINAL_WAIT_MS = 8000;

// ──────────────────────────────────────────────
// Hàm tiện ích
// ──────────────────────────────────────────────

/**
 * Trả thời lượng ghi tối đa thực tế (đã trừ safety margin) cho từng chế độ.
 *
 * @param live  true = nghe trực tiếp (WebSocket), false = ghi file (/api/asr)
 * @returns     số giây tối đa app nên ghi trước khi tự dừng
 */
export function getVoiceMaxDurationS(live: boolean): number {
  const base = live ? VOICE_LIVE_MAX_DURATION_S : VOICE_FILE_MAX_DURATION_S;
  return base - VOICE_SAFETY_MARGIN_S;
}

// ──────────────────────────────────────────────
// Đề xuất: đọc giới hạn từ server lúc chạy
// ──────────────────────────────────────────────
//
// Endpoint GET /health hiện tại (backend/app/main.py dòng 112-127,
// schema backend/app/schemas/health.py) KHÔNG trả MAX_AUDIO_DURATION_S.
// Response chỉ gồm: status, device, vram, models_loaded.
//
// Nếu muốn app luôn đồng bộ với server thực tế (khi admin đổi .env):
//   1. Thêm trường `max_audio_duration_s: float` vào HealthResponse
//      (backend/app/schemas/health.py) và gán = settings.MAX_AUDIO_DURATION_S
//      trong hàm health() (backend/app/main.py).
//   2. Khi app mở, gọi GET /health, đọc trường này, cập nhật giá trị dùng
//      bởi getVoiceMaxDurationS() (lưu vào store hoặc ref).
//   3. Giữ hằng số ở file này làm FALLBACK khi mạng lỗi hoặc server chưa sẵn.
//
// → Chưa cần làm ngay vì giá trị mặc định hiếm khi đổi, nhưng ghi lại
//   để biết hướng xử lý khi cần.
