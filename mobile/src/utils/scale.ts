/**
 * Quy ước co giãn kích thước giao diện cho máy chuẩn 411x890 dp (Pixel 6).
 *
 * - `s(size)`: co giãn theo chiều NGANG = size * (SCREEN_WIDTH / BASE_WIDTH).
 *   Dùng cho: chiều rộng, padding/margin ngang, borderRadius, kích thước nút/icon vuông.
 * - `vs(size)`: co giãn theo chiều DỌC = size * (SCREEN_HEIGHT / BASE_HEIGHT).
 *   Dùng cho: chiều cao khối lớn (ô nhập, thẻ, nút), khoảng cách dọc.
 * - `ms(size, factor = 0.5)`: co giãn VỪA MỪA = size + (s(size) - size) * factor.
 *   Dùng cho: cỡ chữ, lineHeight, kích thước icon.
 *
 * Hệ số co giãn được kẹp trong khoảng [0.8, 1.3] để giao diện không quá nhỏ
 * trên máy bé hay quá to trên tablet. Kết quả làm tròn bằng
 * PixelRatio.roundToNearestPixel.
 *
 * QUY TẮC BẮT BUỘC:
 * - KHÔNG viết số cứng (hardcode) cho kích thước trong StyleSheet,
 *   trừ độ dày viền 1 (StyleSheet.hairlineWidth hoặc 1) và 0.
 * - Luôn dùng s() cho ngang/bo góc/padding, vs() cho chiều cao khối lớn,
 *   ms() cho chữ/icon.
 */

import { Dimensions, PixelRatio } from 'react-native';

export const BASE_WIDTH = 411;
export const BASE_HEIGHT = 890;

// Lấy kích thước cửa sổ; dùng cạnh ngắn làm width và cạnh dài làm height
// để xoay máy không phá tính toán co giãn.
const window = Dimensions.get('window');
const SCREEN_WIDTH_RAW = Math.min(window.width, window.height);
const SCREEN_HEIGHT_RAW = Math.max(window.width, window.height);

export const SCREEN_WIDTH = SCREEN_WIDTH_RAW;
export const SCREEN_HEIGHT = SCREEN_HEIGHT_RAW;

const scaleX = Math.min(Math.max(SCREEN_WIDTH / BASE_WIDTH, 0.8), 1.3);
const scaleY = Math.min(Math.max(SCREEN_HEIGHT / BASE_HEIGHT, 0.8), 1.3);

/**
 * Co giãn theo chiều ngang. Dùng cho chiều rộng, padding/margin ngang,
 * borderRadius, kích thước nút/icon vuông.
 */
export function s(size: number): number {
  return PixelRatio.roundToNearestPixel(size * scaleX);
}

/**
 * Co giãn theo chiều dọc. Dùng cho chiều cao khối lớn (ô nhập, thẻ, nút),
 * khoảng cách dọc.
 */
export function vs(size: number): number {
  return PixelRatio.roundToNearestPixel(size * scaleY);
}

/**
 * Co giãn vừa phải (dùng cho cỡ chữ, lineHeight, icon).
 * ms(size, factor = 0.5) = size + (s(size) - size) * factor
 */
export function ms(size: number, factor: number = 0.5): number {
  return PixelRatio.roundToNearestPixel(size + (s(size) - size) * factor);
}

/**
 * Thiết bị màn hình nhỏ (chiều cao dưới 700 dp).
 */
export const isSmallDevice = SCREEN_HEIGHT < 700;

/**
 * Chiều rộng tối đa của nội dung chính trên máy bảng (tablet), dùng để
 * căn giữa nội dung khi màn hình quá rộng.
 */
export const MAX_CONTENT_WIDTH = 560;
