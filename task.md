# TASK.md — Prompt gửi DeepSeek (opencode) để làm lại giao diện Translation-App (bản thiết kế V2)

## Cách dùng file này

- Mỗi **TASK** gồm: **PROMPT** (khung code, copy nguyên khối gửi DeepSeek) + **GIẢI THÍCH** (cho bạn đọc: làm gì, tạo/sửa file nào, kiểm tra thế nào).
- DeepSeek trong opencode **không đọc được UI.pdf**, nên mọi prompt đã **mô tả bằng chữ rất chi tiết** (bố cục, màu, kích thước, chữ hiển thị, trạng thái). Bạn không cần đính kèm PDF. Chỉ Task 0 cần đính kèm `giai_thich.md`.
- **Gửi theo đúng thứ tự**, mỗi lần một task. Sau mỗi task chạy `cd mobile && npm run typecheck`; nếu lỗi, dán nguyên lỗi cho DeepSeek sửa rồi mới sang task tiếp.
- Nếu bạn đã chạy một số task của bản thiết kế cũ (bottom tabs, màn Cài đặt…), cứ đi tiếp từ Task 0: prompt đã dặn *"nếu file đã tồn tại thì ghi đè theo đặc tả mới"* và Task 31 sẽ dọn phần cũ.
- **Cập nhật V2.1:** sau khi test, mục **K (Task 34–42)** vá một chỗ hiểu nhầm (ô "Dịch từ" bấm được, bỏ "Ngôn ngữ mặc định" khỏi màn "Dịch sang") và thêm bước kiểm tra ngôn ngữ backend hỗ trợ. Task 25 đã bị thay bằng Task 37–38.
- Quy tắc bất biến (nhắc lại trong từng prompt): không sửa backend (trừ Task 33 tuỳ chọn), không sửa `mobile/src/config/api.ts`, không xoá logic API/stream/liveAudio hiện có.

## Thiết kế V2 tóm tắt (để bạn nắm — DeepSeek nhận bản chi tiết trong từng prompt)

- **Không còn thanh tab dưới.** Chỉ 1 màn hình chính "Dịch & Đọc" + các màn phụ toàn màn hình.
- Màn chính: tiêu đề + nút mặt trời (đổi sáng/tối) · hàng ngôn ngữ (Dịch từ **Tiếng Việt** bấm được → Dịch sang **English** bấm được) · ô nhập văn bản lớn có 2 nút tròn **mic** và **camera** · link "+ Thêm ngữ cảnh (không bắt buộc)" mở thẻ ngữ cảnh (ghi chú + 4 giọng văn) · nút **Dịch** dưới cùng · kết quả hiện ngay trên màn chính (nút **Đọc to** + nút sao chép) · lỗi hiện thẻ đỏ có nút **Thử lại**.
- Màn phụ: **Dịch sang** (danh sách đủ các ngôn ngữ app hỗ trợ: English, 中文, 日本語, 한국어, Français, Deutsch, Español, Português), **Dịch từ** (chọn ngôn ngữ nguồn, được nhớ cho lần mở app sau), **Đang nghe…** (chữ hiện theo thời gian thực), **Camera quét chữ** (4 trạng thái: sẵn sàng / đang nhận dạng vàng / lỗi đỏ / chưa có quyền camera).
- **Tỉ lệ màn hình:** thiết kế gốc dựa trên máy chuẩn **411×890 dp (Pixel 6)**. Mọi kích thước trong code phải đi qua hàm co giãn `s()` / `vs()` / `ms()` (Task 2) để không lệch trên máy khác.

## Mục lục

| Nhóm | Task |
| :--- | :--- |
| A. Chuẩn bị | 0 Giới thiệu · 1 Cài thư viện + cấu hình · 2 Hàm co giãn tỉ lệ · 3 Theme sáng/tối + font · 4 Chuỗi tiếng Việt · 5 Danh sách ngôn ngữ |
| B. Component dùng chung | 6 Nút tròn icon · 7 Nút chính + nút viền · 8 Card + Header màn phụ · 9 Chip giọng văn · 10 Thẻ lỗi · 11 Sóng âm · 12 Khung 4 góc |
| C. Store | 13 Store dịch · 14 Store cài đặt · 15 Ngữ cảnh + gọi dịch + lỗi |
| D. Điều hướng | 16 Stack không tab |
| E. Màn chính | 17 Header + hàng ngôn ngữ · 18 Ô nhập · 19 Thẻ ngữ cảnh · 20 Nút Dịch + bàn phím · 21 Kết quả + Đọc to · 22 Lỗi + Thử lại · 23 Đổi sáng/tối + tự dịch |
| F. Màn ngôn ngữ | 24 Dịch sang · 25 Ngôn ngữ mặc định |
| G. Màn Giọng nói | 26 Giao diện · 27 Logic |
| H. Màn Camera | 28 Giao diện + xin quyền · 29 Chụp/thư viện/đèn pin · 30 Nhận dạng + lỗi |
| I. Hoàn thiện | 31 Dọn code cũ · 32 Rà soát tỉ lệ + checklist · 33 (Tuỳ chọn) backend |
| K. Sửa đổi V2.1 (sau test) | 34 Kiểm tra ngôn ngữ backend · 35 Danh mục ngôn ngữ · 36 Store nguồn đổi được · 37 Bỏ "ngôn ngữ mặc định" ở Dịch sang · 38 Màn Dịch từ · 39 Màn Dịch sang theo danh mục · 40 Mic/camera theo ngôn ngữ · 41 Đọc to theo ngôn ngữ · 42 Rà soát · 43 Ô Dịch từ giống Dịch sang |

---

# A. CHUẨN BỊ

## TASK 0 — Giới thiệu dự án, đọc hiện trạng (chưa viết code)

**PROMPT**

````text
Bạn là lập trình viên React Native (Expo, TypeScript) giàu kinh nghiệm. Tôi giao việc theo từng bước nhỏ, mỗi lần một việc.

Dự án: Translation-App. Thư mục mobile/ là app React Native Expo (TypeScript, Zustand, axios, expo-av, React Navigation). Backend FastAPI ở backend/ đã xong, KHÔNG được sửa. Tôi đính kèm giai_thich.md để bạn hiểu dự án (đặc biệt mục 6 "Mobile chi tiết").

Nhiệm vụ tổng thể: làm lại GIAO DIỆN app mobile theo thiết kế mới (V2), toàn bộ bằng tiếng Việt. Bạn không xem được file thiết kế nên tôi sẽ mô tả thật chi tiết trong từng bước. Tóm tắt thiết kế V2:
- KHÔNG có thanh tab dưới. Chỉ có 1 màn hình chính "Dịch & Đọc" và các màn phụ toàn màn hình.
- Màn chính: tiêu đề + nút tròn biểu tượng mặt trời (đổi giao diện sáng/tối); hàng ngôn ngữ "Dịch từ: Tiếng Việt" (bấm để mở màn "Dịch từ" đổi ngôn ngữ nguồn) → "Dịch sang: English" (bấm để đổi); ô nhập văn bản lớn có 2 nút tròn mic và camera; link "+ Thêm ngữ cảnh (không bắt buộc)" mở thẻ ngữ cảnh (ghi chú + 4 giọng văn chọn nhiều); nút "Dịch" ở đáy; kết quả dịch hiện ngay trên màn chính kèm nút "Đọc to" và nút sao chép; lỗi hiện thẻ đỏ kèm nút "Thử lại".
- Màn phụ: "Dịch sang" (danh sách các ngôn ngữ app hỗ trợ: English, 中文, 日本語, 한국어, Français, Deutsch, Español, Português), "Dịch từ", "Đang nghe…" (chữ hiện theo thời gian thực), Camera quét chữ (nhiều trạng thái).
- Thiết kế gốc dựa trên máy chuẩn 411x890 dp (Pixel 6). Mọi kích thước phải co giãn theo tỉ lệ màn hình (sẽ làm ở bước 2).

Quy tắc bắt buộc cho MỌI bước:
1. Không sửa backend. Không sửa mobile/src/config/api.ts (file tự sinh).
2. Không xoá logic hiện có của services/api.ts, services/stream.ts, services/liveAudio.ts.
3. TypeScript strict, không dùng any mới.
4. Nếu một file tôi yêu cầu tạo đã tồn tại từ phiên bản giao diện cũ, hãy ghi đè theo đặc tả mới (không tạo bản trùng tên).
5. Màu và kích thước lấy từ theme + hàm co giãn (sẽ tạo ở bước 2–3), không hardcode rải rác.

Bây giờ CHƯA viết code. Hãy: (a) đọc toàn bộ mobile/src và tóm tắt ngắn gọn bằng tiếng Việt cấu trúc hiện tại (đặc biệt store, services, navigation, screens, components); (b) cho biết các file nào có vẻ thuộc giao diện cũ (tab dưới Văn bản/Giọng nói/Ảnh/Cài đặt, panel Voice Cloning) và có thể bị thay; (c) trả lời "Đã hiểu" và chờ bước tiếp theo.
````

**GIẢI THÍCH**
- **Làm gì:** cho DeepSeek nắm bối cảnh + luật chơi và xem nó đã hiểu code hiện tại chưa.
- **Sửa gì:** không sửa file nào.
- **Đính kèm:** `giai_thich.md`.
- **Kiểm tra:** tóm tắt phải nhắc đúng `translationStore.ts`, `services/api.ts`, `stream.ts`, `liveAudio.ts`. Sai thì bảo đọc lại.

---

## TASK 1 — Cài thư viện + cấu hình app

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Không sửa backend, không sửa src/config/api.ts. Phải chạy được trong Expo Go.

Việc cần làm (CHỈ việc này):
1. Kiểm tra package.json rồi cài các thư viện còn thiếu bằng "npx expo install":
   - @react-navigation/native-stack (cùng major với @react-navigation/native đang dùng)
   - expo-camera (chụp ảnh, bật đèn pin)
   - expo-image-picker (chọn ảnh thư viện)
   - expo-clipboard (sao chép bản dịch)
   - @react-native-async-storage/async-storage
   - expo-font và @expo-google-fonts/be-vietnam-pro (font hỗ trợ tốt dấu tiếng Việt)
   - Đảm bảo đã có: expo-av, react-native-safe-area-context, react-native-screens, @expo/vector-icons
2. Sửa app.json:
   - "orientation": "portrait" (khoá dọc).
   - Thêm plugin expo-camera với cameraPermission: "Để quét chữ trong ảnh, hãy cho phép Dịch & Đọc dùng camera. Ảnh chỉ dùng để nhận dạng, không được lưu." và recordAudioAndroid: false.
   - Giữ nguyên các quyền micro hiện có của app.
3. KHÔNG gỡ @react-navigation/bottom-tabs nếu đang có (sẽ dọn ở bước sau).
Không viết thêm code nào khác. Cuối cùng liệt kê thư viện đã có sẵn và thư viện mới thêm.
````

**GIẢI THÍCH**
- **Làm gì:** chuẩn bị thư viện cho camera trực tiếp, chọn ảnh, sao chép, lưu bền, font Việt; khoá màn hình dọc để tỉ lệ ổn định.
- **Sửa gì:** `mobile/package.json`, `mobile/app.json`.
- **Kiểm tra:** `npx expo start` vẫn chạy, giao diện chưa đổi.

---

## TASK 2 — Hàm co giãn theo tỉ lệ màn hình (chuẩn 411×890)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Không sửa backend, không sửa src/config/api.ts.

Mục tiêu: thiết kế gốc dùng máy chuẩn 411x890 dp (Pixel 6). Để giao diện không lệch trên máy khác, MỌI kích thước (width, height, padding, margin, borderRadius, fontSize, icon size) phải đi qua các hàm co giãn.

Việc cần làm (CHỈ việc này): tạo mobile/src/utils/scale.ts:
- Hằng số BASE_WIDTH = 411, BASE_HEIGHT = 890.
- Lấy kích thước bằng Dimensions.get('window'); dùng cạnh ngắn làm width và cạnh dài làm height (để xoay máy không phá tính toán).
- Hàm s(size): co giãn theo chiều ngang = size * (width / BASE_WIDTH). Dùng cho: chiều rộng, padding/margin ngang, borderRadius, kích thước nút/icon vuông.
- Hàm vs(size): co giãn theo chiều dọc = size * (height / BASE_HEIGHT). Dùng cho: chiều cao khối lớn (ô nhập, thẻ, nút), khoảng cách dọc.
- Hàm ms(size, factor = 0.5): co giãn vừa phải = size + (s(size) - size) * factor. Dùng cho: cỡ chữ, lineHeight, icon.
- Kẹp hệ số co giãn trong khoảng [0.8, 1.3] (clamp) để không quá nhỏ trên máy bé hay quá to trên tablet; kết quả làm tròn bằng PixelRatio.roundToNearestPixel.
- Export thêm: isSmallDevice (height < 700), MAX_CONTENT_WIDTH = 560 (nội dung chính trên tablet được căn giữa với maxWidth này), SCREEN_WIDTH, SCREEN_HEIGHT.
- Ghi comment đầu file giải thích quy ước s/vs/ms (như trên) bằng tiếng Việt, và quy tắc: "KHÔNG viết số cứng cho kích thước trong StyleSheet, trừ độ dày viền 1 (StyleSheet.hairlineWidth hoặc 1) và 0".

Trong mọi component/màn hình sau này, dùng: s() cho ngang/bo góc/padding, vs() cho chiều cao khối lớn, ms() cho chữ/icon. Cũng yêu cầu: với Text luôn đặt maxFontSizeMultiplier={1.2} để chữ hệ thống phóng to không phá bố cục (sẽ làm trong component Text/ThemedText ở bước 3).

Chưa sửa màn hình nào.
````

**GIẢI THÍCH**
- **Làm gì:** tạo "thước đo" co giãn theo máy chuẩn Pixel 6 (411×890); mọi số đo trong code sẽ nhân tỉ lệ để khỏi lệch giữa các điện thoại.
- **Sửa gì:** tạo mới `mobile/src/utils/scale.ts`.
- **Kiểm tra:** typecheck sạch; ở các bước sau mỗi prompt đều nhắc dùng `s()/vs()/ms()`.

---

## TASK 3 — Theme sáng/tối + font + ThemedText

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Đã có src/utils/scale.ts (s, vs, ms). Đã cài expo-font và @expo-google-fonts/be-vietnam-pro. Không sửa backend, không sửa src/config/api.ts. Nếu file đã tồn tại từ bản cũ thì ghi đè theo đặc tả mới.

Việc cần làm (CHỈ việc này), tạo trong mobile/src/theme/:

1. colors.ts export 2 bảng màu lightColors và darkColors cùng kiểu ThemeColors:
LIGHT: background #F2F3FA, surface #FFFFFF, surfaceMuted #ECEEF6 (ô "Dịch từ" bị làm mờ), inputBg #F6F7FC, border #E3E6F0, borderStrong #C9CDDB, primary #3347D6, onPrimary #FFFFFF, primarySoft #E6E8FF (nút tròn mic/camera/sao chép), primarySoftStrong #DDE2FB (hàng ngôn ngữ đang chọn), primaryDark #1E2A9E, textPrimary #111827, textSecondary #5B6075, placeholder #7A7D87, interimText #6B7280 (chữ đang nhận dạng chưa chốt), disabledBg #DDE1EC, disabledText #5B6075, iconButtonBg #E9EBF4, danger #B42318, dangerSoft #FFEFEE, dangerBorder #F0B8B5, dangerTitle #8A1C14, dangerText #6B2B28.
DARK: background #0F1220, surface #181C2E, surfaceMuted #1F2438, inputBg #131728, border #2A3050, borderStrong #3A4166, primary #6B7DFF, onPrimary #0B1033, primarySoft #262C57, primarySoftStrong #2B3366, primaryDark #AEB8FF, textPrimary #F2F4FA, textSecondary #A3A9C0, placeholder #8087A0, interimText #9BA1B8, disabledBg #252A40, disabledText #7E85A0, iconButtonBg #252A40, danger #FF6B5E, dangerSoft #3A1F22, dangerBorder #6B2F2F, dangerTitle #FFB4AC, dangerText #E8C4C0.
Ngoài ra export cameraColors (cố định, không đổi theo theme, dùng cho màn camera): background #1E2B38, bottomBar #0F1A22, pill #182836, circleButton #2F3D49, closeButton rgba(255,255,255,0.25), frameWhite #FFFFFF, frameYellow #F2C94C, frameRed #FF6B5E, descText #B8C2D0, hintText #A9B4FF, text #FFFFFF.

2. ThemeProvider.tsx: React context cung cấp { colors, mode: 'light' | 'dark', toggleMode(), setMode() }. Giá trị khởi tạo lấy từ useColorScheme() của hệ thống (lưu bền sẽ nối ở bước sau, tạm để mode trong state). Export hook useTheme(). Export hàm tiện ích useThemedStyles(makeStyles: (colors: ThemeColors) => T) trả về StyleSheet đã tạo, memo theo colors, để các màn hình tạo style động theo theme.

3. typography.ts: tên font Be Vietnam Pro: regular = 'BeVietnamPro_400Regular', medium = 'BeVietnamPro_500Medium', semibold = 'BeVietnamPro_600SemiBold', bold = 'BeVietnamPro_700Bold'. Export các kiểu chữ (đều dùng ms()):
- title (26, bold) — tiêu đề "Dịch & Đọc"
- screenTitle (28, bold) — tiêu đề màn phụ ("Dịch sang")
- bodyLarge (24, medium, lineHeight 34) — chữ trong ô nhập
- result (25, semibold, lineHeight 38) — bản dịch
- button (19, bold)
- itemTitle (19, bold) — hàng ngôn ngữ
- cardTitle (17, bold)
- label (12, medium) — nhãn nhỏ như "Dịch từ"
- value (17, bold)
- body (15, regular), caption (14, regular)

4. ThemedText.tsx: component Text bọc sẵn: prop variant (key của typography), prop color (key của ThemeColors, mặc định textPrimary), maxFontSizeMultiplier mặc định 1.2, các prop Text khác truyền xuống.

5. Trong mobile/App.tsx: bọc ThemeProvider; load font bằng useFonts (4 font trên); trong lúc chưa load xong thì hiện màn nền background không chữ (không crash). StatusBar style theo mode (dark-content khi light, light-content khi dark). Giữ nguyên SafeAreaProvider + NavigationContainer hiện có.

Chưa sửa màn hình nào.
````

**GIẢI THÍCH**
- **Làm gì:** tạo hệ màu sáng/tối (nút mặt trời ở màn chính sẽ đổi giữa hai bảng này), font Be Vietnam Pro, và component chữ dùng chung.
- **Sửa gì:** tạo `theme/colors.ts`, `ThemeProvider.tsx`, `typography.ts`, `ThemedText.tsx`; sửa `App.tsx`.
- **Lưu ý:** bảng màu **tối do mình tự đề xuất** (PDF chỉ có bản sáng). Muốn đổi màu, sửa trong `colors.ts`.
- **Kiểm tra:** typecheck sạch; app vẫn mở được (dù màn hình cũ chưa đổi).

---

## TASK 4 — Gom chuỗi tiếng Việt

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Không sửa backend, không sửa src/config/api.ts. Ghi đè nếu file đã tồn tại.

Việc cần làm (CHỈ việc này): tạo mobile/src/constants/strings.ts export object `strings` (as const) chứa mọi chuỗi giao diện:

home:
- title "Dịch & Đọc"
- from "Dịch từ", to "Dịch sang"
- placeholder "Nhập văn bản cần dịch"
- addContext "Thêm ngữ cảnh", contextOptional "(không bắt buộc)"
- contextAdded "Ngữ cảnh đã thêm"
- translate "Dịch", translating "Đang dịch…"
- readAloud "Đọc to", stopReading "Dừng"
- copied "Đã sao chép"
context:
- title "Ngữ cảnh"
- optional "(không bắt buộc)"
- notePlaceholder "Ví dụ: gửi cho khách hàng, giữ nguyên từ “deadline”."
- noteMax 200
tones: formal "Trang trọng", friendly "Thân mật", academic "Học thuật", business "Kinh doanh"
error:
- translateTitle "Không dịch được"
- network "Không kết nối được tới máy chủ dịch. Kiểm tra mạng rồi thử lại."
- generic "Đã có lỗi xảy ra. Vui lòng thử lại."
- retry "Thử lại"
targetLanguage: title "Dịch sang", available "Ngôn ngữ có sẵn", setDefault "Đổi ngôn ngữ mặc định"
defaultLanguage: title "Ngôn ngữ mặc định", description "Ngôn ngữ này được chọn sẵn mỗi lần mở app. Bạn vẫn đổi được ở màn Dịch.", section "Dịch sang"
voice:
- listening "Đang nghe…"
- hint "Hãy nói tiếng Việt. Chữ hiện ra khi bạn nói."
- hintNoLive "Hãy nói tiếng Việt. Chữ sẽ hiện sau khi bạn dừng."
- recognizing "Đang nhận dạng…"
- tapToStop "Chạm để dừng và dịch"
- noSpeech "Chưa nghe thấy giọng nói. Hãy thử lại."
- permissionDenied "Cần quyền micro để nhận dạng giọng nói."
camera:
- pill "Đưa chữ vào khung"
- recognizing "Đang nhận dạng chữ…"
- recognizingHint "(xong → dịch)"
- failTitle "Không nhận dạng được chữ nào"
- failHint "Thử ở nơi đủ sáng, giữ máy thẳng và gần chữ hơn."
- retake "Chụp lại"
- permissionTitle "Cần quyền dùng camera"
- permissionBody "Để quét chữ trong ảnh, hãy cho phép Dịch & Đọc dùng camera. Ảnh chỉ dùng để nhận dạng, không được lưu."
- openSettings "Mở cài đặt quyền"
- typeInstead "Nhập văn bản thay thế"
accessibility: các nhãn cho nút icon: toggleTheme "Đổi giao diện sáng tối", clear "Xoá văn bản", mic "Nói để nhập văn bản", camera "Quét chữ bằng camera", copy "Sao chép bản dịch", back "Quay lại", close "Đóng", gallery "Chọn ảnh từ thư viện", torch "Bật tắt đèn pin", shutter "Chụp ảnh".

Chưa sửa màn hình nào.
````

**GIẢI THÍCH**
- **Làm gì:** gom toàn bộ chữ tiếng Việt vào một chỗ, đúng từng chữ trong thiết kế.
- **Sửa gì:** tạo mới `constants/strings.ts`.
- **Kiểm tra:** đối chiếu chữ với bản thiết kế (dấu, dấu ba chấm "…").

---

## TASK 5 — Danh sách ngôn ngữ (nguồn cố định + 3 đích)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Không sửa backend, không sửa src/config/api.ts.

Việc cần làm (CHỈ việc này): sửa mobile/src/constants/languages.ts.
1. GIỮ NGUYÊN mảng LANGUAGES, STT_LANGUAGES, hàm supportsSpeechToText hiện có (không xoá ngôn ngữ nào khỏi code).
2. Thêm export SOURCE_LANGUAGE = { code: 'vi', label: 'Tiếng Việt' } (nguồn cố định, vì nhận dạng giọng nói chỉ hỗ trợ tiếng Việt).
3. Thêm export TARGET_LANGUAGES: danh sách các ngôn ngữ ĐÍCH mà app hỗ trợ = TOÀN BỘ ngôn ngữ trong LANGUAGES hiện có TRỪ tiếng Việt ('vi'), giữ đúng thứ tự như danh sách "Select input language" của app cũ. Tối thiểu phải có 8 ngôn ngữ sau, theo đúng thứ tự này, mỗi phần tử { code, label, shortLabel }:
   - English → label 'English', shortLabel 'English'
   - Chinese (Simplified) → label '中文 (Mandarin)', shortLabel '中文'
   - Japanese → label '日本語 (Japanese)', shortLabel '日本語'
   - Korean → label '한국어 (Korean)', shortLabel '한국어'
   - French → label 'Français (French)', shortLabel 'Français'
   - German → label 'Deutsch (German)', shortLabel 'Deutsch'
   - Spanish → label 'Español (Spanish)', shortLabel 'Español'
   - Portuguese → label 'Português (Portuguese)', shortLabel 'Português'
   Nếu LANGUAGES còn ngôn ngữ nào khác ngoài 8 ngôn ngữ trên (danh sách cũ có thể dài hơn phần nhìn thấy), cũng thêm vào cuối theo mẫu label "Tên bản ngữ (Tên tiếng Anh)".
   Với mỗi ngôn ngữ, `code` PHẢI là mã mà backend đang nhận (lấy từ mã trong LANGUAGES hiện có và kiểm tra khớp với LANGUAGE_NAMES trong backend/app/models/translation_adapter.py; ví dụ tiếng Trung có thể là 'zh' hoặc 'zh-CN'; nếu code trong app cũ khác backend thì dùng code backend và ghi chú lại).
4. Thêm hàm getTargetLabel(code: string): string trả về shortLabel (dùng hiển thị trên thẻ "Dịch sang" ở màn chính, ví dụ "English", "中文", "日本語"); và hàm getTargetFullLabel(code: string): string trả về label đầy đủ. Không tìm thấy thì trả lại chính code.
5. Thêm kiểu TargetLanguageCode suy ra từ TARGET_LANGUAGES (as const) và hằng DEFAULT_TARGET_CODE = mã của English.
Cuối cùng liệt kê cho tôi bảng: tên ngôn ngữ → code đang dùng ở backend (đủ tất cả ngôn ngữ trong TARGET_LANGUAGES), và cho biết ngôn ngữ nào có giọng đọc (TTS) trong backend/app/models/tts_adapter.py.
````

**GIẢI THÍCH**
- **Làm gì:** UI V2 dịch từ tiếng Việt sang **tất cả ngôn ngữ app đang hỗ trợ**: English, 中文 (Chinese Simplified), 日本語, 한국어, Français, Deutsch, Español, Português (và ngôn ngữ nào khác còn trong danh sách cũ). Mỗi ngôn ngữ có tên đầy đủ (cho danh sách chọn) và tên ngắn (cho thẻ "Dịch sang" ở màn chính).
- **Sửa gì:** `constants/languages.ts`.
- **Kiểm tra:** mã từng ngôn ngữ phải khớp backend (không khớp sẽ dịch sai/không dịch). DeepSeek sẽ trả bảng tên → mã để bạn đối chiếu. Phần "giọng đọc" cho biết ngôn ngữ nào đọc to được.

---

# B. COMPONENT DÙNG CHUNG

> Quy ước kích thước trong các prompt: mọi số là **dp trên máy chuẩn 411×890**; trong code phải bọc `s()` (ngang, bo góc, padding, nút vuông), `vs()` (cao khối lớn, khoảng cách dọc), `ms()` (chữ, icon). Màu lấy từ `useTheme()`.

## TASK 6 — IconCircleButton (nút tròn có icon)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Đã có utils/scale.ts, theme (useTheme, useThemedStyles), constants/strings.ts. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; trong code bọc s()/vs()/ms(). Màu lấy từ useTheme().

Việc cần làm (CHỈ việc này): tạo mobile/src/components/IconCircleButton.tsx — nút tròn chứa 1 icon Ionicons.
Props: icon (tên Ionicons), onPress, size ('small' | 'medium' | 'large'), variant ('soft' | 'neutral' | 'cameraDark' | 'cameraClose'), accessibilityLabel (bắt buộc), disabled?, iconColor? (ghi đè).
Kích thước đường kính: small 46, medium 50, large 54 (dp). Icon: ms(22) với medium, ms(20) với small, ms(26) với large.
Màu:
- soft: nền colors.primarySoft, icon colors.primaryDark (nút mic, camera, sao chép trong ô nhập/kết quả).
- neutral: nền colors.iconButtonBg, icon colors.textPrimary (nút mặt trời, nút quay lại, nút đóng ×).
- cameraDark: nền cameraColors.circleButton, icon trắng (nút thư viện, đèn pin trong thanh camera).
- cameraClose: nền cameraColors.closeButton, icon trắng.
Hiệu ứng nhấn: opacity 0.7 khi pressed (Pressable). hitSlop 6. accessibilityRole="button".
Export default. Chưa gắn vào màn hình.
````

**GIẢI THÍCH**
- **Làm gì:** tạo nút tròn dùng cho mic, camera, sao chép, mặt trời, quay lại, ×, thư viện, đèn pin.
- **Sửa gì:** tạo mới `components/IconCircleButton.tsx`.

---

## TASK 7 — PrimaryButton và OutlineButton

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Đã có utils/scale.ts, theme, ThemedText. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; trong code bọc s()/vs()/ms(). Màu lấy từ useTheme().

Việc cần làm (CHỈ việc này): tạo 2 component trong mobile/src/components/:

1. PrimaryButton.tsx — nút full-width, cao vs(59), bo góc s(22), chữ typography.button căn giữa.
   Props: label, onPress, disabled?, loading?, iconLeft? (Ionicons), variant? ('primary' | 'pill'), accessibilityLabel?.
   - primary: nền colors.primary, chữ colors.onPrimary (trắng) đậm.
   - disabled: nền colors.disabledBg, chữ colors.disabledText, không bấm được.
   - loading: hiện ActivityIndicator (màu chữ) bên cạnh nhãn; không bấm được.
   - 'pill': nút nhỏ KHÔNG full-width, cao vs(50), bo tròn hoàn toàn (borderRadius lớn), padding ngang s(22), nền primary, có iconLeft màu trắng ms(22) + nhãn đậm ms(17) — dùng cho nút "Đọc to" có icon loa.
2. OutlineButton.tsx — nút full-width cao vs(48), bo góc s(14), nền surface (hoặc trắng), viền 1px.
   Props: label, onPress, iconLeft?, tone? ('default' | 'danger' | 'dark'), fullWidth? (mặc định true).
   - default: viền colors.borderStrong, chữ colors.textPrimary đậm ms(17).
   - danger: viền colors.danger, chữ & icon colors.danger (nút "Thử lại" trong thẻ lỗi; icon "refresh").
   - dark: nền trắng, chữ #111827 đậm (nút "Chụp lại" trên nền camera tối), icon "refresh".
   Với trường hợp nút "Nhập văn bản thay thế" (màn xin quyền camera) cần cao vs(59), bo s(22): thêm prop size ('md' = vs(48)/s(14), 'lg' = vs(59)/s(22)).
Cả hai: accessibilityRole="button", Pressable với opacity 0.85 khi nhấn. Export default. Chưa gắn vào màn hình.
````

**GIẢI THÍCH**
- **Làm gì:** nút "Dịch" (xám khi chưa có chữ, xanh khi có), nút "Đọc to" dạng viên thuốc có icon loa, nút viền "Thử lại"/"Chụp lại"/"Nhập văn bản thay thế".
- **Sửa gì:** tạo mới `PrimaryButton.tsx`, `OutlineButton.tsx`.

---

## TASK 8 — Card + ScreenHeader (cho màn phụ)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Đã có utils/scale.ts, theme, ThemedText, IconCircleButton. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): tạo 2 component trong mobile/src/components/:

1. Card.tsx — View bao nội dung: nền colors.surface, viền 1px colors.border, bo góc s(24), padding s(22). Props: children, style?, onPress? (nếu có thì bọc Pressable).
2. ScreenHeader.tsx — dùng cho màn phụ ("Dịch sang", "Ngôn ngữ mặc định"): hàng ngang cao s(46): bên trái IconCircleButton (icon "chevron-back", size small, variant neutral, accessibilityLabel "Quay lại", onPress = goBack từ props) rồi khoảng cách s(12) rồi tiêu đề (typography.screenTitle, 28 đậm). Props: title, onBack.
Export default. Chưa gắn vào màn hình.
````

**GIẢI THÍCH**
- **Làm gì:** thẻ trắng bo góc dùng ở ô nhập/kết quả; thanh tiêu đề có nút quay lại tròn cho màn phụ.
- **Sửa gì:** tạo mới `Card.tsx`, `ScreenHeader.tsx`.

---

## TASK 9 — ToneChip (chip giọng văn có checkbox)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Đã có utils/scale.ts, theme, ThemedText. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): tạo mobile/src/components/ToneChip.tsx — chip chọn nhiều có ô checkbox vuông bên trái.
Props: label, checked, onToggle.
Bố cục: hàng ngang, cao vs(47), bo tròn hoàn toàn (pill), padding ngang s(16), khoảng cách checkbox–chữ s(12).
- Checkbox: ô vuông s(18)x s(18), bo góc s(3), viền 1.5px.
- Chưa chọn: nền colors.surface, viền 1px colors.borderStrong; checkbox rỗng viền colors.textSecondary; chữ colors.textPrimary, weight medium, ms(17).
- Đã chọn: nền colors.primarySoft, viền 1.5px colors.primary; checkbox nền colors.primaryDark (hoặc colors.primary) với dấu tick trắng (Ionicons "checkmark", ms(13)); chữ colors.primaryDark, weight bold, ms(17).
accessibilityRole="checkbox", accessibilityState={{ checked }}. Export default. Chưa gắn vào màn hình.
````

**GIẢI THÍCH**
- **Làm gì:** chip "Trang trọng / Thân mật / Học thuật / Kinh doanh" có ô tick, chọn nhiều.
- **Sửa gì:** tạo mới `components/ToneChip.tsx`.

---

## TASK 10 — ErrorCard (thẻ lỗi đỏ)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Đã có utils/scale.ts, theme, ThemedText, OutlineButton. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): tạo mobile/src/components/ErrorCard.tsx.
Props: title, message, onRetry, retryLabel? (mặc định strings.error.retry).
Bố cục: View nền colors.dangerSoft, viền 1px colors.dangerBorder, bo góc s(22), padding s(17).
- Hàng đầu: icon Ionicons "alert-circle-outline" ms(22) màu colors.danger, khoảng cách s(12), bên phải là cột chữ: title đậm ms(17) màu colors.dangerTitle; message ms(15) màu colors.dangerText, lineHeight ms(21).
- Cách hàng đầu vs(14), dưới là OutlineButton tone 'danger', label "Thử lại", iconLeft "refresh", full-width (cao vs(48), bo s(14)), bấm gọi onRetry.
accessibilityRole="alert" cho khối chữ. Export default. Chưa gắn vào màn hình.
````

**GIẢI THÍCH**
- **Làm gì:** thẻ lỗi nền hồng nhạt "Không dịch được / Không kết nối được tới máy chủ dịch…" kèm nút "Thử lại".
- **Sửa gì:** tạo mới `components/ErrorCard.tsx`.

---

## TASK 11 — Waveform (sóng âm 13 thanh)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Đã có utils/scale.ts, theme. Không sửa backend, không sửa src/config/api.ts. Không thêm thư viện native.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms().

Việc cần làm (CHỈ việc này): tạo mobile/src/components/Waveform.tsx.
Props: active: boolean, level?: number (0..1, mức âm lượng tuỳ chọn).
- 13 thanh dọc bo tròn hoàn toàn, rộng s(6), cách nhau s(9) (tổng rộng ~s(159)), màu colors.primary, căn giữa theo chiều dọc (cùng tâm).
- Chiều cao nền (dp) lần lượt: 20, 34, 52, 30, 56, 36, 18, 46, 30, 52, 28, 38, 16 (thanh ở giữa-trái cao nhất; mô phỏng sóng âm ngẫu nhiên). Bọc vs().
- Khi active=true: mỗi thanh co giãn chiều cao theo vòng lặp mượt (Animated.loop với Animated.timing, mỗi thanh lệch pha/thời lượng 500–900ms khác nhau), dùng transform scaleY với useNativeDriver: true (scaleY từ 0.45 đến 1.0). Nếu có level thì biên độ lớn nhất nhân theo (0.5 + level*0.5).
- Khi active=false: về chiều cao nền, đứng yên, opacity 0.6.
- Dọn animation khi unmount. Bọc toàn bộ trong accessible={false} importantForAccessibility="no-hide-descendants".
Export default. Chưa gắn vào màn hình.
````

**GIẢI THÍCH**
- **Làm gì:** sóng âm xanh nhảy khi đang nghe ở màn "Đang nghe…".
- **Sửa gì:** tạo mới `components/Waveform.tsx`.

---

## TASK 12 — CornerFrame (khung 4 góc cho camera)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Đã có utils/scale.ts, theme (cameraColors). Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms().

Việc cần làm (CHỈ việc này): tạo mobile/src/components/CornerFrame.tsx — khung quét gồm 4 dấu góc hình chữ L bo tròn, nền trong suốt (pointerEvents="none").
Props: color: string, top?: number, bottom?: number (khoảng cách từ mép trên/dưới màn hình tính theo dp; mặc định top = 93, bottom = 165 tức đáy khung cách đáy màn hình 165dp), horizontalInset?: number (mặc định 25).
- Khung được đặt absolute phủ màn hình: left/right = s(horizontalInset), top = vs(top), bottom = vs(bottom).
- Mỗi góc: View kích thước s(38) x s(38), viền dày 3px chỉ ở hai cạnh tạo chữ L (ví dụ góc trên-trái: borderTopWidth + borderLeftWidth; borderTopLeftRadius s(20)), màu = prop color. Bốn góc đặt ở 4 góc của khung (trên-trái, trên-phải, dưới-trái, dưới-phải) với bo góc tương ứng.
- Có animation đổi màu mượt giữa các trạng thái (Animated hoặc chuyển ngay nếu phức tạp; ưu tiên đơn giản, không crash).
Export default. Chưa gắn vào màn hình.
````

**GIẢI THÍCH**
- **Làm gì:** khung 4 góc trên màn camera: trắng (sẵn sàng), vàng (đang nhận dạng), đỏ san hô (lỗi).
- **Sửa gì:** tạo mới `components/CornerFrame.tsx`.

---

# C. STORE

## TASK 13 — translationStore: trạng thái màn chính mới

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). Không sửa backend, không sửa src/config/api.ts, KHÔNG xoá action/state hiện có trong translationStore.ts (inputLanguage, targetLanguage, vietnameseText, translatedText, translate, startStreaming, stopStreaming, processImage, v.v.). Xem services/api.ts để biết các hàm gọi API.

Việc cần làm (CHỈ việc này): THÊM vào mobile/src/store/translationStore.ts (không đổi hành vi cũ):

State mới:
- phase: 'idle' | 'translating' | 'result' | 'error' (mặc định 'idle') — trạng thái khối kết quả trên màn chính
- tones: ToneId[] (ToneId = 'formal' | 'friendly' | 'academic' | 'business'), mặc định []
- contextNote: string, mặc định ''
- contextOpen: boolean, mặc định false (thẻ ngữ cảnh đang mở)
- translateError: string | null
- pendingAutoTranslate: boolean, mặc định false (cờ "vừa nhập từ giọng nói/camera, tự dịch khi về màn chính")

Action mới:
- setText(text: string): đặt vietnameseText; nếu phase là 'result' hoặc 'error' thì đưa phase về 'idle' và xoá translatedText, translateError (sửa nội dung thì kết quả cũ không còn đúng)
- clearText(): xoá vietnameseText, translatedText, translateError, phase='idle'
- toggleTone(tone: ToneId), setContextNote(note: string) (cắt tối đa 200 ký tự), toggleContext(), setContextOpen(open: boolean) — các hàm đổi tone/ghi chú cũng đưa phase từ 'result'/'error' về 'idle'
- setTargetLang(code) : đặt targetLanguage (store hiện có) và nếu phase là 'result'/'error' thì về 'idle' và xoá translatedText
- requestAutoTranslate(text: string): đặt vietnameseText = text, pendingAutoTranslate = true
- consumeAutoTranslate(): đặt pendingAutoTranslate = false (trả về giá trị cũ)
- Cố định inputLanguage = 'vi' (nguồn luôn tiếng Việt); nếu code cũ cho đổi inputLanguage thì để nguyên, UI mới không dùng.

Export kiểu ToneId. KHÔNG sửa hàm translate() ở bước này (sẽ sửa ở bước 15). Chưa sửa màn hình nào.
````

**GIẢI THÍCH**
- **Làm gì:** thêm "bộ nhớ" cho màn chính V2: đang ở trạng thái nào (rảnh/đang dịch/có kết quả/lỗi), giọng văn, ghi chú, thẻ ngữ cảnh đang mở hay đóng, và cờ "tự dịch sau khi nói/chụp xong".
- **Sửa gì:** chỉ thêm vào `store/translationStore.ts`.
- **Kiểm tra:** typecheck sạch, action cũ còn nguyên.

---

## TASK 14 — settingsStore: lưu bền ngôn ngữ mặc định + sáng/tối

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). Đã cài @react-native-async-storage/async-storage. Đã có theme/ThemeProvider.tsx (mode, setMode, toggleMode). Không sửa backend, không sửa src/config/api.ts. Ghi đè nếu file đã tồn tại từ bản cũ.

Việc cần làm (CHỈ việc này):
1. Tạo mobile/src/store/settingsStore.ts bằng Zustand + middleware persist (createJSONStorage(() => AsyncStorage), name 'translation-settings'):
   - defaultTargetLang: TargetLanguageCode (import từ constants/languages.ts; mặc định DEFAULT_TARGET_CODE tức English)
   - themeMode: 'light' | 'dark' | 'system' (mặc định 'system')
   - Action: setDefaultTargetLang(code), setThemeMode(mode)
   - Export cờ hasHydrated (đánh dấu đã đọc xong từ bộ nhớ, dùng onRehydrateStorage).
2. Sửa ThemeProvider.tsx để mode lấy từ settingsStore.themeMode ('system' → theo useColorScheme()); toggleMode() đổi giữa 'light' và 'dark' (từ 'system' thì đảo so với giá trị hệ thống hiện tại) và ghi vào settingsStore.
3. Trong translationStore.ts export hàm applyDefaultsFromSettings(): đặt targetLanguage = settingsStore.getState().defaultTargetLang. Tránh import vòng giữa hai store (nếu có thì đưa kiểu dùng chung sang file types.ts).
Chưa sửa màn hình nào.
````

**GIẢI THÍCH**
- **Làm gì:** nhớ lại ngôn ngữ đích mặc định và chế độ sáng/tối khi mở lại app.
- **Sửa gì:** tạo mới `store/settingsStore.ts`; sửa `theme/ThemeProvider.tsx`, `translationStore.ts` (thêm hàm).

---

## TASK 15 — buildContext + nối translate() + thông báo lỗi

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). Backend POST /api/translate nhận: text, target_language, source_language, context (chuỗi), context_preset (một trong 'Formal','Friendly','IT','Medical','Travel','General'). Xem services/api.ts để biết chữ ký apiTranslateText. Không sửa backend, không sửa src/config/api.ts.

Việc cần làm (CHỈ việc này):
1. Tạo mobile/src/utils/buildContext.ts export buildContext(tones: ToneId[], note: string): { context: string; contextPreset?: string }.
   - Tên giọng văn: formal "Trang trọng", friendly "Thân mật", academic "Học thuật", business "Kinh doanh".
   - context = các phần nối bằng ". ": nếu có tones thì "Giọng văn: <tên1>, <tên2>"; nếu note (đã trim) khác rỗng thì "Ghi chú: <note>"; cả hai rỗng thì ''.
   - contextPreset: chỉ khi tones có ĐÚNG 1 phần tử: 'formal' → 'Formal', 'friendly' → 'Friendly'; còn lại undefined.
   - Viết 4 ví dụ đầu vào/đầu ra dạng comment.
2. Sửa translate() trong translationStore.ts:
   - Kiểm tra text rỗng (trim) → set({ phase:'error', translateError: strings.error.generic }) rồi return.
   - Bắt đầu: set({ phase: 'translating', translateError: null, translatedText: '' }).
   - Gọi apiTranslateText với source 'vi', target là targetLanguage, context và contextPreset từ buildContext(tones, contextNote) (nếu apiTranslateText chưa có tham số contextPreset thì thêm tham số tuỳ chọn, giữ tương thích ngược).
   - Thành công: set({ translatedText, phase: 'result' }).
   - Lỗi: phân loại: nếu là lỗi mạng (axios error không có response, hoặc code ECONNABORTED/ERR_NETWORK) → translateError = strings.error.network; nếu có response với detail từ server → dùng extractErrorMessage; còn lại strings.error.generic. set({ phase: 'error', translateError }).
   - Giữ cờ isTranslating cũ đồng bộ với phase === 'translating' nếu code khác còn dùng.
Chưa sửa màn hình nào.
````

**GIẢI THÍCH**
- **Làm gì:** biến giọng văn + ghi chú thành chuỗi `context` gửi backend; quản lý các trạng thái dịch/kết quả/lỗi, đổi lỗi mạng thành câu tiếng Việt như thiết kế.
- **Sửa gì:** tạo `utils/buildContext.ts`; sửa `translate()` trong `translationStore.ts`; có thể thêm 1 tham số tuỳ chọn ở `services/api.ts`.
- **Kiểm tra:** đọc 4 ví dụ trong comment; tắt server rồi gọi dịch phải ra đúng câu "Không kết nối được tới máy chủ dịch…".

---

# D. ĐIỀU HƯỚNG

## TASK 16 — Stack không có tab dưới

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, React Navigation, đã cài @react-navigation/native-stack). Không sửa backend, không sửa src/config/api.ts. Không xoá file màn hình cũ (chỉ ngừng dùng).

Việc cần làm (CHỈ việc này):
1. Tạo mobile/src/navigation/types.ts: RootStackParamList = { Home: undefined; TargetLanguage: undefined; DefaultLanguage: undefined; VoiceListening: undefined; Camera: undefined }. Kèm kiểu props tiện dụng bằng NativeStackScreenProps.
2. Viết lại mobile/src/navigation/AppNavigator.tsx dùng createNativeStackNavigator, KHÔNG có tab dưới:
   - screenOptions: headerShown false, contentStyle nền theme.colors.background (lấy từ useTheme), animation 'slide_from_right' mặc định.
   - Home: HomeScreen (màn chính).
   - TargetLanguage: TargetLanguageScreen; DefaultLanguage: DefaultLanguageScreen (animation slide_from_right).
   - VoiceListening: VoiceListeningScreen với presentation 'fullScreenModal', animation 'slide_from_bottom', gestureEnabled false.
   - Camera: CameraScreen với presentation 'fullScreenModal', animation 'slide_from_bottom', gestureEnabled false.
3. Tạo các màn hình TẠM trong mobile/src/screens/ (mỗi file chỉ hiện tên màn ở giữa, nền theme background, có SafeAreaView): HomeScreen.tsx, TargetLanguageScreen.tsx, DefaultLanguageScreen.tsx, VoiceListeningScreen.tsx, CameraScreen.tsx. Nếu file cùng tên đã có thì ghi đè.
4. Trong HomeScreen tạm: 4 nút thử điều hướng sang 4 màn còn lại, để kiểm tra.
5. App.tsx giữ SafeAreaProvider + ThemeProvider + NavigationContainer; NavigationContainer dùng theme của React Navigation lấy nền từ colors.background để không chớp trắng.
Không viết giao diện thật ở bước này.
````

**GIẢI THÍCH**
- **Làm gì:** dựng bộ khung điều hướng V2: một màn chính + 4 màn phụ, hai màn (Giọng nói, Camera) bật lên toàn màn từ dưới.
- **Sửa gì:** viết lại `navigation/AppNavigator.tsx`; tạo `navigation/types.ts`; tạo/ghi đè 5 màn tạm trong `screens/`.
- **Kiểm tra:** chạy app, không còn thanh tab dưới; bấm 4 nút thử qua lại không crash.

---

# E. MÀN CHÍNH (HomeScreen)

> Bố cục tổng của màn chính (dp, máy chuẩn 411×890): lề trái/phải mỗi bên **21**; từ trên xuống: [header 46] → khoảng cách 14 → [hàng ngôn ngữ cao 59] → khoảng cách 14 → [ô nhập] → khoảng cách 14 → (khối kết quả/lỗi/thẻ ngữ cảnh) → link ngữ cảnh → … → nút Dịch dính đáy (cách đáy 17 + safe area).

## TASK 17 — HomeScreen: header + hàng ngôn ngữ (chỉ giao diện)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand, React Navigation). Đã có utils/scale.ts, theme (useTheme, useThemedStyles), ThemedText, IconCircleButton, strings, languages (SOURCE_LANGUAGE, getTargetLabel), translationStore (targetLanguage, swap không dùng nữa). Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; trong code bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): viết phần ĐẦU của mobile/src/screens/HomeScreen.tsx (ghi đè màn tạm). Chưa có ô nhập, chưa có nút Dịch.

Khung màn hình: SafeAreaView nền colors.background; nội dung nằm trong View có paddingHorizontal s(21), maxWidth MAX_CONTENT_WIDTH và alignSelf 'center' (width 100%) để tablet không bị giãn.

1) HEADER (hàng ngang, cao s(46), justifyContent space-between, alignItems center, paddingTop vs(8)):
   - Trái: ThemedText variant title (chữ "Dịch & Đọc", 26 đậm).
   - Phải: IconCircleButton size 'small' (46), variant 'neutral', icon "sunny-outline" khi đang sáng hoặc "moon-outline" khi đang tối, accessibilityLabel "Đổi giao diện sáng tối". Tạm để onPress rỗng (nối ở Task 23).

2) HÀNG NGÔN NGỮ (cách header vs(14), cao vs(59), hàng ngang, alignItems center):
   - Thẻ trái "Dịch từ": rộng ~s(166) (flex 1), nền colors.surfaceMuted, viền 1px colors.border, bo góc s(22), padding ngang s(16). Hai dòng chữ xếp dọc: nhãn "Dịch từ" (typography.label 12, màu textSecondary) và giá trị "Tiếng Việt" (typography.value 17 đậm, textPrimary). KHÔNG bấm được (nguồn cố định), không có mũi tên chevron.
   - Giữa: icon Ionicons "arrow-forward" ms(20) màu textSecondary, chiếm ngang s(38) căn giữa.
   - Thẻ phải "Dịch sang": cùng kích thước thẻ trái (flex 1), nền colors.surface, viền 1px colors.border, bo s(22), padding ngang s(16); bên trái hai dòng: nhãn "Dịch sang" và giá trị là getTargetLabel(targetLanguage) (tạm hiện "English"); bên phải icon "chevron-down" ms(20) màu textSecondary. Pressable: tạm onPress rỗng (nối ở Task 24).

Giá trị hiển thị lấy từ strings. Có accessibilityLabel hợp lý (ví dụ "Dịch sang English, bấm để đổi ngôn ngữ").
````

**GIẢI THÍCH**
- **Làm gì:** dựng phần đầu màn chính: tiêu đề "Dịch & Đọc", nút mặt trời, ô "Dịch từ Tiếng Việt" (mờ, cố định) → ô "Dịch sang English ⌄".
- **Sửa gì:** `screens/HomeScreen.tsx`.
- **Kiểm tra:** ô trái xám nhạt, không có mũi tên xuống; ô phải trắng có ⌄; hai ô bằng nhau.

---

## TASK 18 — HomeScreen: ô nhập văn bản (có mic + camera)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand, React Navigation). HomeScreen.tsx đã có header + hàng ngôn ngữ. Đã có Card, IconCircleButton, ThemedText, theme, scale; translationStore có vietnameseText, setText, clearText. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): thêm Ô NHẬP VĂN BẢN vào HomeScreen.tsx, bên dưới hàng ngôn ngữ (cách vs(14)).

Ô nhập là một Card (nền surface, viền 1px border, bo s(24)), bên trong:
- TextInput multiline, nối với vietnameseText/setText của store. Placeholder "Nhập văn bản cần dịch" màu colors.placeholder. Chữ nhập: typography.bodyLarge (24, weight medium, lineHeight 34), màu textPrimary. textAlignVertical 'top'. maxLength 500 (không hiển thị bộ đếm). Padding trong card: ngang s(22), trên vs(20). Chiều cao tối thiểu của card: vs(248) khi chưa có chữ và vs(200) khi đã có chữ hoặc đang có kết quả; card tự cao thêm theo nội dung (tối đa vs(330), vượt thì TextInput cuộn).
- Nút xoá "×": chỉ hiện khi có chữ; đặt góc trên-phải của hàng chữ đầu (absolute top vs(20), right s(22)), icon Ionicons "close" ms(22) màu textSecondary, vùng chạm s(36), accessibilityLabel "Xoá văn bản"; bấm gọi clearText() và focus lại input. Chừa paddingRight cho TextInput để chữ không đè lên nút × khi có chữ (paddingRight s(40)).
- Hàng 2 nút tròn nằm góc DƯỚI-TRÁI của card (absolute: left s(22), bottom vs(13)): hai IconCircleButton size 'medium' (50), variant 'soft', cách nhau s(11): nút 1 icon "mic-outline" (accessibilityLabel "Nói để nhập văn bản"), nút 2 icon "camera-outline" ("Quét chữ bằng camera"). Chừa paddingBottom cho nội dung của card đủ vs(76) để chữ không đè lên nút. onPress: mic → navigation.navigate('VoiceListening'); camera → navigation.navigate('Camera').
- Khi người dùng bắt đầu gõ lúc phase là 'result'/'error' thì setText đã tự đưa phase về 'idle' (store lo).
Bao toàn bộ màn hình trong ScrollView keyboardShouldPersistTaps="handled" (nút Dịch sẽ cố định bên ngoài ở Task 20). Không làm thẻ ngữ cảnh/kết quả ở bước này.
````

**GIẢI THÍCH**
- **Làm gì:** ô nhập lớn đúng thiết kế: placeholder "Nhập văn bản cần dịch", nút × khi có chữ, hai nút tròn mic/camera ở góc dưới-trái.
- **Sửa gì:** `screens/HomeScreen.tsx`.
- **Kiểm tra:** chưa có chữ → ô cao hơn; gõ chữ → hiện ×; bấm mic/camera mở màn tạm tương ứng.

---

## TASK 19 — HomeScreen: link "Thêm ngữ cảnh" + thẻ ngữ cảnh

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). HomeScreen.tsx đã có header, hàng ngôn ngữ, ô nhập. Đã có Card, ToneChip, ThemedText, strings, theme, scale; translationStore có tones, toggleTone, contextNote, setContextNote, contextOpen, toggleContext, phase. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): thêm vào HomeScreen.tsx, bên dưới ô nhập (và bên dưới khối kết quả nếu có, sẽ làm sau):

A) LINK NGỮ CẢNH (khi contextOpen = false): hàng ngang, cách ô nhập vs(22), paddingLeft s(8), alignItems center, Pressable bấm gọi toggleContext():
   - icon Ionicons "add" ms(20) màu colors.primary;
   - chữ "Thêm ngữ cảnh" (bold ms(16), màu colors.primary) cách icon s(8);
   - rồi " (không bắt buộc)" (regular ms(16), màu colors.textSecondary).
   - Nếu đã có ngữ cảnh (tones.length > 0 hoặc contextNote.trim() khác rỗng): thay icon bằng "checkmark-circle" và nhãn thành "Ngữ cảnh đã thêm" kèm phần phụ màu textSecondary là danh sách tên giọng văn đã chọn nối ", " (nếu không có giọng văn thì "ghi chú").
   accessibilityRole="button".

B) THẺ NGỮ CẢNH (khi contextOpen = true; thay cho link, cách ô nhập vs(14)): một Card (padding s(22), bo s(24)):
   1. Hàng tiêu đề (bấm vào gọi toggleContext()): chữ "Ngữ cảnh" (bold ms(17), textPrimary) + " (không bắt buộc)" (regular ms(17), textSecondary); bên phải icon "chevron-up" ms(22) màu textSecondary.
   2. Cách vs(14): ô ghi chú: TextInput multiline, nền colors.inputBg, viền 1px colors.border, bo s(15), padding s(14), cao vs(62) (cuộn khi dài), chữ ms(17) màu textPrimary, placeholder "Ví dụ: gửi cho khách hàng, giữ nguyên từ “deadline”." màu placeholder, maxLength 200, nối contextNote/setContextNote. Hiện thanh cuộn dọc.
   3. Dưới ô ghi chú, căn phải: bộ đếm `${contextNote.length}/200` ms(14) màu textSecondary, cách vs(6).
   4. Cách vs(14): lưới 4 ToneChip xếp 2 hàng, wrap, khoảng cách ngang s(9) và dọc vs(9), thứ tự: Trang trọng, Thân mật (hàng 1); Học thuật, Kinh doanh (hàng 2). Chip chọn nhiều, trạng thái nối tones/toggleTone.
   Khi thẻ mở: tự cuộn ScrollView xuống để thấy hết thẻ.
C) Hiệu ứng mở/đóng: dùng LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut) (bật UIManager.setLayoutAnimationEnabledExperimental cho Android).

Chưa làm nút Dịch/kết quả.
````

**GIẢI THÍCH**
- **Làm gì:** dòng "+ Thêm ngữ cảnh (không bắt buộc)" mở ra thẻ có ô ghi chú 0/200 và 4 chip giọng văn chọn nhiều.
- **Sửa gì:** `screens/HomeScreen.tsx`.
- **Kiểm tra:** bấm link → thẻ mở; bấm tiêu đề thẻ → đóng; tick giọng văn → link đóng đổi thành "Ngữ cảnh đã thêm (Trang trọng)".

---

## TASK 20 — HomeScreen: nút "Dịch" dính đáy + xử lý bàn phím

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). HomeScreen.tsx đã có header, hàng ngôn ngữ, ô nhập, link/thẻ ngữ cảnh. Đã có PrimaryButton, strings, scale; translationStore có vietnameseText, phase, translate(). Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms().

Việc cần làm (CHỈ việc này):
1. Cấu trúc lại HomeScreen thành: KeyboardAvoidingView (behavior 'padding' trên iOS, 'height' hoặc undefined trên Android tuỳ cấu hình edge-to-edge; đảm bảo nút Dịch nổi lên trên bàn phím) > [ScrollView chứa nội dung (flex 1)] + [Vùng nút Dịch cố định phía dưới].
2. Vùng nút Dịch: paddingHorizontal s(21), paddingTop vs(10), paddingBottom vs(17) (+ safe area dưới), nền trong suốt (hoặc colors.background). Trong đó PrimaryButton label "Dịch", cao vs(59), full-width:
   - disabled khi vietnameseText.trim() rỗng (nền xám disabledBg, chữ disabledText) — đúng thiết kế khi chưa nhập gì;
   - enabled khi có chữ (nền colors.primary, chữ trắng đậm);
   - khi phase === 'translating': loading=true, label "Đang dịch…", không bấm được.
   - onPress: Keyboard.dismiss() rồi gọi translate() của store.
3. Chỉ HIỆN vùng nút Dịch khi phase là 'idle' hoặc 'translating'. Khi phase là 'result' hoặc 'error' thì ẩn hoàn toàn nút Dịch (không chừa khoảng trống). (Khi người dùng sửa chữ/ngôn ngữ/ngữ cảnh, store đưa phase về 'idle' nên nút Dịch hiện lại.)
4. Khi bàn phím mở, ScrollView vẫn cuộn được; keyboardShouldPersistTaps="handled"; keyboardDismissMode="on-drag".
Chưa làm khối kết quả/lỗi.
````

**GIẢI THÍCH**
- **Làm gì:** nút "Dịch" cố định dưới cùng (xám khi trống, xanh khi có chữ), nổi lên trên bàn phím; ẩn khi đã có kết quả hoặc lỗi — đúng như các ảnh thiết kế.
- **Sửa gì:** `screens/HomeScreen.tsx` (đổi cấu trúc bao ngoài).
- **Lưu ý:** việc "ẩn nút Dịch khi có kết quả" mình suy ra từ ảnh thiết kế (ảnh kết quả/lỗi không có nút Dịch).
- **Kiểm tra:** thử cả Android và iOS: bàn phím không che nút.

---

## TASK 21 — HomeScreen: khối kết quả + nút "Đọc to" và sao chép

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand, expo-av, expo-clipboard). HomeScreen.tsx đã có ô nhập, thẻ ngữ cảnh, nút Dịch. Đã có Card, PrimaryButton (variant 'pill'), IconCircleButton, ThemedText, theme, scale, strings, utils; services/api.ts có hàm gọi TTS (xem chữ ký synthesizeSpeech) và saveBase64Audio; translationStore có translatedText, targetLanguage, phase. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này):

1) GIAO DIỆN thẻ kết quả: khi phase === 'result', hiện một Card ngay bên dưới ô nhập (cách vs(14)), padding s(22), bo s(24):
   - Dòng nhãn ngôn ngữ đích: chữ getTargetLabel(targetLanguage) (ví dụ "English") ms(13) đậm màu colors.primary.
   - Cách vs(14): bản dịch translatedText: typography.result (25, weight semibold, lineHeight 38), màu textPrimary, có thể bôi chọn (selectable).
   - Cách vs(16): hàng ngang gồm: PrimaryButton variant 'pill' label "Đọc to" iconLeft "volume-medium-outline" (nền primary, chữ icon trắng, cao vs(50), bo tròn hoàn toàn); khoảng cách s(12); IconCircleButton size 'medium' variant 'soft' icon "copy-outline" accessibilityLabel "Sao chép bản dịch".
   - Bên dưới thẻ kết quả (cách vs(22)) vẫn hiện link/thẻ ngữ cảnh như đã làm.

2) LOGIC sao chép: bấm nút → expo-clipboard setStringAsync(translatedText); icon đổi thành "checkmark" trong 1500ms rồi trở lại (dọn timeout khi unmount), và gọi AccessibilityInfo.announceForAccessibility("Đã sao chép").

3) LOGIC đọc to:
   - Bấm "Đọc to": lần đầu gọi hàm TTS của services/api.ts với translatedText và targetLanguage (đúng chữ ký hiện có; giọng mặc định nữ), lưu file bằng saveBase64Audio rồi tạo Audio.Sound (expo-av) và phát. Cache uri theo (translatedText + targetLanguage); đổi bản dịch/ngôn ngữ thì gọi lại.
   - Khi đang tải: nút pill hiện ActivityIndicator và disabled. Khi đang phát: nút đổi nhãn "Dừng" icon "stop"; bấm để dừng (stopAsync + đặt vị trí 0). Phát xong tự về trạng thái ban đầu (setOnPlaybackStatusUpdate: didJustFinish).
   - Lỗi TTS: hiện dòng chữ nhỏ màu danger dưới hàng nút (ms(14)), không dùng Alert; bấm "Đọc to" lại để thử lại.
   - Dọn dẹp: unloadAsync Sound khi unmount hoặc khi translatedText đổi/phase rời 'result'. Cấu hình Audio.setAudioModeAsync cho phát qua loa (playsInSilentModeIOS: true).
Đặt logic đọc to vào hook mobile/src/hooks/useSpeech.ts (trả về { status: 'idle'|'loading'|'playing'|'error', play, stop }) để HomeScreen gọn.
````

**GIẢI THÍCH**
- **Làm gì:** thẻ kết quả: nhãn "English", bản dịch cỡ lớn, nút xanh "Đọc to" (phát giọng đọc từ backend) và nút tròn sao chép.
- **Sửa gì:** `screens/HomeScreen.tsx`; tạo mới `hooks/useSpeech.ts`.
- **Kiểm tra:** dịch xong thấy thẻ; bấm "Đọc to" có tiếng; "Sao chép" dán được; đổi chữ đầu vào thì thẻ kết quả biến mất.

---

## TASK 22 — HomeScreen: thẻ lỗi + nút "Thử lại"

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). HomeScreen.tsx đã có ô nhập, kết quả, nút Dịch. Đã có ErrorCard, strings; translationStore có phase, translateError, translate(). Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms().

Việc cần làm (CHỈ việc này): trong HomeScreen.tsx, khi phase === 'error', hiện ErrorCard ngay bên dưới ô nhập (cách vs(14)):
- title = strings.error.translateTitle ("Không dịch được")
- message = translateError (đã được store chuyển thành câu tiếng Việt thân thiện, ví dụ "Không kết nối được tới máy chủ dịch. Kiểm tra mạng rồi thử lại.")
- onRetry = gọi lại translate() của store (giữ nguyên chữ trong ô nhập).
Khi phase === 'error': KHÔNG hiện nút Dịch (đã xử lý ở bước 20) và KHÔNG hiện link ngữ cảnh. Khi bấm "Thử lại" thì phase chuyển 'translating' rồi 'result' hoặc lại 'error'.
Đảm bảo ErrorCard cuộn vào tầm nhìn (scrollTo) khi xuất hiện, và AccessibilityInfo thông báo nội dung lỗi.
````

**GIẢI THÍCH**
- **Làm gì:** hiện thẻ đỏ "Không dịch được" kèm "Thử lại" khi mất mạng/server lỗi.
- **Sửa gì:** `screens/HomeScreen.tsx`.
- **Kiểm tra:** tắt backend rồi bấm Dịch → thấy thẻ lỗi đúng chữ; bật backend, bấm "Thử lại" → ra kết quả.

---

## TASK 23 — HomeScreen: nút mặt trời đổi sáng/tối + tự dịch + mặc định

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). HomeScreen.tsx đã đầy đủ giao diện. Đã có ThemeProvider (mode, toggleMode), settingsStore, translationStore (pendingAutoTranslate, consumeAutoTranslate, applyDefaultsFromSettings, translate). Không sửa backend, không sửa src/config/api.ts.

Việc cần làm (CHỈ việc này), trong HomeScreen.tsx:
1. Nút mặt trời ở header: onPress gọi toggleMode() của ThemeProvider; icon "sunny-outline" khi mode sáng, "moon-outline" khi mode tối.
2. Khi màn Home mount lần đầu (và sau khi settingsStore đã hydrate xong): gọi applyDefaultsFromSettings() một lần để đặt ngôn ngữ đích mặc định.
3. Dùng useFocusEffect: khi Home được focus lại và store.pendingAutoTranslate === true (cờ này được bật sau khi nhận chữ từ Giọng nói hoặc Camera) thì: consumeAutoTranslate() rồi gọi translate() ngay (nếu vietnameseText không rỗng). Đóng thẻ bàn phím (Keyboard.dismiss).
4. Khi targetLanguage thay đổi từ màn TargetLanguage và đang có kết quả cũ, store đã tự reset về 'idle' — đảm bảo màn Home hiển thị nút Dịch trở lại.
Không thêm giao diện mới.
````

**GIẢI THÍCH**
- **Làm gì:** nút mặt trời đổi sáng/tối thật; mở app dùng ngôn ngữ mặc định; sau khi nói/chụp xong quay lại màn chính thì **tự dịch**.
- **Sửa gì:** `screens/HomeScreen.tsx`.
- **Kiểm tra:** đổi sáng/tối được và nhớ khi mở lại app; (tự dịch sẽ kiểm tra đầy đủ sau khi làm Task 27 và 30).

---

# F. MÀN NGÔN NGỮ

## TASK 24 — TargetLanguageScreen ("Dịch sang") — ⚠ link "Đổi ngôn ngữ mặc định" ở cuối màn bị bỏ ở Task 37

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand, React Navigation). Đã có ScreenHeader, ThemedText, theme, scale, strings, languages (TARGET_LANGUAGES), translationStore (targetLanguage, setTargetLang). Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): viết mobile/src/screens/TargetLanguageScreen.tsx (ghi đè màn tạm) và nối bấm "Dịch sang" ở HomeScreen để mở màn này (navigation.navigate('TargetLanguage')).

Giao diện: SafeAreaView nền colors.background, paddingHorizontal s(21), maxWidth MAX_CONTENT_WIDTH căn giữa.
- Đầu trang: ScreenHeader với title "Dịch sang" (nút back tròn 46 + tiêu đề 28 đậm; back gọi goBack()). paddingTop vs(8).
- Cách vs(24): nhãn section "Ngôn ngữ có sẵn" (bold ms(14), màu textSecondary, paddingLeft s(19)).
- Cách vs(10): danh sách các hàng từ TARGET_LANGUAGES (English, 中文 (Mandarin), 日本語 (Japanese), 한국어 (Korean), Français (French), Deutsch (German), Español (Spanish), Português (Portuguese), …; dùng label đầy đủ). Vì danh sách dài, đặt trong FlatList (hoặc ScrollView) cuộn được, flex 1, paddingBottom vs(24) + safe area; phần link "Đổi ngôn ngữ mặc định" nằm CUỐI danh sách (ListFooterComponent) chứ không cố định. Mỗi hàng: cao vs(59), bo tròn hoàn toàn (pill), hàng ngang alignItems center, khoảng cách giữa các hàng vs(3).
   - Hàng đang chọn (targetLanguage): nền colors.primarySoftStrong, bên trái icon "checkmark" ms(24) màu colors.primaryDark ở vị trí cách mép trái hàng s(18) (căn giữa trong ô rộng s(36)), chữ typography.itemTitle (19, bold) màu textPrimary.
   - Hàng chưa chọn: nền trong suốt, KHÔNG có icon nhưng chữ vẫn thụt vào cùng vị trí với hàng đang chọn (chừa ô icon rộng s(36) + khoảng cách s(12)), chữ ms(19) weight medium màu textPrimary.
   - Bấm một hàng: gọi setTargetLang(code) của store rồi goBack().
- Cuối màn hình (cách vs(28) phía dưới danh sách): một Pressable căn giữa chữ "Đổi ngôn ngữ mặc định" (bold ms(15), màu colors.primary) → navigation.navigate('DefaultLanguage'). (Đây là điểm vào cho màn Ngôn ngữ mặc định; thiết kế gốc chưa nêu rõ chỗ vào nên đặt tại đây.)
accessibilityRole="radio" cho các hàng, accessibilityState selected.
````

**GIẢI THÍCH**
- **Làm gì:** màn chọn ngôn ngữ đích: hàng đang chọn có dấu ✓ và nền xanh nhạt hình viên thuốc, các hàng còn lại chữ thường; danh sách dài nên cuộn được.
- **Sửa gì:** `screens/TargetLanguageScreen.tsx`; nối `onPress` ở `HomeScreen.tsx`.
- **Lưu ý:** bản thiết kế có màn "Ngôn ngữ mặc định" nhưng **không chỉ ra cách vào**, nên mình đặt một link nhỏ "Đổi ngôn ngữ mặc định" ở cuối màn "Dịch sang". Bạn có thể đổi vị trí sau.
- **Kiểm tra:** chọn 한국어 → quay về, ô "Dịch sang" hiện "한국어".

---

## TASK 25 — DefaultLanguageScreen ("Ngôn ngữ mặc định") — ⚠ ĐÃ THAY BẰNG TASK 37–38 (đây thực ra là màn "Dịch từ")

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand, React Navigation). Đã có ScreenHeader, ThemedText, theme, scale, strings, languages (TARGET_LANGUAGES), settingsStore (defaultTargetLang, setDefaultTargetLang). Màn TargetLanguageScreen đã làm xong (xem file để dùng lại kiểu hàng ngôn ngữ). Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): viết mobile/src/screens/DefaultLanguageScreen.tsx (ghi đè màn tạm).
1. Tách component hàng ngôn ngữ dùng chung thành mobile/src/components/LanguageRow.tsx (props: label, selected, onPress) từ TargetLanguageScreen rồi dùng lại ở cả hai màn (không đổi giao diện TargetLanguageScreen).
2. Giao diện DefaultLanguageScreen: SafeAreaView nền background, paddingHorizontal s(21):
   - ScreenHeader title "Ngôn ngữ mặc định" (28 đậm).
   - Cách vs(18): đoạn mô tả "Ngôn ngữ này được chọn sẵn mỗi lần mở app. Bạn vẫn đổi được ở màn Dịch." typography.body (ms(15), lineHeight ms(22), màu textSecondary), paddingLeft s(19).
   - Cách vs(22): nhãn section "Dịch sang" (bold ms(14), textSecondary, paddingLeft s(19)).
   - Cách vs(10): danh sách LanguageRow cho TOÀN BỘ TARGET_LANGUAGES (label đầy đủ) như TargetLanguageScreen, đặt trong FlatList cuộn được; hàng đang chọn theo defaultTargetLang của settingsStore.
   - Bấm một hàng: setDefaultTargetLang(code) (lưu bền). Giữ nguyên màn (không goBack ngay); có thể goBack() sau 250ms để người dùng thấy dấu ✓ chuyển.
3. Khi đổi mặc định, KHÔNG đổi targetLanguage đang dùng ở màn Dịch hiện tại (chỉ ảnh hưởng lần mở app sau).
````

**GIẢI THÍCH**
- **Làm gì:** màn chọn ngôn ngữ đích mặc định (mô tả "…được chọn sẵn mỗi lần mở app…"), lưu bền.
- **Sửa gì:** `screens/DefaultLanguageScreen.tsx`; tạo mới `components/LanguageRow.tsx`; refactor nhẹ `TargetLanguageScreen.tsx`.
- **Kiểm tra:** chọn 中文 mặc định → tắt hẳn app mở lại → ô "Dịch sang" hiện "中文".

---

# G. MÀN GIỌNG NÓI ("Đang nghe…")

## TASK 26 — VoiceListeningScreen: giao diện

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand, React Navigation). Đã có ThemedText, Card, IconCircleButton, Waveform, theme, scale, strings. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): viết GIAO DIỆN mobile/src/screens/VoiceListeningScreen.tsx (ghi đè màn tạm). Dùng state cục bộ: confirmedText (string, phần chữ đã chốt), interimText (string, phần chữ đang nhận dạng), isListening (bool, mặc định true), phase 'listening' | 'recognizing'. KHÔNG ghi âm thật, KHÔNG gọi API ở bước này (chỉ dựng giao diện; thêm 2 nút thử __DEV__ để nhập chữ giả kiểm tra hiển thị).

Bố cục (SafeAreaView nền colors.background, paddingHorizontal s(21), maxWidth MAX_CONTENT_WIDTH căn giữa; toàn màn hình, KHÔNG có thanh tab):
1. Hàng đầu (cao s(46), space-between, paddingTop vs(8)): trái tiêu đề "Đang nghe…" (typography cardTitle nhưng cỡ ms(24) bold); khi phase là 'recognizing' đổi thành "Đang nhận dạng…". Phải: IconCircleButton size small variant neutral icon "close" accessibilityLabel "Đóng" (onPress tạm goBack).
2. Cách vs(14): dòng gợi ý ms(16) màu textSecondary: "Hãy nói tiếng Việt. Chữ hiện ra khi bạn nói." (đổi thành "Hãy nói tiếng Việt. Chữ sẽ hiện sau khi bạn dừng." khi thiết bị không hỗ trợ nghe trực tiếp — nhận prop/route state liveSupported, mặc định true).
3. Cách vs(18): Card lớn chứa chữ nhận dạng: flex 1 (chiếm hết chiều cao còn lại giữa phần trên và nhóm điều khiển dưới; trên máy chuẩn cao khoảng vs(515)), nền surface, viền 1px border, bo s(24), padding s(22). Bên trong ScrollView cuộn tự động xuống cuối khi có chữ mới. Chữ dùng typography.bodyLarge (24, medium, lineHeight 34): đoạn confirmedText màu textPrimary; ngay sau đó đoạn interimText màu colors.interimText (xám hơn) và kết thúc bằng dấu "…" khi interimText không rỗng. Khi chưa có chữ gì: không hiện placeholder.
4. NHÓM ĐIỀU KHIỂN dưới cùng (căn giữa theo chiều ngang, cách đáy vs(16) + safe area, cách Card lớn vs(14)):
   a) <Waveform active={isListening} /> (cao ~vs(56)).
   b) Cách vs(14): nút dừng: vòng ngoài (halo) tròn đường kính s(114) màu colors.primarySoft; bên trong nút tròn đường kính s(93) màu colors.primary; ở giữa hình vuông bo góc trắng s(30)x s(30), borderRadius s(6) (biểu tượng "dừng"). Pressable; accessibilityLabel "Dừng và dịch". Khi phase 'recognizing' thay hình vuông bằng ActivityIndicator trắng và không bấm được.
   c) Cách vs(10): chữ chú thích căn giữa ms(14) màu textSecondary: "Chạm để dừng và dịch".
5. Nút × và nút dừng chỉ là giao diện ở bước này (onPress tạm rỗng ngoại trừ goBack cho ×).
````

**GIẢI THÍCH**
- **Làm gì:** màn "Đang nghe…": tiêu đề + nút ×, dòng gợi ý, thẻ trắng lớn hiện chữ (phần đã chốt đậm, phần đang nghe xám có "…"), sóng âm xanh, nút dừng tròn xanh có vòng sáng, chú thích "Chạm để dừng và dịch".
- **Sửa gì:** `screens/VoiceListeningScreen.tsx`.
- **Kiểm tra:** dùng nút thử nhập chữ giả: thấy chữ đậm + chữ xám "thứ Sáu nhé…".

---

## TASK 27 — VoiceListeningScreen: nối nghe thời gian thực + dịch

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand, expo-av). Trong dự án đã có: services/stream.ts (StreamClient: connect, finish, các callback onAsrInterim, onAsrFinal, onTransDelta, onTransFinal, onTtsAudio, onError; xem file để biết đúng tên), services/liveAudio.ts (isLiveAudioSupported, bắt đầu/dừng thu PCM 16kHz), services/api.ts (apiTranscribeAudio dùng cho ghi âm file .m4a), components/VoiceRecorder.tsx (cách ghi âm bằng expo-av), translationStore (requestAutoTranslate, startStreaming/stopStreaming hiện có). VoiceListeningScreen.tsx đã có giao diện (state cục bộ). Backend /ws/stream gửi các sự kiện asr_interim, asr_final, trans_*, tts_audio. Không sửa backend, không sửa src/config/api.ts, không xoá logic hiện có.

Việc cần làm (CHỈ việc này): nối logic thật cho VoiceListeningScreen.tsx, GIỮ NGUYÊN giao diện:

A) Chế độ NGHE TRỰC TIẾP (khi isLiveAudioSupported() là true — cần development build):
   1. Khi màn mount: xin quyền micro; nếu bị từ chối thì dừng và hiện thông báo lỗi trong thẻ chữ (màu danger, "Cần quyền micro để nhận dạng giọng nói.") kèm nút × vẫn dùng được.
   2. Mở StreamClient với nguồn 'vi' và ngôn ngữ đích hiện tại (targetLanguage của store); bắt đầu thu PCM từ liveAudio và gửi từng gói qua stream (xem stream.ts/liveAudio.ts).
   3. Sự kiện asr_interim: đặt interimText = text (thay thế, không cộng dồn). Sự kiện asr_final: nối text vào confirmedText (thêm khoảng trắng giữa các câu), xoá interimText. BỎ QUA hoàn toàn các sự kiện trans_start/trans_delta/trans_final/tts_audio (màn này chỉ cần chữ nhận dạng).
   4. Dùng sessionId (như translationStore.startStreaming) để bỏ qua sự kiện của phiên cũ.
B) Chế độ GHI RỒI NHẬN DẠNG (khi isLiveAudioSupported() là false, ví dụ Expo Go):
   1. Hint hiện "Hãy nói tiếng Việt. Chữ sẽ hiện sau khi bạn dừng." (liveSupported=false).
   2. Ghi âm bằng expo-av (tái sử dụng cách ghi trong VoiceRecorder.tsx; có thể tách hook hooks/useVoiceRecording.ts với { start, stop, uri }). Khi bấm dừng: phase='recognizing' (tiêu đề "Đang nhận dạng…"), gọi apiTranscribeAudio(uri), kết quả đặt vào confirmedText.
C) Nút DỪNG ("Chạm để dừng và dịch"): dừng thu; chờ kết quả cuối (live: gọi finish() và đợi asr_final cuối tối đa 3 giây; ghi âm file: chờ ASR xong); sau đó text = (confirmedText + ' ' + interimText).trim(). Nếu text rỗng: hiện dòng thông báo "Chưa nghe thấy giọng nói. Hãy thử lại." trong thẻ và quay về trạng thái nghe lại (không đóng màn). Nếu có text: gọi requestAutoTranslate(text) của store rồi navigation.goBack() (Home sẽ tự dịch ở useFocusEffect).
D) Nút ×: huỷ toàn bộ (dừng thu, đóng stream, bỏ chữ) rồi goBack() mà KHÔNG đổi vietnameseText.
E) Dọn dẹp: khi unmount hoặc app xuống nền (AppState không còn 'active'): dừng thu âm, đóng StreamClient, giải phóng recorder. Không để micro mở ngầm.
F) Waveform: nếu liveAudio cung cấp mức âm lượng thì truyền vào prop level; nếu không thì để animation mặc định.
G) Bỏ 2 nút thử __DEV__ ở bước trước.
````

**GIẢI THÍCH**
- **Làm gì:** nghe thật: chữ hiện theo thời gian thực (đậm = chốt, xám = đang nghe); bấm dừng thì đóng màn, chữ chuyển sang ô nhập và **tự dịch**.
- **Sửa gì:** `screens/VoiceListeningScreen.tsx`; có thể tạo `hooks/useVoiceRecording.ts`.
- **Lưu ý quan trọng:** hiệu ứng "chữ hiện ra khi bạn nói" cần **development build** (module native `react-native-live-audio-stream`, theo `giai_thich.md` mục 6.6). Trong **Expo Go** màn tự chuyển sang chế độ "ghi xong mới nhận dạng" (đã dặn DeepSeek làm fallback), chữ chỉ hiện sau khi dừng.
- **Kiểm tra:** nói tiếng Việt → bấm dừng → quay về màn chính, chữ đã nằm trong ô nhập và đang dịch. Cần backend chạy.

---

# H. MÀN CAMERA

## TASK 28 — CameraScreen: giao diện + màn xin quyền

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, React Navigation). Đã cài expo-camera. Đã có utils/scale.ts, theme (cameraColors, useTheme), IconCircleButton (variant cameraDark, cameraClose, neutral), CornerFrame, PrimaryButton, OutlineButton, ThemedText, strings. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms().

Việc cần làm (CHỈ việc này): viết GIAO DIỆN mobile/src/screens/CameraScreen.tsx (ghi đè màn tạm). Màn có state cục bộ camState: 'ready' | 'processing' | 'error' | 'noPermission' và hasPermission (tạm giả lập; xin quyền thật ở bước 29). Dùng CameraView của expo-camera làm nền xem trước khi có quyền; khi chưa nối được, dùng View nền cameraColors.background làm giả lập. Thêm 4 nút thử __DEV__ chuyển camState để kiểm tra giao diện. StatusBar style "light" khi ở các trạng thái camera, "theme" khi noPermission.

A) CÁC TRẠNG THÁI CAMERA (ready / processing / error): toàn màn hình, nền camera (cameraColors.background #1E2B38 hoặc CameraView), có:
   1. Nút đóng: IconCircleButton size small (46), variant 'cameraClose', icon "close", góc trên-trái (left s(21), top = safe area trên + vs(12)), accessibilityLabel "Đóng" (goBack).
   2. Viên thuốc gợi ý ở giữa phía trên, cùng hàng với nút đóng: nền cameraColors.pill, bo tròn hoàn toàn, cao vs(37), padding ngang s(26), chữ "Đưa chữ vào khung" trắng bold ms(16), căn giữa màn hình theo chiều ngang.
   3. <CornerFrame> phủ màn hình: top = 93, bottom tuỳ trạng thái (ready: đáy khung cách đáy màn 165dp; processing: 130dp; error: 165dp); màu: ready = trắng (frameWhite), processing = vàng (frameYellow), error = san hô (frameRed).
   4. THANH DƯỚI cố định sát đáy, nền cameraColors.bottomBar, bo không, có paddingBottom theo safe area:
      - ready: cao vs(140). Hàng 3 phần căn giữa theo chiều dọc: trái IconCircleButton size large (54) variant 'cameraDark' icon "image-outline" (nhãn "Chọn ảnh từ thư viện"); giữa NÚT CHỤP: vòng ngoài trắng đường kính s(80) viền trắng dày s(5), bên trong hình tròn s(70) màu colors.primary xanh (#3347D6) (accessibilityLabel "Chụp ảnh"); phải IconCircleButton size large variant 'cameraDark' icon "flashlight-outline" (nhãn "Bật tắt đèn pin"). Ba phần cách đều (space-around, padding ngang s(30)).
      - processing: cao vs(104). Một hàng ngang căn trái padding s(30): vòng quay ActivityIndicator (hoặc vòng tròn viền xám có cung quay) kích thước s(28) màu trắng/xám nhạt, khoảng cách s(14), chữ "Đang nhận dạng chữ…" trắng bold ms(19), rồi cách s(10) chữ nhỏ "(xong → dịch)" ms(14) màu cameraColors.hintText (#A9B4FF).
      - error: panel cao tự nhiên (~vs(161)), nền cameraColors.bottomBar, padding s(21): hàng đầu icon "alert-circle-outline" ms(24) màu cameraColors.frameRed + cột chữ: "Không nhận dạng được chữ nào" trắng bold ms(17), bên dưới "Thử ở nơi đủ sáng, giữ máy thẳng và gần chữ hơn." ms(14) màu cameraColors.descText; cách vs(14) dưới là OutlineButton tone 'dark' (nền trắng, chữ đậm tối) "Chụp lại" iconLeft "refresh", cao vs(50), bo s(14), full-width.
   5. (Tuỳ chọn, bỏ qua nếu phức tạp) bản thiết kế có vẽ 3 thanh chữ giả làm minh hoạ — KHÔNG cần làm.

B) TRẠNG THÁI noPermission (màn xin quyền, KHÔNG dùng nền camera mà dùng nền theme background, SafeAreaView):
   1. Nút đóng góc trên-phải: IconCircleButton size small variant 'neutral' icon "close" (goBack).
   2. Giữa màn hình (cao khoảng 38% từ trên), căn giữa: vòng tròn s(76) nền colors.primarySoft chứa icon "camera-outline" ms(32) màu colors.primary; cách vs(18) tiêu đề "Cần quyền dùng camera" ms(23) bold màu textPrimary căn giữa; cách vs(12) đoạn mô tả "Để quét chữ trong ảnh, hãy cho phép Dịch & Đọc dùng camera. Ảnh chỉ dùng để nhận dạng, không được lưu." ms(15), lineHeight ms(22), màu textSecondary, căn giữa, rộng tối đa s(330).
   3. Dưới cùng (paddingHorizontal s(21), cách đáy vs(30) + safe area): PrimaryButton "Mở cài đặt quyền" (cao vs(59), bo s(22), nền primary) rồi cách vs(14) là OutlineButton size 'lg' (cao vs(59), bo s(22)) "Nhập văn bản thay thế".
Các nút trong bước này chỉ là giao diện (onPress tạm rỗng, trừ nút đóng).
````

**GIẢI THÍCH**
- **Làm gì:** dựng toàn bộ giao diện camera theo 4 trạng thái: sẵn sàng (khung trắng + thanh dưới có Thư viện / nút chụp xanh / Đèn pin), đang nhận dạng (khung vàng + "Đang nhận dạng chữ… (xong → dịch)"), lỗi (khung đỏ + "Không nhận dạng được chữ nào" + nút trắng "Chụp lại"), và màn xin quyền "Cần quyền dùng camera".
- **Sửa gì:** `screens/CameraScreen.tsx`.
- **Kiểm tra:** dùng 4 nút thử chuyển trạng thái, so từng trạng thái với mô tả (màu khung, chữ, nút).

---

## TASK 29 — CameraScreen: quyền, chụp, thư viện, đèn pin

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). CameraScreen.tsx đã có giao diện 4 trạng thái (state cục bộ + 4 nút thử __DEV__). Đã cài expo-camera và expo-image-picker. Không sửa backend, không sửa src/config/api.ts.

Việc cần làm (CHỈ việc này) trong CameraScreen.tsx (giữ nguyên giao diện):
1. Quyền camera: dùng useCameraPermissions() của expo-camera. Khi mount: nếu chưa có quyền và canAskAgain thì gọi requestPermission() tự động. Nếu không có quyền (denied) thì camState = 'noPermission'. Khi người dùng quay lại app từ Cài đặt (AppState chuyển 'active') thì kiểm tra lại quyền và chuyển sang 'ready' nếu đã được cấp.
2. Màn noPermission: "Mở cài đặt quyền" → Linking.openSettings(); "Nhập văn bản thay thế" và nút × → navigation.goBack() (về màn chính, nơi ô nhập tự focus: dùng một tham số/ cờ để HomeScreen focus input — nếu phức tạp, chỉ cần goBack()).
3. Khi có quyền: render <CameraView> của expo-camera phủ toàn màn hình (facing 'back', ref lưu lại) làm nền, các lớp giao diện (nút đóng, viên thuốc, khung 4 góc, thanh dưới) đè lên.
4. Đèn pin: state torchOn; nút "đèn pin" đổi torchOn, truyền vào CameraView prop enableTorch; icon đổi "flashlight" (đặc) khi bật và "flashlight-outline" khi tắt. Khi rời màn hình thì tắt đèn.
5. Nút chụp: gọi cameraRef.current.takePictureAsync({ quality: 0.8, skipProcessing: false }) lấy uri; bảo vệ chống bấm nhiều lần (đang chụp thì bỏ qua). Sau khi có uri đặt capturedUri và camState = 'processing' (phần gọi OCR làm ở bước 30; ở bước này chỉ cần log uri và đưa về 'ready' sau 1 giây để thử).
6. Nút thư viện: ImagePicker.launchImageLibraryAsync({ mediaTypes: images, quality: 0.8 }); nếu chọn ảnh thì dùng uri như bước 5; nếu huỷ thì không làm gì.
7. Xoá 4 nút thử __DEV__ cho các nút đã có logic thật (giữ lại nút thử cho 'error'/'processing' nếu cần ở bước sau).
8. Dọn dẹp: tắt đèn pin, không giữ tham chiếu camera khi unmount.
````

**GIẢI THÍCH**
- **Làm gì:** camera thật trong Expo Go: xin quyền, xem trước, chụp, chọn ảnh thư viện, bật/tắt đèn pin; xử lý đúng khi người dùng từ chối quyền.
- **Sửa gì:** `screens/CameraScreen.tsx`.
- **Kiểm tra:** từ chối quyền → thấy màn "Cần quyền dùng camera"; cấp quyền → thấy hình camera; đèn pin bật/tắt; chụp/ chọn ảnh chạy không crash.

---

## TASK 30 — CameraScreen: nhận dạng chữ (OCR), thành công và lỗi

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). CameraScreen.tsx đã có camera thật, chụp, thư viện, đèn pin; có capturedUri và camState. Trong dự án: services/api.ts có hàm gọi POST /api/ocr (xem tên và các trường trả về: extracted_text, translated_text, ngôn ngữ phát hiện), translationStore có processImage(uri) (gọi OCR và có thể tự dịch), requestAutoTranslate. Backend /api/ocr trả cả extracted_text lẫn translated_text. Không sửa backend, không sửa src/config/api.ts, không xoá logic hiện có.

Việc cần làm (CHỈ việc này):
1. Thêm vào translationStore một hàm runOcrOnly(uri: string): Promise<string> — gọi API OCR và CHỈ trả về extracted_text (đã trim); KHÔNG ghi vào vietnameseText/translatedText, KHÔNG dịch. Giữ nguyên processImage cũ. Nếu API cần target_language thì truyền targetLanguage hiện tại; bỏ qua translated_text trong phản hồi.
2. Trong CameraScreen: khi có uri (từ chụp hoặc thư viện):
   - camState = 'processing': hiện ảnh vừa chụp phủ làm nền (Image resizeMode 'cover', dim 40% bằng lớp phủ đen mờ) thay cho xem trước camera; khung 4 góc vàng; thanh dưới "Đang nhận dạng chữ… (xong → dịch)"; tắt đèn pin; nút đóng vẫn hoạt động (huỷ: bỏ kết quả của phiên này bằng sessionId, goBack).
   - Gọi runOcrOnly(uri):
     • Có chữ (độ dài sau trim ≥ 1): gọi requestAutoTranslate(text) của store rồi navigation.goBack(). Màn chính sẽ tự dịch.
     • Chữ rỗng, hoặc ném lỗi: camState = 'error' (khung đỏ san hô, panel lỗi "Không nhận dạng được chữ nào" / "Thử ở nơi đủ sáng, giữ máy thẳng và gần chữ hơn." + nút "Chụp lại"). Nếu lỗi là do mạng thì đổi dòng mô tả thành strings.error.network.
   - Nút "Chụp lại": xoá capturedUri, camState = 'ready' (quay lại xem trước camera, khung trắng).
3. Bỏ hoàn toàn các nút thử __DEV__ còn lại.
4. Dọn dẹp: huỷ kết quả OCR về muộn nếu màn đã đóng (kiểm tra mounted/sessionId trước khi set state hoặc điều hướng).
````

**GIẢI THÍCH**
- **Làm gì:** chụp/chọn ảnh → khung vàng + "Đang nhận dạng chữ… (xong → dịch)" → có chữ thì đóng camera, chữ nằm trong ô nhập và tự dịch; không có chữ thì khung đỏ + "Chụp lại".
- **Sửa gì:** `screens/CameraScreen.tsx`; thêm `runOcrOnly` vào `store/translationStore.ts`.
- **Kiểm tra:** chụp trang có chữ → về màn chính có chữ + kết quả dịch; chụp tường trắng → khung đỏ và nút "Chụp lại".

---

# I. HOÀN THIỆN

## TASK 31 — Dọn code giao diện cũ

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Giao diện V2 (stack không tab) đã chạy. Không sửa backend, không sửa src/config/api.ts, KHÔNG xoá logic API/stream/liveAudio/voice cloning.

Việc cần làm (CHỈ việc này):
1. Tìm mọi nơi còn import các file giao diện cũ: screens/TranslationScreen.tsx, TextScreen.tsx, VoiceScreen.tsx, ImageScreen.tsx, SettingsScreen.tsx, LanguagePickerScreen.tsx, ContextScreen.tsx, ResultScreen.tsx, VoicePickerScreen.tsx, và components InputModeSelector, LanguagePicker (cũ), ContextInput, TranslationResult, ImagePickerButton, VoiceRecorder, VoiceCloningPanel, LanguageSelector... Đảm bảo luồng chạy hiện tại không còn import chúng.
2. Với file không còn dùng: không xoá; thêm comment đầu file "// Deprecated: thay bởi giao diện V2 (HomeScreen/TargetLanguageScreen/...). Giữ để tham khảo." Riêng VoiceRecorder.tsx và VoiceCloningPanel.tsx giữ nguyên (logic còn giá trị).
3. Nếu có @react-navigation/bottom-tabs trong package.json mà không còn dùng: báo cho tôi, KHÔNG tự gỡ.
4. Tìm chuỗi tiếng Anh còn sót trong giao diện V2 (ví dụ "Translate", "Tap to record", "Input language", "Pick Image") và thay bằng strings tương ứng (trừ tên ngôn ngữ 'English', '한국어 (Korean)', '中文 (Mandarin)' theo thiết kế).
5. Tìm số cứng (kích thước, màu hex) trong các màn hình/component V2 chưa đi qua s()/vs()/ms()/theme và sửa (trừ độ dày viền 1 và các màu của cameraColors).
6. Báo cáo ngắn các file đã đổi.
````

**GIẢI THÍCH**
- **Làm gì:** gỡ giao diện cũ khỏi luồng chạy, soát chữ Anh và số cứng còn sót.
- **Sửa gì:** thêm comment vào file cũ; sửa rải rác file V2.
- **Kiểm tra:** chạy app, không còn dấu vết tab dưới/panel Voice Cloning.

---

## TASK 32 — Rà soát tỉ lệ nhiều kích thước + checklist cuối

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Giao diện V2 đã làm xong. Không sửa backend, không sửa src/config/api.ts. Kích thước chuẩn thiết kế: 411x890 dp.

Việc cần làm (CHỈ việc này): rà soát và sửa lỗi, KHÔNG thêm tính năng mới.
1. Chạy "npm run typecheck" và sửa mọi lỗi TypeScript.
2. KIỂM TRA TỈ LỆ: với mỗi màn (Home ở các trạng thái idle/có chữ/ngữ cảnh mở/kết quả/lỗi; TargetLanguage; DefaultLanguage; VoiceListening; Camera 4 trạng thái) hãy tự đánh giá bằng cách đọc code rằng bố cục không vỡ ở các kích thước: 360x640 (máy nhỏ), 393x851, 411x890 (chuẩn), 428x926, và tablet 768x1024. Cụ thể:
   - không có chiều cao/độ rộng cứng không qua s()/vs()/ms();
   - nội dung Home cuộn được khi màn thấp (360x640): nút Dịch vẫn nằm trên bàn phím và không che ô nhập;
   - Card lớn ở VoiceListening dùng flex nên không tràn trên máy thấp;
   - CornerFrame/thanh dưới camera dùng safe area (inset trên/dưới) và không chồng lên nhau trên máy thấp (nếu chồng thì rút gọn bottom của khung);
   - tablet: nội dung được căn giữa với maxWidth MAX_CONTENT_WIDTH, không bị giãn;
   - chữ hệ thống phóng to 1.3 lần (fontScale) không làm vỡ nút/hàng (maxFontSizeMultiplier 1.2 đã đặt, các hàng dùng minHeight thay vì height cố định cho chỗ chứa chữ).
   Sửa những chỗ lệch tìm thấy. Nếu có thể, thêm một script đơn giản hoặc ghi chú hướng dẫn tôi kiểm tra tay trên các emulator Pixel 4a (360x… ), Pixel 6 (411x…), Pixel Tablet.
3. Đối chiếu checklist giao diện:
   - Màn chính: tiêu đề "Dịch & Đọc" + nút mặt trời; ô "Dịch từ Tiếng Việt" mờ không bấm được → "Dịch sang English ⌄" bấm được; ô nhập placeholder "Nhập văn bản cần dịch", nút × khi có chữ, nút mic + camera tròn góc dưới-trái; link "+ Thêm ngữ cảnh (không bắt buộc)"; nút "Dịch" xám khi trống/xanh khi có chữ; có kết quả thì ẩn nút Dịch và hiện thẻ "English" + bản dịch + "Đọc to" + sao chép; lỗi thì thẻ đỏ "Không dịch được" + "Thử lại".
   - Thẻ ngữ cảnh: tiêu đề "Ngữ cảnh (không bắt buộc)" + ⌃, ô ghi chú, bộ đếm x/200, 4 chip có checkbox (chọn nhiều).
   - Dịch sang: hàng đang chọn nền xanh nhạt + ✓; danh sách đủ các ngôn ngữ (English, 中文, 日本語, 한국어, Français, Deutsch, Español, Português…) cuộn được, đúng chữ.
   - Ngôn ngữ mặc định: có đoạn mô tả đúng chữ, lưu bền.
   - Đang nghe…: nút ×, gợi ý, thẻ chữ lớn (đậm + xám), sóng âm, nút dừng có vòng sáng, "Chạm để dừng và dịch".
   - Camera: 4 trạng thái đúng màu khung (trắng/vàng/đỏ) và đúng chữ; màn "Cần quyền dùng camera" có 2 nút.
   - Đổi sáng/tối hoạt động và được nhớ.
4. Cuối cùng báo cáo ngắn: những gì khớp, những gì còn lệch/chưa làm và lý do.
````

**GIẢI THÍCH**
- **Làm gì:** bước kiểm tra cuối: lỗi kiểu, tỉ lệ trên nhiều kích thước máy (nhỏ, chuẩn, to, tablet, chữ hệ thống phóng to) và đối chiếu từng màn với đặc tả.
- **Sửa gì:** sửa nhỏ rải rác tuỳ lỗi tìm thấy.
- **Kiểm tra tay đề xuất:** chạy emulator Pixel 4a/Pixel 6/Pixel Tablet, hoặc thay đổi "Kích thước hiển thị"/"Cỡ chữ" trong Cài đặt Android để thử.

---

## TASK 33 (TUỲ CHỌN) — Thêm preset "Học thuật" và "Kinh doanh" ở backend

> Chỉ làm khi bạn muốn giọng văn này tác động mạnh hơn. Đây là task DUY NHẤT sửa backend.

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App. Task này được phép sửa backend ở đúng một file: backend/app/models/translation_adapter.py. Không sửa file khác của backend, không sửa mobile.

Việc cần làm (CHỈ việc này): trong dict CONTEXT_PRESETS thêm 2 preset theo cùng phong cách các preset hiện có (mô tả bằng tiếng Việt, ngắn gọn):
- "Academic": văn phong học thuật, chính xác, dùng thuật ngữ chuyên ngành, câu rõ ràng, không dùng từ lóng.
- "Business": văn phong kinh doanh lịch sự, ngắn gọn, chuyên nghiệp, giữ nguyên tên riêng, số liệu và thuật ngữ thương mại.
Không thay đổi build_prompt, không đổi các preset đang có. Chạy test: "python -m pytest backend/tests/test_translation_adapter.py backend/tests/test_translation_api.py -m 'not slow'" và báo kết quả. Sau đó đề xuất (chưa làm) cách sửa mobile/src/utils/buildContext.ts để gửi contextPreset 'Academic'/'Business' khi người dùng chỉ chọn đúng một giọng văn tương ứng.
````

**GIẢI THÍCH**
- **Làm gì:** thêm 2 giọng văn mới vào backend để "Học thuật"/"Kinh doanh" có hiệu lực mạnh hơn việc chỉ ghi trong chuỗi ngữ cảnh.
- **Sửa gì:** `backend/app/models/translation_adapter.py`.
- **Kiểm tra:** test backend vẫn pass.

---

# K. SỬA ĐỔI SAU KHI TEST (V2.1) — "Dịch từ" bấm được + kiểm tra ngôn ngữ backend hỗ trợ

> **Bối cảnh:** sau khi chạy xong Task 0–32, bạn test và thấy mình hiểu nhầm một chỗ:
> - Màn có đoạn mô tả *"Ngôn ngữ này được chọn sẵn mỗi lần mở app…"* thực ra là màn **"Dịch từ"**: bấm vào ô **Tiếng Việt** (bên trái) là mở màn này. Tiêu đề đổi từ "Ngôn ngữ mặc định" thành **"Dịch từ"**.
> - Vì vậy bỏ hẳn phần "Đổi ngôn ngữ mặc định" mà Task 24/25 đã thêm vào màn "Dịch sang".
> - Cần kiểm tra backend thật sự hỗ trợ bao nhiêu ngôn ngữ (cả **dịch từ** và **dịch sang**) và đưa đúng danh sách đó vào frontend.
>
> Các task 34–43 dưới đây là **bản vá chạy sau Task 32**. Thứ tự: 34 → 43, mỗi lần một task. Nếu bạn làm lại dự án từ đầu thì bỏ qua Task 25 và phần link "Đổi ngôn ngữ mặc định" của Task 24, rồi làm Task 34–43 sau Task 32.

## TASK 34 — Kiểm tra backend hỗ trợ những ngôn ngữ nào (chưa sửa code app)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App. Backend FastAPI ở backend/ (KHÔNG được sửa bất kỳ file nào trong backend/). Tôi muốn biết CHÍNH XÁC backend hỗ trợ những ngôn ngữ nào, để đưa đúng danh sách vào app mobile, cho cả ngôn ngữ NGUỒN (Dịch từ) lẫn ngôn ngữ ĐÍCH (Dịch sang).

Việc cần làm (CHỈ việc này, chỉ đọc code và viết báo cáo): đọc kỹ các file sau và trả lời bằng bảng tiếng Việt:
1. backend/app/models/translation_adapter.py: dict LANGUAGE_NAMES (liệt kê đủ mọi mã ngôn ngữ), hàm build_prompt (mã lạ/không có trong LANGUAGE_NAMES thì xử lý ra sao: lỗi, đoán tự động hay dùng thẳng chuỗi?), có hỗ trợ source_language 'auto' hay không, mô hình TranslateGemma có giới hạn cặp ngôn ngữ nào không.
2. backend/app/api/routes/translate.py và backend/app/schemas/translate.py: có kiểm tra/validate mã ngôn ngữ không (danh sách cho phép?), mã nào bị từ chối.
3. backend/app/models/asr_adapter.py và routes/asr.py: nhận dạng giọng nói hỗ trợ ngôn ngữ nào (PhoASR chỉ tiếng Việt? tham số language có đổi được không?). Và backend/app/api/routes/stream.py: trường source/target trong thông điệp "start" có được dùng cho ASR không.
4. backend/app/models/ocr_adapter.py và routes/ocr.py: RapidOCR đang nạp model/ngôn ngữ nào; hàm detect_language() có thể trả về những mã nào; ngôn ngữ nào (Latin có dấu như Pháp/Đức/Tây Ban Nha/Bồ Đào Nha, Hàn, Nhật, Trung, Việt, Anh) đọc được thật sự, ngôn ngữ nào không chắc chắn.
5. backend/app/models/tts_adapter.py và routes/tts.py: EDGE_VOICES_FEMALE / EDGE_VOICES_MALE có những mã nào; Pocket TTS hỗ trợ những ngôn ngữ nào; với mỗi ngôn ngữ đích thì đọc to được bằng engine nào (hay không đọc được).
6. Đọc thêm các test trong backend/tests liên quan để xác nhận (test_translation_api, test_tts_api, test_ocr_adapter, test_asr_api).

Kết quả: tạo file docs/language-support.md ở thư mục gốc dự án (ngoài backend/ và mobile/src/config/api.ts) gồm:
- Bảng chính, mỗi hàng là một ngôn ngữ backend nhận được: cột Tên (tiếng Việt) | Tên bản ngữ | Mã backend (đúng chuỗi dùng khi gọi API) | Dịch TỪ (nguồn) có/không | Dịch SANG (đích) có/không | Nhập giọng nói (ASR) có/không | Quét chữ (OCR) có/không/không chắc | Đọc to (TTS) engine hoặc không | Ghi chú.
- Mục "Cách backend xử lý mã lạ".
- Mục "Đề xuất danh sách đưa vào app": danh sách NGUỒN (thứ tự đề xuất, Tiếng Việt đầu tiên) và danh sách ĐÍCH (thứ tự đề xuất theo app cũ: English, Chinese (Simplified), Japanese, Korean, French, German, Spanish, Portuguese, rồi các ngôn ngữ khác nếu có; Tiếng Việt nếu backend dịch sang tiếng Việt được).
Nếu có thể chạy backend và model đã tải, hãy thử gọi nhanh /api/translate cho vài cặp (vi→en, en→vi, ja→vi, ko→vi, fr→vi) để xác nhận; nếu không chạy được thì nói rõ là kết luận chỉ dựa trên đọc code.
Cuối cùng trả lời ngắn trong chat: tổng số ngôn ngữ dịch nguồn / dịch đích / có ASR / có OCR / có TTS và những điểm đáng lo.
````

**GIẢI THÍCH**
- **Làm gì:** để DeepSeek tự kiểm tra backend hỗ trợ **bao nhiêu** và **những** ngôn ngữ nào, cho từng chức năng (dịch từ, dịch sang, nói, quét chữ, đọc to). Đây là "nguồn sự thật" cho các task sau.
- **Sửa gì:** chỉ tạo mới `docs/language-support.md`, không sửa code.
- **Kiểm tra:** mở `docs/language-support.md` đọc lại bảng. Đặc biệt xem: ASR (nhiều khả năng chỉ tiếng Việt), OCR (chữ Hàn/Latin có dấu có đọc được không), và TTS (ngôn ngữ nào không có giọng đọc). Nếu bạn thấy số liệu lạ, hỏi lại DeepSeek trước khi sang Task 35.

---

## TASK 35 — Danh mục ngôn ngữ trong app theo đúng backend

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). Đã có docs/language-support.md (báo cáo ngôn ngữ backend hỗ trợ) và constants/languages.ts hiện có (LANGUAGES, STT_LANGUAGES, supportsSpeechToText, SOURCE_LANGUAGE, TARGET_LANGUAGES, getTargetLabel, getTargetFullLabel, TargetLanguageCode, DEFAULT_TARGET_CODE). Không sửa backend, không sửa src/config/api.ts, không xoá LANGUAGES/STT_LANGUAGES/supportsSpeechToText cũ.

Việc cần làm (CHỈ việc này): viết lại phần mới của mobile/src/constants/languages.ts dựa vào docs/language-support.md (mã ngôn ngữ phải đúng chuỗi backend nhận).

0. DỮ LIỆU ĐÃ CHỐT từ báo cáo (nếu mâu thuẫn với phần "Đề xuất" trong báo cáo thì làm theo mục này):
   - Catalog có đúng 11 ngôn ngữ: vi, en, ja, zh, ko, fr, de, es, pt, ru, it. KHÔNG đưa nl (Hà Lan) vào vì backend không dịch được.
   - canBeSource = true cho cả 11 (dịch văn bản không giới hạn ngôn ngữ nguồn; người dùng gõ hoặc dán chữ). BỎ QUA đề xuất "nguồn chỉ vi" của báo cáo: việc hạn chế theo ngôn ngữ chỉ áp dụng cho giọng nói và quét chữ qua các cờ riêng bên dưới.
   - canBeTarget = true cho cả 11 (bao gồm 'vi').
   - supportsVoiceInput = true CHỈ với 'vi' (ASR chỉ tiếng Việt).
   - supportsOcr = true với vi, en, ja, zh; false với ko, fr, de, es, pt, ru, it (detect_language của backend chỉ nhận ra 4 ngôn ngữ đó, các ngôn ngữ còn lại dễ bị nhận nhầm).
   - supportsTts = true cho cả 11 (Edge-TTS).
   - Nhãn bổ sung: ru → label 'Русский (Russian)', shortLabel 'Русский'; it → label 'Italiano (Italian)', shortLabel 'Italiano'.
   - Thứ tự SOURCE_LANGUAGES: vi, en, zh, ja, ko, fr, de, es, pt, ru, it. Thứ tự TARGET_LANGUAGES: en, zh, ja, ko, fr, de, es, pt, ru, it, vi.
   Các mục 1–5 dưới đây vẫn áp dụng, đối chiếu với dữ liệu đã chốt này:
1. Tạo kiểu Language = { code: string; label: string; shortLabel: string; canBeSource: boolean; canBeTarget: boolean; supportsVoiceInput: boolean; supportsOcr: boolean; supportsTts: boolean }, và mảng LANGUAGE_CATALOG gồm MỌI ngôn ngữ backend hỗ trợ (bao gồm Tiếng Việt). Cờ lấy đúng từ bảng báo cáo (cột Dịch TỪ, Dịch SANG, ASR, OCR, TTS). Mẫu nhãn:
   - 'vi': label 'Tiếng Việt', shortLabel 'Tiếng Việt'
   - 'en': 'English' / 'English'
   - tiếng Trung: '中文 (Mandarin)' / '中文'
   - tiếng Nhật: '日本語 (Japanese)' / '日本語'
   - tiếng Hàn: '한국어 (Korean)' / '한국어'
   - tiếng Pháp: 'Français (French)' / 'Français'; Đức: 'Deutsch (German)' / 'Deutsch'; Tây Ban Nha: 'Español (Spanish)' / 'Español'; Bồ Đào Nha: 'Português (Portuguese)' / 'Português'
   - các ngôn ngữ khác backend hỗ trợ: theo mẫu 'Tên bản ngữ (Tên tiếng Anh)' / 'Tên bản ngữ'.
2. Export SOURCE_LANGUAGES = LANGUAGE_CATALOG.filter(canBeSource), thứ tự: Tiếng Việt đầu tiên, sau đó English, rồi các ngôn ngữ còn lại theo thứ tự đề xuất trong báo cáo. Export TARGET_LANGUAGES = LANGUAGE_CATALOG.filter(canBeTarget), thứ tự: English, 中文, 日本語, 한국어, Français, Deutsch, Español, Português, các ngôn ngữ khác, và Tiếng Việt ở cuối nếu dịch sang tiếng Việt được.
3. Export các hàm: getLanguage(code), getSourceLabel(code) (trả shortLabel, không có thì trả code), getTargetLabel(code) (shortLabel), getTargetFullLabel(code) và getSourceFullLabel(code) (label đầy đủ), supportsVoiceInput(code), supportsOcr(code), supportsTts(code). Kiểu LanguageCode (suy ra từ LANGUAGE_CATALOG as const) và DEFAULT_SOURCE_CODE = 'vi', DEFAULT_TARGET_CODE = 'en'.
4. Giữ tương thích: SOURCE_LANGUAGE (hằng cũ) giữ lại nhưng ghi chú @deprecated; TargetLanguageCode giữ lại làm alias; getTargetLabel/getTargetFullLabel giữ nguyên chữ ký.
5. Tìm trong mobile/src mọi nơi còn dùng SOURCE_LANGUAGE cố định hoặc giả định nguồn luôn là 'vi' ở phần hiển thị và liệt kê cho tôi (chưa sửa các nơi đó ở bước này, sẽ sửa ở các task sau).
Cuối cùng in bảng ngắn: số ngôn ngữ trong SOURCE_LANGUAGES, TARGET_LANGUAGES, và số ngôn ngữ có voice/OCR/TTS.
````

**GIẢI THÍCH**
- **Làm gì:** tạo "danh mục ngôn ngữ" duy nhất trong app, mỗi ngôn ngữ kèm cờ cho biết dùng được làm nguồn, đích, nói, quét chữ, đọc to hay không — đúng như backend.
- **Sửa gì:** `constants/languages.ts`.
- **Kiểm tra:** typecheck sạch; số lượng khớp báo cáo Task 34.

---

## TASK 36 — Store: ngôn ngữ nguồn thay đổi được và lưu làm mặc định

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). Đã có constants/languages.ts mới (LANGUAGE_CATALOG, SOURCE_LANGUAGES, TARGET_LANGUAGES, DEFAULT_SOURCE_CODE, DEFAULT_TARGET_CODE, LanguageCode), store/settingsStore.ts (persist, defaultTargetLang), store/translationStore.ts (inputLanguage, targetLanguage, setTargetLang, applyDefaultsFromSettings, translate). Không sửa backend, không sửa src/config/api.ts, không xoá logic hiện có.

Thay đổi hành vi: ngôn ngữ NGUỒN không còn cố định là tiếng Việt; người dùng chọn ở màn "Dịch từ". Lựa chọn nguồn được LƯU làm mặc định cho lần mở app sau. Ngôn ngữ ĐÍCH không còn khái niệm "mặc định" riêng.

Việc cần làm (CHỈ việc này):
1. settingsStore.ts: THAY defaultTargetLang bằng defaultSourceLang: LanguageCode (mặc định DEFAULT_SOURCE_CODE = 'vi'); action setDefaultSourceLang(code). Bỏ setDefaultTargetLang. Dữ liệu cũ đã lưu có defaultTargetLang thì bỏ qua (thêm version/migrate nếu persist yêu cầu, tránh crash khi đọc dữ liệu cũ).
2. translationStore.ts:
   - Thêm action setSourceLang(code: LanguageCode): đặt inputLanguage = code. Nếu code trùng với targetLanguage hiện tại thì đổi targetLanguage sang ngôn ngữ nguồn cũ (hoán đổi) để nguồn luôn khác đích. Nếu phase là 'result' hoặc 'error' thì phase='idle', xoá translatedText, translateError (giống setTargetLang). Gọi setDefaultSourceLang(code) của settingsStore để lưu bền.
   - Sửa setTargetLang(code): nếu code trùng với inputLanguage hiện tại thì đổi inputLanguage sang ngôn ngữ đích cũ (hoán đổi); không lưu bền gì cả.
   - Sửa applyDefaultsFromSettings(): inputLanguage = settingsStore.defaultSourceLang; targetLanguage = DEFAULT_TARGET_CODE, nhưng nếu nguồn là 'en' thì targetLanguage = 'vi' (nếu 'vi' có trong TARGET_LANGUAGES, ngược lại ngôn ngữ đầu tiên khác nguồn).
   - translate(): truyền source_language = inputLanguage (không còn gán cứng 'vi') và target_language = targetLanguage.
   - Cả hai setter nếu nhận mã không có trong catalog thì bỏ qua (không đổi state).
3. Tìm các nơi khác trong mobile/src còn gán cứng 'vi' làm nguồn (ví dụ Camera/OCR, Voice) và liệt kê (sẽ sửa ở các task sau; việc gán cứng 'vi' cho nguồn giọng nói là ĐÚNG khi chỉ tiếng Việt có ASR nên đừng sửa phần ASR/streaming ở bước này).
4. Chưa sửa màn hình nào.
````

**GIẢI THÍCH**
- **Làm gì:** cho phép đổi ngôn ngữ nguồn; nguồn luôn khác đích (chọn trùng thì tự hoán đổi); nguồn được nhớ cho lần mở app sau; dịch thật sự dùng nguồn người dùng chọn.
- **Sửa gì:** `store/settingsStore.ts`, `store/translationStore.ts`.
- **Kiểm tra:** typecheck sạch. (Hành vi sẽ thấy rõ sau Task 38.)

---

## TASK 37 — Bỏ phần "Ngôn ngữ mặc định" ở màn "Dịch sang"

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, React Navigation). Trước đây Task 24/25 thêm: link "Đổi ngôn ngữ mặc định" ở cuối màn TargetLanguageScreen, route 'DefaultLanguage' và màn DefaultLanguageScreen. Nay các thứ này SAI Ý và phải bỏ. Không sửa backend, không sửa src/config/api.ts.

Việc cần làm (CHỈ việc này):
1. TargetLanguageScreen.tsx: xoá link/ListFooterComponent "Đổi ngôn ngữ mặc định" và mọi liên quan (navigate('DefaultLanguage')). Giữ nguyên phần còn lại của màn.
2. navigation/types.ts và AppNavigator.tsx: bỏ route 'DefaultLanguage'; THÊM route 'SourceLanguage' (animation 'slide_from_right') trỏ tới SourceLanguageScreen (sẽ tạo ở Task 38; tạm thời trỏ vào file DefaultLanguageScreen.tsx đổi tên). Cụ thể: đổi tên file screens/DefaultLanguageScreen.tsx thành screens/SourceLanguageScreen.tsx (dùng git mv nếu là repo git) và đổi tên component/export tương ứng thành SourceLanguageScreen. Chưa đổi nội dung bên trong (làm ở Task 38).
3. strings.ts: xoá strings.targetLanguage.setDefault ("Đổi ngôn ngữ mặc định"); đổi object defaultLanguage thành sourceLanguage với: title "Dịch từ", description "Ngôn ngữ này được chọn sẵn mỗi lần mở app. Bạn vẫn đổi được ở màn Dịch.", section "Ngôn ngữ có sẵn". Cập nhật mọi chỗ dùng.
4. Tìm mọi tham chiếu còn lại tới 'DefaultLanguage' / defaultTargetLang / setDefaultTargetLang trong mobile/src và dọn sạch (không để lỗi typecheck).
5. Chạy npm run typecheck và báo kết quả.
````

**GIẢI THÍCH**
- **Làm gì:** gỡ phần "đổi ngôn ngữ mặc định" khỏi màn "Dịch sang"; chuyển màn mặc định cũ thành màn "Dịch từ" (về mặt tên file/route/chuỗi).
- **Sửa gì:** `TargetLanguageScreen.tsx`, `navigation/types.ts`, `AppNavigator.tsx`, `strings.ts`; đổi tên `DefaultLanguageScreen.tsx` → `SourceLanguageScreen.tsx`.
- **Kiểm tra:** typecheck sạch; màn "Dịch sang" không còn link chữ xanh ở cuối.

---

## TASK 38 — SourceLanguageScreen ("Dịch từ") + bấm ô "Tiếng Việt" để mở

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand, React Navigation). Đã có screens/SourceLanguageScreen.tsx (trước đây là DefaultLanguageScreen), components/LanguageRow.tsx, ScreenHeader, ThemedText, theme, scale, strings.sourceLanguage, constants/languages.ts (SOURCE_LANGUAGES, getSourceFullLabel), translationStore (inputLanguage, setSourceLang), route 'SourceLanguage'. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này): viết lại SourceLanguageScreen.tsx cho đúng màn "Dịch từ":
Giao diện (giống màn TargetLanguageScreen; SafeAreaView nền colors.background, paddingHorizontal s(21), maxWidth MAX_CONTENT_WIDTH căn giữa):
- ScreenHeader title "Dịch từ" (nút back tròn 46 + tiêu đề 28 đậm; back gọi goBack()).
- Cách vs(18): đoạn mô tả "Ngôn ngữ này được chọn sẵn mỗi lần mở app. Bạn vẫn đổi được ở màn Dịch." (ms(15), lineHeight ms(22), màu textSecondary, paddingLeft s(19)).
- Cách vs(22): nhãn section "Ngôn ngữ có sẵn" (bold ms(14), textSecondary, paddingLeft s(19)).
- Cách vs(10): danh sách LanguageRow cho TOÀN BỘ SOURCE_LANGUAGES (label đầy đủ qua getSourceFullLabel; Tiếng Việt đầu tiên) trong FlatList cuộn được; hàng đang chọn (inputLanguage) nền primarySoftStrong + dấu ✓; paddingBottom vs(24) + safe area.
- Bấm một hàng: gọi setSourceLang(code) của translationStore (store tự lưu mặc định và tự hoán đổi đích nếu trùng), rồi goBack() sau 250ms để thấy ✓ chuyển.

Nối ở HomeScreen.tsx: ô "Dịch từ" (bên trái hàng ngôn ngữ) trở thành Pressable → navigation.navigate('SourceLanguage'). Hiển thị chữ ngôn ngữ nguồn bằng getSourceLabel(inputLanguage) (không còn gán cứng "Tiếng Việt"). Kiểu dáng của ô "Dịch từ" phải GIỐNG HỆT ô "Dịch sang": nền colors.surface (trắng), viền 1px colors.border, bo s(22), padding ngang s(16), hai dòng chữ (nhãn "Dịch từ" + tên ngôn ngữ) và icon "chevron-down" ms(20) màu textSecondary ở bên phải. Thêm accessibilityRole="button" và accessibilityLabel `Dịch từ ${tên đầy đủ}, bấm để đổi ngôn ngữ`. Mũi tên "→" ở giữa vẫn chỉ là icon tĩnh.
Khi người dùng đổi nguồn mà đang có kết quả cũ, store đã đưa phase về 'idle' → HomeScreen hiện lại nút Dịch (kiểm tra đúng).
````

**GIẢI THÍCH**
- **Làm gì:** bấm ô **Tiếng Việt** → mở màn **"Dịch từ"** (có đoạn mô tả "được chọn sẵn mỗi lần mở app…") với danh sách mọi ngôn ngữ backend nhận làm nguồn; chọn xong được nhớ cho lần sau.
- **Sửa gì:** `screens/SourceLanguageScreen.tsx`, `screens/HomeScreen.tsx`.
- **Lưu ý:** theo yêu cầu của bạn, ô "Dịch từ" có kiểu **giống hệt ô "Dịch sang"** (nền trắng, có mũi tên ⌄), không còn mờ như ảnh thiết kế gốc. Nếu bạn đã chạy Task 38 từ trước khi có thay đổi này thì chạy thêm Task 43.
- **Kiểm tra:** chọn English làm nguồn → quay về thấy "English → ?"; đích tự đổi nếu trùng; tắt app mở lại vẫn là English.

---

## TASK 39 — Màn "Dịch sang": dùng danh mục ngôn ngữ mới

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). TargetLanguageScreen.tsx hiện hiển thị TARGET_LANGUAGES cũ. Đã có constants/languages.ts mới (TARGET_LANGUAGES theo backend, getTargetFullLabel). Không sửa backend, không sửa src/config/api.ts.

Việc cần làm (CHỈ việc này), trong TargetLanguageScreen.tsx:
1. Danh sách lấy từ TARGET_LANGUAGES mới (đủ mọi ngôn ngữ backend dịch sang được, label đầy đủ qua getTargetFullLabel); FlatList cuộn được. Hàng đang chọn (targetLanguage) nền primarySoftStrong + ✓.
2. Bấm một hàng: gọi setTargetLang(code) (store tự hoán đổi nguồn nếu trùng) rồi goBack().
3. Không ẩn ngôn ngữ trùng với nguồn (người dùng chọn thì hoán đổi), nhưng nếu hàng đó chính là ngôn ngữ nguồn hiện tại thì thêm dòng phụ nhỏ ms(13) màu textSecondary bên dưới tên: "Đang là ngôn ngữ nguồn — sẽ hoán đổi".
4. Ở HomeScreen, thẻ "Dịch sang" hiện getTargetLabel(targetLanguage) (shortLabel). Kiểm tra không còn danh sách ngôn ngữ cứng nào khác trong app.
Giữ nguyên kiểu dáng đã có của màn.
````

**GIẢI THÍCH**
- **Làm gì:** danh sách "Dịch sang" lấy đúng theo backend (không còn danh sách tự soạn); chọn trùng nguồn thì tự hoán đổi và có chú thích.
- **Sửa gì:** `screens/TargetLanguageScreen.tsx`, kiểm tra nhẹ `HomeScreen.tsx`.
- **Kiểm tra:** đếm số hàng khớp số ngôn ngữ đích trong `docs/language-support.md`.

---

## TASK 40 — Mic / camera / Đọc to: chỉ bật khi ngôn ngữ hỗ trợ

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). Nguồn giờ có thể đổi, nhưng không phải ngôn ngữ nào cũng nhập giọng nói (ASR), quét chữ (OCR) hoặc đọc to (TTS) được. Đã có constants/languages.ts với supportsVoiceInput(code), supportsOcr(code), supportsTts(code). Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này):
1. strings.ts thêm: voice.unsupported "Nhận dạng giọng nói hiện chỉ hỗ trợ tiếng Việt. Hãy chọn Dịch từ: Tiếng Việt." (nội dung điều chỉnh theo danh sách ngôn ngữ có ASR trong catalog: nếu có nhiều hơn tiếng Việt thì viết "Nhận dạng giọng nói chưa hỗ trợ <tên ngôn ngữ nguồn>."), camera.ocrUnsupported "Quét chữ chưa hỗ trợ <tên ngôn ngữ nguồn>. Hãy chọn Dịch từ: Tiếng Việt, English, 中文 hoặc 日本語." (dùng hàm tạo chuỗi nhận tên; danh sách gợi ý lấy từ các ngôn ngữ có supportsOcr trong catalog).
2. HomeScreen: nút mic và nút camera trong ô nhập vẫn hiển thị bình thường. Khi bấm:
   - mic: nếu !supportsVoiceInput(inputLanguage) thì KHÔNG mở màn Giọng nói; hiện dòng thông báo nhỏ ms(14) màu textSecondary ngay dưới ô nhập (tự ẩn sau 3 giây, có AccessibilityInfo.announceForAccessibility) với nội dung strings.voice.unsupported. Nếu hỗ trợ thì mở như cũ.
   - camera: tương tự với supportsOcr(inputLanguage) và strings.camera.ocrUnsupported.
3. VoiceListeningScreen: nguồn gửi lên ASR/stream vẫn đúng ngôn ngữ nguồn hiện tại (inputLanguage) chứ không gán cứng 'vi' (nếu backend ASR chỉ có tiếng Việt thì supportsVoiceInput đã chặn từ bước 2). Dòng gợi ý đổi thành `Hãy nói ${tên ngôn ngữ nguồn}. Chữ hiện ra khi bạn nói.` (và bản "Chữ sẽ hiện sau khi bạn dừng." tương ứng).
4. CameraScreen/OCR: KHÔNG tự đổi ngôn ngữ nguồn dựa trên kết quả OCR (hàm detect_language của backend chỉ trả vi/en/ja/zh và dễ nhận nhầm các ngôn ngữ Latin có dấu thành 'vi'). Giữ nguyên inputLanguage người dùng đã chọn; không thêm logic phát hiện ngôn ngữ.
5. Khoá chống nhầm: nếu nguồn đổi trong lúc đang ghi âm/OCR thì bỏ kết quả cũ (dùng sessionId đã có).
````

**GIẢI THÍCH**
- **Làm gì:** nhập giọng nói, quét chữ chỉ chạy với ngôn ngữ nguồn mà backend hỗ trợ; bấm khi không hỗ trợ thì hiện dòng giải thích thay vì lỗi khó hiểu. Quét chữ chỉ mở cho tiếng Việt, English, 中文, 日本語 (backend chỉ nhận ra 4 ngôn ngữ này).
- **Sửa gì:** `strings.ts`, `HomeScreen.tsx`, `VoiceListeningScreen.tsx`, `CameraScreen.tsx`.
- **Kiểm tra:** chọn nguồn English rồi bấm mic → thấy dòng "Nhận dạng giọng nói…"; chọn lại Tiếng Việt thì mở được.

---

## TASK 41 — Nút "Đọc to" chỉ hiện khi ngôn ngữ đích có giọng đọc

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). Khối kết quả ở HomeScreen có nút "Đọc to" (PrimaryButton pill) và nút sao chép. Đã có supportsTts(code) trong constants/languages.ts (theo docs/language-support.md). Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms().

Việc cần làm (CHỈ việc này):
1. Trong thẻ kết quả của HomeScreen: nếu !supportsTts(targetLanguage) thì KHÔNG hiện nút "Đọc to" (chỉ còn nút sao chép tròn, căn trái như cũ); thêm dòng chữ nhỏ ms(13) màu textSecondary bên cạnh/bên dưới: "Chưa có giọng đọc cho ngôn ngữ này."
2. Hook useSpeech: trước khi gọi TTS, kiểm tra supportsTts(targetLanguage); nếu không hỗ trợ thì không gọi API và trả status 'error' với thông điệp trên.
3. Nếu backend có phân biệt engine/giọng (Pocket TTS với tham chiếu giọng hoặc Edge-TTS) thì đảm bảo yêu cầu gửi lên có language đúng mã backend (xem docs/language-support.md).
Không thay đổi giao diện khác.
````

**GIẢI THÍCH**
- **Làm gì:** tránh bấm "Đọc to" rồi lỗi với ngôn ngữ không có giọng đọc.
- **Sửa gì:** `HomeScreen.tsx`, `hooks/useSpeech.ts`.
- **Kiểm tra:** dịch sang ngôn ngữ có giọng thì thấy "Đọc to"; ngôn ngữ không có thì ẩn và có dòng chú thích (theo báo cáo Task 34, cả 11 ngôn ngữ đều có giọng đọc nên task này hiện chỉ là lớp bảo vệ, bạn sẽ không thấy khác biệt; có thể bỏ qua nếu muốn gọn).

---

## TASK 42 — Rà soát lại sau V2.1

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript, Zustand). Đã hoàn tất Task 34–41. Không sửa backend, không sửa src/config/api.ts. Không thêm tính năng mới.

Việc cần làm (CHỈ việc này): rà soát và sửa lỗi:
1. Chạy npm run typecheck, sửa mọi lỗi.
2. Tìm mọi tham chiếu còn sót tới 'DefaultLanguage', defaultTargetLang, setDefaultTargetLang, "Ngôn ngữ mặc định", "Đổi ngôn ngữ mặc định", SOURCE_LANGUAGE (hằng cũ) và danh sách ngôn ngữ viết cứng (en/ko/zh...) trong mobile/src; xoá hoặc chuyển sang constants/languages.ts.
3. Kiểm tra bằng đọc code các kịch bản và sửa nếu sai:
   a) Mở app lần đầu: nguồn 'vi', đích 'en'. Đổi nguồn sang English: đích tự đổi (do trùng) → tắt app mở lại: nguồn vẫn English, đích là 'vi' (theo applyDefaultsFromSettings).
   b) Ở màn "Dịch sang" chọn ngôn ngữ đang là nguồn: hai bên hoán đổi.
   c) Có kết quả dịch → đổi nguồn hoặc đích: kết quả biến mất, nút Dịch hiện lại.
   d) Nguồn không phải ngôn ngữ có ASR: bấm mic hiện dòng giải thích, không mở màn Giọng nói. Nguồn không có OCR: bấm camera hiện dòng giải thích.
   e) translate() gửi source_language và target_language đúng mã backend (kiểm tra payload trong services/api.ts).
   f) Màn "Dịch từ" và "Dịch sang" đều cuộn được với danh sách dài, và đúng số lượng như docs/language-support.md.
   g) Đổi sáng/tối vẫn hoạt động ở cả hai màn ngôn ngữ.
4. Báo cáo ngắn: đã sửa gì, còn lệch gì.
````

**GIẢI THÍCH**
- **Làm gì:** bước kiểm tra cuối cho phần vá: dọn tham chiếu cũ, thử các kịch bản chọn ngôn ngữ.
- **Sửa gì:** sửa nhỏ rải rác tuỳ lỗi tìm thấy.
- **Kiểm tra tay đề xuất:** (1) đổi nguồn sang English, dịch "Hello" sang Tiếng Việt; (2) đổi nguồn sang Japanese, chụp ảnh chữ Nhật; (3) mở lại app xem nguồn có được nhớ.

---

## TASK 43 — Ô "Dịch từ" giống hệt ô "Dịch sang" (nếu đã chạy Task 38 trước đó)

**PROMPT**

````text
[Bối cảnh] Dự án Translation-App, mobile/ (React Native Expo, TypeScript). HomeScreen.tsx có hàng ngôn ngữ gồm ô "Dịch từ" (hiện nền mờ surfaceMuted, không có mũi tên) → mũi tên "→" → ô "Dịch sang" (nền trắng, có icon chevron-down). Cả hai ô đều bấm được. Không sửa backend, không sửa src/config/api.ts.
[Kích thước] Mọi số là dp trên máy chuẩn 411x890; bọc s()/vs()/ms(). Màu từ useTheme().

Việc cần làm (CHỈ việc này):
1. Tạo component mobile/src/components/LanguageTile.tsx dùng chung cho cả hai ô. Props: label ("Dịch từ" hoặc "Dịch sang"), value (tên ngôn ngữ ngắn), onPress, accessibilityLabel. Kiểu dáng: flex 1, cao vs(59), nền colors.surface, viền 1px colors.border, bo góc s(22), padding ngang s(16); bên trái hai dòng chữ xếp dọc (nhãn typography.label 12 màu textSecondary; giá trị typography.value 17 đậm màu textPrimary); bên phải icon Ionicons "chevron-down" ms(20) màu textSecondary; Pressable, opacity 0.85 khi nhấn, accessibilityRole="button".
2. Trong HomeScreen.tsx thay hai ô cũ bằng hai LanguageTile giống hệt nhau về kích thước và kiểu dáng: ô trái label "Dịch từ" value getSourceLabel(inputLanguage) mở màn 'SourceLanguage'; ô phải label "Dịch sang" value getTargetLabel(targetLanguage) mở màn 'TargetLanguage'. Giữa hai ô vẫn là icon tĩnh "arrow-forward" ms(20) màu textSecondary, chiếm ngang s(38), căn giữa.
3. Xoá mọi chỗ còn dùng màu surfaceMuted cho ô "Dịch từ" (giữ màu này trong theme, không xoá khỏi colors.ts).
Không đổi gì khác.
````

**GIẢI THÍCH**
- **Làm gì:** ô "Dịch từ" có nền trắng và mũi tên ⌄ y hệt ô "Dịch sang"; gom hai ô thành một component nên sau này sửa một chỗ là đổi cả hai.
- **Sửa gì:** tạo mới `components/LanguageTile.tsx`; sửa `screens/HomeScreen.tsx`.
- **Kiểm tra:** hai ô cao bằng nhau, cùng viền, cùng bo góc, cùng có ⌄; bấm ô trái mở màn "Dịch từ", ô phải mở "Dịch sang".

---

## Phụ lục — Khi DeepSeek làm sai

- **Lỗi TypeScript:** *"Sửa lỗi sau, không đổi giao diện: <dán lỗi>"*.
- **Làm quá phạm vi:** *"Bạn đã sửa file ngoài phạm vi. Hoàn tác thay đổi ở <file> và chỉ làm đúng việc đã giao."*
- **Lệch giao diện so với thiết kế:** vì DeepSeek không thấy PDF, hãy mô tả chỗ lệch bằng chữ hoặc gửi ảnh chụp app hiện tại cùng đoạn mô tả đặc tả trong task đó: *"So với đặc tả trong task, chỗ lệch là: <mô tả>. Sửa chỉ trong <file>."*
- **Lệch trên máy khác:** gửi *"Trên máy 360x640 phần <X> bị <vỡ/che>. Kiểm tra lại mọi số cứng ở <file>, chuyển qua s()/vs()/ms() và dùng minHeight thay vì height cố định cho chỗ chứa chữ."*
- **Quên ngữ cảnh:** gửi lại Task 0 (kèm `giai_thich.md`) rồi gửi tiếp task đang làm.
