# Báo Cáo Đánh Giá Hệ Thống (Benchmark Evaluation Report)

- **Thời gian chạy**: `2026-11-20T20:13:47.998631`
- **Môi trường**: Linux / Multimodal Translation System
- **TranslateGemma backend**: requested=`cuda`, actual=`cuda`, gpu_offload=`True`, supported=`True`, n_gpu_layers=`-1`, reason=`none`

## 1. Bảng Tổng Hợp Chỉ Số

| Module | Chỉ Số (Metric) | Kết Quả | Trạng Thái |
| :--- | :--- | :--- | :--- |
| **TranslateGemma (MT)** | BLEU (corpus) | **38.21** | Hoàn tất |
| | BLEU trung bình câu | **35.84** | Hoàn tất |
| | chrF++ | **60.12** | Hoàn tất |
| | Độ trễ trung bình | **561.3 ms** | Hoàn tất |
| **Context Presets** | - | - | N/A |
| **PhoASR (Speech)** | - | - | N/A |
| **Edge-TTS (Speech)** | - | - | N/A |

## 2. Nguồn Dữ Liệu

- **translation**: source=`cache`, returned=`100`, available=`1012`, meets_100=`True`, license=`CC-BY-SA-4.0`

## 3. Ghi Chú & Khuyến Nghị

- QED trong Context có license research-only; cần ghi rõ khi công bố kết quả.
- Nếu mô hình chưa nạp weights, chạy `python backend/scripts/download_models.py` để bổ sung weights.
- Xem chi tiết từng câu kiểm thử tại: `translation_results.json`.