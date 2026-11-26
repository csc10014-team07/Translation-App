import type { ToneId } from '../store/translationStore';

/**
 * Tên hiển thị tiếng Việt cho mỗi giọng văn.
 */
const TONE_LABELS: Record<ToneId, string> = {
  formal: 'Trang trọng',
  friendly: 'Thân mật',
  academic: 'Học thuật',
  business: 'Kinh doanh',
};

/**
 * Giọng văn ↔ context_preset backend chỉ áp dụng khi chọn ĐÚNG 1 tone.
 */
const PRESET_MAP: Partial<Record<ToneId, string>> = {
  formal: 'Formal',
  friendly: 'Friendly',
};

/**
 * Xây chuỗi context + contextPreset gửi cho backend từ tones & ghi chú.
 *
 * Ví dụ:
 *   buildContext([], '')
 *   // → { context: '' }
 *
 *   buildContext(['formal'], '')
 *   // → { context: 'Giọng văn: Trang trọng', contextPreset: 'Formal' }
 *
 *   buildContext(['formal', 'business'], 'gửi cho khách hàng')
 *   // → { context: 'Giọng văn: Trang trọng, Kinh doanh. Ghi chú: gửi cho khách hàng' }
 *
 *   buildContext([], 'giữ nguyên từ "deadline"')
 *   // → { context: 'Ghi chú: giữ nguyên từ "deadline"' }
 */
export function buildContext(
  tones: ToneId[],
  note: string,
): { context: string; contextPreset?: string } {
  const parts: string[] = [];

  if (tones.length > 0) {
    const labels = tones.map((t) => TONE_LABELS[t]);
    parts.push(`Giọng văn: ${labels.join(', ')}`);
  }

  const trimmedNote = note.trim();
  if (trimmedNote.length > 0) {
    parts.push(`Ghi chú: ${trimmedNote}`);
  }

  const context = parts.join('. ');

  // contextPreset chỉ khi chọn đúng 1 tone và tone đó có mapping
  const contextPreset =
    tones.length === 1 ? PRESET_MAP[tones[0]] : undefined;

  return contextPreset ? { context, contextPreset } : { context };
}
