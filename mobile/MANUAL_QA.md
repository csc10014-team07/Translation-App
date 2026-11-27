# Manual QA — Giao diện V2 (kiểm tra tỉ lệ & checklist)

Tài liệu này để kiểm tra tay giao diện V2 trên nhiều kích thước màn hình.
Thiết kế chuẩn: **411×890 dp (Pixel 6)**. Mọi kích thước trong code đi qua
`s()` / `vs()` / `ms()` (xem `src/utils/scale.ts`), nội dung căn giữa bằng
`MAX_CONTENT_WIDTH` trên máy bảng.

---

## 0. Chạy app

```bash
cd mobile
npm run typecheck      # phải sạch (0 lỗi)
npm start              # Expo dev server
```

> Camera (quét chữ) và "nghe trực tiếp" cần **development build** (native module
> `expo-camera`, `react-native-live-audio-stream`). Trong **Expo Go**:
> - Camera: vẫn mở được màn, chụp/thư viện chạy; OCR gọi API như bình thường.
> - Giọng nói: tự chuyển sang chế độ "ghi rồi nhận dạng" (`useVoiceRecording`),
>   chữ hiện sau khi bấm dừng (không hiện realtime).

## 1. Tạo emulator/thiết bị để kiểm tra tỉ lệ

| Thiết bị | Độ phân giải (dp) | Ghi chú |
| --- | --- | --- |
| Pixel 4a | 360×800 | Màn hẹp/thấp — ca khó nhất |
| (màn nhỏ hơn) | 360×640 | Mô phỏng máy rất thấp |
| Pixel 6 | 411×890 | **Chuẩn thiết kế** |
| Pixel 7/8 | 428×926 | Máy cao |
| Pixel Tablet | 768×1024 | Kiểm tra căn giữa (tablet) |

**Android (Android Studio → Device Manager → Create Device → chọn profile →
"Show Advanced Settings" → đổi độ phân giải).**
Cách nhanh không cần AVD mới: **Settings → Display → Display size** trên emulator
để thay đổi dp hiệu dụng.

**Kiểm tra phóng to chữ (fontScale 1.3):**
Settings → Accessibility → Font size → kéo lên mức lớn nhất, hoặc chạy:

```bash
adb shell settings put system font_scale 1.3   # bật 1.3x
adb shell settings put system font_scale 1.0   # trả lại mặc định
```

## 2. Các điểm cần soi (mỗi kích thước)

- [ ] **Không tràn ngang**: không có chữ/nút nào bị cắt mép phải.
- [ ] **Home cuộn được** khi màn thấp (360×640): mở bàn phím → nút **Dịch**
      vẫn nằm trên bàn phím, **không che ô nhập**.
- [ ] **Nút "Dịch" thẳng hàng** với ô nhập (cùng lề trái/phải).
- [ ] **VoiceListening**: thẻ chữ lớn (`flex: 1`) co lại, **không đẩy** nhóm
      sóng âm/nút dừng ra ngoài màn.
- [ ] **Camera**: khung 4 góc **không chồng** lên thanh dưới / panel lỗi; khung
      chừa đúng safe-area trên (tai thỏ) và dưới (thanh điều hướng).
- [ ] **Tablet**: nội dung căn giữa, không bị giãn hết bề ngang.
- [ ] **fontScale 1.3**: nút và hàng ngôn ngữ **không bị cắt chữ**
      (đã dùng `minHeight` thay cho `height` cố định + `maxFontSizeMultiplier 1.2`).

## 3. Checklist chức năng (đối chiếu thiết kế)

**Màn chính**
- [ ] Tiêu đề **"Dịch & Đọc"** + nút mặt trời/mặt trăng (đổi sáng/tối).
- [ ] Ô **"Dịch từ Tiếng Việt"** nền xám, **không bấm được**.
- [ ] Ô **"Dịch sang English ⌄"** bấm được → mở màn "Dịch sang".
- [ ] Ô nhập placeholder **"Nhập văn bản cần dịch"**; nút **×** chỉ hiện khi có chữ.
- [ ] Hai nút tròn **mic** + **camera** ở góc dưới-trái ô nhập.
- [ ] Link **"+ Thêm ngữ cảnh (không bắt buộc)"**.
- [ ] Nút **"Dịch"** xám khi ô trống, xanh khi có chữ.
- [ ] Khi có kết quả: **ẩn nút Dịch**, hiện thẻ **"English"** + bản dịch +
      **"Đọc to"** + nút sao chép.
- [ ] Khi lỗi: thẻ đỏ **"Không dịch được"** + nút **"Thử lại"**.

**Thẻ ngữ cảnh**
- [ ] Tiêu đề **"Ngữ cảnh (không bắt buộc)"** + mũi tên **⌃** để đóng.
- [ ] Ô ghi chú + bộ đếm **x/200**.
- [ ] 4 chip giọng văn có checkbox, **chọn nhiều** được.

**Dịch sang / Ngôn ngữ mặc định**
- [ ] Hàng đang chọn: nền xanh nhạt + dấu **✓**.
- [ ] Danh sách đủ: English, 中文, 日本語, 한국어, Français, Deutsch, Español,
      Português… cuộn được, đúng chữ.
- [ ] Màn mặc định có đoạn mô tả; chọn xong **lưu bền** (mở lại app vẫn giữ).

**Đang nghe…**
- [ ] Nút **×**, dòng gợi ý, thẻ chữ lớn (đậm + xám), sóng âm,
      nút dừng có **vòng sáng**, chú thích **"Chạm để dừng và dịch"**.

**Camera**
- [ ] 4 trạng thái đúng màu khung: **trắng** (sẵn sàng) / **vàng** (đang nhận
      dạng) / **đỏ san hô** (lỗi) + đúng chữ.
- [ ] Màn **"Cần quyền dùng camera"** có **2 nút** (Mở cài đặt quyền /
      Nhập văn bản thay thế) + nút ×.

**Sáng/tối**
- [ ] Bấm nút mặt trời đổi sáng↔tối; **tắt/mở lại app vẫn nhớ** lựa chọn.
