/**
 * Tất cả chuỗi giao diện tiếng Việt, dùng xuyên suốt mobile app.
 * Sửa ở đây thay vì hardcode trong component.
 */

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
    copied: 'Đã sao chép',
    // Nhãn tóm tắt khi chỉ có ghi chú ngữ cảnh (không chọn giọng văn nào).
    contextNoteFallback: 'ghi chú',
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
    setDefault: 'Đổi ngôn ngữ mặc định',
  },

  defaultLanguage: {
    title: 'Ngôn ngữ mặc định',
    description:
      'Ngôn ngữ này được chọn sẵn mỗi lần mở app. Bạn vẫn đổi được ở màn Dịch.',
    section: 'Dịch sang',
  },

  voice: {
    listening: 'Đang nghe…',
    hint: 'Hãy nói tiếng Việt. Chữ hiện ra khi bạn nói.',
    hintNoLive: 'Hãy nói tiếng Việt. Chữ sẽ hiện sau khi bạn dừng.',
    recognizing: 'Đang nhận dạng…',
    tapToStop: 'Chạm để dừng và dịch',
    noSpeech: 'Chưa nghe thấy giọng nói. Hãy thử lại.',
    permissionDenied: 'Cần quyền micro để nhận dạng giọng nói.',
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
