/**
 * Định dạng số giây thành chuỗi "m:ss" (ví dụ: 0 → "0:00", 75 → "1:15").
 * Dùng để hiện bộ đếm giờ trên VoiceListeningScreen.
 */
export function formatMmSs(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(s / 60);
  const seconds = s % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}
