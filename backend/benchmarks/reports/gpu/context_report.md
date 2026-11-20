# Báo Cáo Đánh Giá Hệ Thống (Benchmark Evaluation Report)

- **Thời gian chạy**: `2026-11-20T20:16:18.987902`
- **Môi trường**: Linux / Multimodal Translation System
- **TranslateGemma backend**: requested=`cuda`, actual=`cuda`, gpu_offload=`True`, supported=`True`, n_gpu_layers=`-1`, reason=`none`

## 1. Bảng Tổng Hợp Chỉ Số

| Module | Chỉ Số (Metric) | Kết Quả | Trạng Thái |
| :--- | :--- | :--- | :--- |
| **TranslateGemma (MT)** | - | - | N/A |
| **Context Presets** | Độ chính xác ngữ cảnh | **95.0%** | Hoàn tất |
| | Formal | **100.0%** | Hoàn tất |
| | Friendly | **90.0%** | Hoàn tất |
| | IT | **95.0%** | Hoàn tất |
| | Medical | **93.3%** | Hoàn tất |
| | Travel | **93.3%** | Hoàn tất |
| | General | **100.0%** | Hoàn tất |
| **PhoASR (Speech)** | - | - | N/A |
| **Edge-TTS (Speech)** | - | - | N/A |

## 2. Nguồn Dữ Liệu

- **context**: source=`cache`, returned=`100`, available=`100`, meets_100=`True`, license=`mixed: curated, CC-BY-2.0, research-only, CC-BY-SA-4.0`
  - preset_counts: `{'Formal': 20, 'Friendly': 20, 'IT': 20, 'Medical': 15, 'Travel': 15, 'General': 10}`

## 3. Ghi Chú & Khuyến Nghị

- QED trong Context có license research-only; cần ghi rõ khi công bố kết quả.
- Nếu mô hình chưa nạp weights, chạy `python backend/scripts/download_models.py` để bổ sung weights.
- Xem chi tiết từng câu kiểm thử tại: `context_results.json`.