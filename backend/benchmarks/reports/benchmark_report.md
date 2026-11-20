# Báo Cáo Đánh Giá Hệ Thống (Benchmark Evaluation Report)

- **Thời gian chạy**: `2026-11-19T20:24:34.121769`
- **Môi trường**: Linux / Multimodal Translation System

## 1. Bảng Tổng Hợp Chỉ Số

| Module | Chỉ Số (Metric) | Kết Quả | Trạng Thái |
| :--- | :--- | :--- | :--- |
| **TranslateGemma (MT)** | BLEU (corpus) | **37.37** | Hoàn tất |
| | BLEU trung bình câu | **35.24** | Hoàn tất |
| | chrF++ | **59.99** | Hoàn tất |
| | Độ trễ trung bình | **4062.5 ms** | Hoàn tất |
| **Context Presets** | Độ chính xác ngữ cảnh | **93.0%** | Hoàn tất |
| | Formal | **95.0%** | Hoàn tất |
| | Friendly | **90.0%** | Hoàn tất |
| | IT | **95.0%** | Hoàn tất |
| | Medical | **93.3%** | Hoàn tất |
| | Travel | **86.7%** | Hoàn tất |
| | General | **100.0%** | Hoàn tất |
| **PhoASR (Speech)** | Word Error Rate (WER) | **8.91** | Hoàn tất |
| | Character Error Rate (CER) | **5.7** | Hoàn tất |
| | Real-Time Factor (RTF) | **0.107x** | Hoàn tất |
| **Edge-TTS (Speech)** | Tỷ lệ tổng hợp thành công | **85.0%** | Hoàn tất |
| | Độ trễ trung bình | **11533.5 ms** | Hoàn tất |
| | Real-Time Factor (RTF) | **1.867x** | Hoàn tất |
| | Round-trip WER (PhoASR) | **10.71** | Hoàn tất |

## 2. Nguồn Dữ Liệu

- **translation**: source=`cache`, returned=`100`, available=`1012`, meets_100=`True`, license=`CC-BY-SA-4.0`
- **context**: source=`curated+online`, returned=`100`, available=`100`, meets_100=`True`, license=`mixed: curated, CC-BY-2.0, research-only, CC-BY-SA-4.0`
  - preset_counts: `{'Formal': 20, 'Friendly': 20, 'IT': 20, 'Medical': 15, 'Travel': 15, 'General': 10}`
- **asr**: source=`cache+download`, returned=`100`, available=`100`, meets_100=`True`, license=`CC-BY-4.0`
- **tts**: source=`cache`, returned=`100`, available=`851`, meets_100=`True`, license=`CC-BY-4.0`

## 3. Ghi Chú & Khuyến Nghị

- TTS WER/CER là round-trip qua PhoASR, không phải điểm MOS; chỉ phản ánh mức độ giữ nội dung sau tổng hợp.
- QED trong Context có license research-only; cần ghi rõ khi công bố kết quả.
- Nếu mô hình chưa nạp weights, chạy `python backend/scripts/download_models.py` để bổ sung weights.
- Xem chi tiết từng câu kiểm thử tại: `benchmark_results.json`.