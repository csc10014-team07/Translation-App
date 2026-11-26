/**
 * Tất cả chuỗi giao diện tiếng Việt, dùng xuyên suốt mobile app.
 * Sửa ở đây thay vì hardcode trong component.
 */
import { LANGUAGE_CATALOG } from './languages';

/** Ghép danh sách tên thành "A, B hoặc C" (rỗng → chuỗi rỗng). */
function joinWithHoac(names: readonly string[]): string {
  if (names.length === 0) return '';
  if (names.length === 1) return names[0];
  return `${names.slice(0, -1).join(', ')} hoặc ${names[names.length - 1]}`;
}

/**
 * Hạ chữ đầu của tên ngôn ngữ tiếng Việt khi đứng giữa câu
 * ("Tiếng Việt" → "tiếng Việt"). Tên riêng khác (English, 中文, …) giữ nguyên.
 */
function lowerMidSentence(label: string): string {
  const prefix = 'Tiếng ';
  return label.startsWith(prefix)
    ? `tiếng ${label.slice(prefix.length)}`
    : label;
}

/** Nhãn ngắn các ngôn ngữ có một khả năng đặc biệt (theo catalog). */
function labelsSupporting(
  capability: 'supportsVoiceInput' | 'supportsOcr',
): string[] {
  return LANGUAGE_CATALOG.filter((l) => l[capability]).map((l) => l.shortLabel);
}

export const strings = {
  home: {
    title: 'Dịch & Đọc',
    from: 'Dịch từ',
    to: 'Dịch sang',
    placeholder: 'Nhập văn bản cần dịch',
    addContext: 'Thêm ngữ cảnh',
    contextOptional: '(không bắt buộc)',
    contextAdded: 'Ngữ cảnh đã thêm',
    translate: 'Dịch',
    translating: 'Đang dịch…',
    readAloud: 'Đọc to',
    stopReading: 'Dừng',
    /** Hiện thay nút "Đọc to" khi ngôn ngữ đích không có giọng đọc. */
    ttsUnsupported: 'Chưa có giọng đọc cho ngôn ngữ này.',
    copied: 'Đã sao chép',
    // Nhãn tóm tắt khi chỉ có ghi chú ngữ cảnh (không chọn giọng văn nào).
    contextNoteFallback: 'ghi chú',
    voiceSample: 'Giọng mẫu',
    voiceSampleActive: 'Đang dùng giọng mẫu',
    voiceClonedNote: 'Đã dùng giọng mẫu',
    voiceCloneFallbackNote: 'Không dùng được giọng mẫu, đã dùng giọng mặc định',
  },

  voiceClone: {
    title: 'Giọng mẫu',
    description: 'Ghi 3–30 giây giọng của bạn để đọc bản dịch bằng giọng này.',
    record: 'Bắt đầu ghi',
    stop: 'Dừng ghi',
    play: 'Nghe lại',
    stopPlay: 'Dừng nghe',
    use: 'Dùng giọng này',
    clear: 'Xoá giọng mẫu',
    close: 'Đóng',
    ready: 'Giọng mẫu đã sẵn sàng',
    recordingHint: 'Đang ghi… hãy nói tự nhiên.',
    tooShort: 'Giọng mẫu quá ngắn. Hãy ghi ít nhất 3 giây.',
    permissionDenied: 'Cần quyền micro để ghi giọng mẫu.',
    recordError: 'Không ghi được giọng mẫu. Vui lòng thử lại.',
    accessibilityRecord: 'Ghi giọng mẫu',
    accessibilityStop: 'Dừng ghi giọng mẫu',
    accessibilityPlay: 'Nghe lại giọng mẫu',
    accessibilityUse: 'Dùng giọng mẫu này',
    accessibilityClear: 'Xoá giọng mẫu',
  },

  context: {
    title: 'Ngữ cảnh',
    optional: '(không bắt buộc)',
    notePlaceholder: 'Ví dụ: gửi cho khách hàng, giữ nguyên từ "deadline".',
    noteMax: 200,
    closeLabel: 'Đóng ngữ cảnh',
  },

  tones: {
    formal: 'Trang trọng',
    friendly: 'Thân mật',
    academic: 'Học thuật',
    business: 'Kinh doanh',
  },

  error: {
    translateTitle: 'Không dịch được',
    network: 'Không kết nối được tới máy chủ dịch. Kiểm tra mạng rồi thử lại.',
    generic: 'Đã có lỗi xảy ra. Vui lòng thử lại.',
    retry: 'Thử lại',
  },

  targetLanguage: {
    title: 'Dịch sang',
    available: 'Ngôn ngữ có sẵn',
    /** Dòng phụ ở hàng trùng với ngôn ngữ nguồn hiện tại. */
    isSourceHint: 'Đang là ngôn ngữ nguồn — sẽ hoán đổi',
  },

  sourceLanguage: {
    title: 'Dịch từ',
    description:
      'Ngôn ngữ này được chọn sẵn mỗi lần mở app. Bạn vẫn đổi được ở màn Dịch.',
    section: 'Ngôn ngữ có sẵn',
  },

  voice: {
    // ── idle ──
    /** Tiêu đề khi chưa bắt đầu nói. */
    idleTitle: 'Chạm để nói',
    /** Gợi ý một dòng dưới tiêu đề khi idle. */
    idleHint: 'Chạm vào micro rồi nói tiếng Việt. Chữ hiện ra khi bạn nói.',
    /** Placeholder giữa card khi idle (chưa có chữ nào). */
    idleCardHint: 'Chữ bạn nói sẽ hiện ở đây.',
    /** Chú thích dưới nút micro khi idle. */
    tapToStart: 'Chạm để bắt đầu nói',
    // ── listening ──
    listening: 'Đang nghe…',
    /** Gợi ý khi nghe trực tiếp; tên ngôn ngữ lấy từ nguồn hiện tại. */
    hint: (sourceLabel: string): string =>
      `Hãy nói ${lowerMidSentence(sourceLabel)}. Chữ hiện ra khi bạn nói.`,
    /** Gợi ý khi ghi âm rồi nhận dạng; tên ngôn ngữ lấy từ nguồn hiện tại. */
    hintNoLive: (sourceLabel: string): string =>
      `Hãy nói ${lowerMidSentence(sourceLabel)}. Chữ sẽ hiện sau khi bạn dừng.`,
    /** Placeholder giữa card khi đang nghe nhưng chưa có chữ nào. */
    listeningPlaceholder: 'Đang nghe bạn nói…',
    tapToStop: 'Chạm để dừng và dịch',
    // ── recognizing ──
    recognizing: 'Đang nhận dạng…',
    /** Gợi ý dưới tiêu đề khi đang nhận dạng. */
    recognizingHint: 'Đợi một chút, đang xử lý lời nói của bạn.',
    /** Chú thích dưới nút khi đang nhận dạng. */
    recognizingCaption: 'Đang nhận dạng…',
    // ── recognizing / finalize ──
    /** Gợi ý thay thế khi tự động dừng do vượt thời gian tối đa. */
    limitReached: 'Đã đạt thời gian tối đa, đang dịch…',
    /** Thông báo accessibility khi còn VOICE_WARNING_REMAINING_S giây. */
    warningAnnounce: 'Còn 5 giây',
    // ── lỗi ──
    noSpeech: 'Chưa nghe thấy giọng nói. Hãy thử lại.',
    permissionDenied: 'Cần quyền micro để nhận dạng giọng nói.',
    /** Lỗi khi file ghi âm vượt quá thời lượng backend cho phép (HTTP 422). */
    tooLong: 'Bạn nói quá dài, hãy nói ngắn hơn.',
    /** Lỗi mất kết nối WebSocket trong chế độ nghe trực tiếp. */
    networkError: 'Mất kết nối. Hãy thử lại.',
    /**
     * Thông báo khi nguồn hiện tại không nhập được bằng giọng nói. Danh sách
     * ngôn ngữ ASR lấy trực tiếp từ catalog (`supportsVoiceInput`).
     */
    unsupported: (sourceLabel: string): string => {
      const supported = labelsSupporting('supportsVoiceInput');
      if (supported.length <= 1) {
        const only = supported[0] ?? 'Tiếng Việt';
        return `Nhận dạng giọng nói hiện chỉ hỗ trợ ${lowerMidSentence(
          only,
        )}. Hãy chọn Dịch từ: ${only}.`;
      }
      return `Nhận dạng giọng nói chưa hỗ trợ ${lowerMidSentence(sourceLabel)}.`;
    },
  },

  camera: {
    pill: 'Đưa chữ vào khung',
    recognizing: 'Đang nhận dạng chữ…',
    recognizingHint: '(xong → dịch)',
    failTitle: 'Không nhận dạng được chữ nào',
    failHint: 'Thử ở nơi đủ sáng, giữ máy thẳng và gần chữ hơn.',
    retake: 'Chụp lại',
    permissionTitle: 'Cần quyền dùng camera',
    permissionBody:
      'Để quét chữ trong ảnh, hãy cho phép Dịch & Đọc dùng camera. Ảnh chỉ dùng để nhận dạng, không được lưu.',
    openSettings: 'Mở cài đặt quyền',
    typeInstead: 'Nhập văn bản thay thế',
    /**
     * Thông báo khi nguồn hiện tại không quét chữ được. Danh sách gợi ý lấy
     * trực tiếp từ catalog (`supportsOcr`).
     */
    ocrUnsupported: (sourceLabel: string): string =>
      `Quét chữ chưa hỗ trợ ${lowerMidSentence(
        sourceLabel,
      )}. Hãy chọn Dịch từ: ${joinWithHoac(labelsSupporting('supportsOcr'))}.`,
  },

  accessibility: {
    toggleTheme: 'Đổi giao diện sáng tối',
    clear: 'Xoá văn bản',
    mic: 'Nói để nhập văn bản',
    camera: 'Quét chữ bằng camera',
    copy: 'Sao chép bản dịch',
    back: 'Quay lại',
    close: 'Đóng',
    gallery: 'Chọn ảnh từ thư viện',
    torch: 'Bật tắt đèn pin',
    shutter: 'Chụp ảnh',
    changeTarget: 'bấm để đổi ngôn ngữ',
  },
} as const;
