/**
 * Bảng màu giao diện Translation-App.
 * - lightColors / darkColors: thay đổi theo chế độ sáng/tối.
 * - cameraColors: cố định, không đổi theo theme, dùng cho màn hình camera (chụp ảnh OCR).
 */

export interface ThemeColors {
  background: string;
  surface: string;
  surfaceMuted: string;
  inputBg: string;
  border: string;
  borderStrong: string;
  primary: string;
  onPrimary: string;
  primarySoft: string;
  primarySoftStrong: string;
  primaryDark: string;
  textPrimary: string;
  textSecondary: string;
  placeholder: string;
  interimText: string;
  disabledBg: string;
  disabledText: string;
  iconButtonBg: string;
  danger: string;
  dangerSoft: string;
  dangerBorder: string;
  dangerTitle: string;
  dangerText: string;
}

export const lightColors: ThemeColors = {
  background: '#F2F3FA',
  surface: '#FFFFFF',
  surfaceMuted: '#ECEEF6',
  inputBg: '#F6F7FC',
  border: '#E3E6F0',
  borderStrong: '#C9CDDB',
  primary: '#3347D6',
  onPrimary: '#FFFFFF',
  primarySoft: '#E6E8FF',
  primarySoftStrong: '#DDE2FB',
  primaryDark: '#1E2A9E',
  textPrimary: '#111827',
  textSecondary: '#5B6075',
  placeholder: '#7A7D87',
  interimText: '#6B7280',
  disabledBg: '#DDE1EC',
  disabledText: '#5B6075',
  iconButtonBg: '#E9EBF4',
  danger: '#B42318',
  dangerSoft: '#FFEFEE',
  dangerBorder: '#F0B8B5',
  dangerTitle: '#8A1C14',
  dangerText: '#6B2B28',
};

export const darkColors: ThemeColors = {
  background: '#0F1220',
  surface: '#181C2E',
  surfaceMuted: '#1F2438',
  inputBg: '#131728',
  border: '#2A3050',
  borderStrong: '#3A4166',
  primary: '#6B7DFF',
  onPrimary: '#0B1033',
  primarySoft: '#262C57',
  primarySoftStrong: '#2B3366',
  primaryDark: '#AEB8FF',
  textPrimary: '#F2F4FA',
  textSecondary: '#A3A9C0',
  placeholder: '#8087A0',
  interimText: '#9BA1B8',
  disabledBg: '#252A40',
  disabledText: '#7E85A0',
  iconButtonBg: '#252A40',
  danger: '#FF6B5E',
  dangerSoft: '#3A1F22',
  dangerBorder: '#6B2F2F',
  dangerTitle: '#FFB4AC',
  dangerText: '#E8C4C0',
};

export interface CameraColors {
  background: string;
  bottomBar: string;
  pill: string;
  circleButton: string;
  closeButton: string;
  frameWhite: string;
  frameYellow: string;
  frameRed: string;
  descText: string;
  hintText: string;
  text: string;
  /** Lớp phủ đen mờ trên ảnh đã chụp (dim 40%). */
  imageOverlay: string;
  /** Nền nút outline trên nền camera tối (nút "Chụp lại"). */
  buttonSurface: string;
  /** Màu chữ/icon của nút outline trên nền camera tối. */
  buttonText: string;
}

export const cameraColors: CameraColors = {
  background: '#1E2B38',
  bottomBar: '#0F1A22',
  pill: '#182836',
  circleButton: '#2F3D49',
  closeButton: 'rgba(255,255,255,0.25)',
  frameWhite: '#FFFFFF',
  frameYellow: '#F2C94C',
  frameRed: '#FF6B5E',
  descText: '#B8C2D0',
  hintText: '#A9B4FF',
  text: '#FFFFFF',
  imageOverlay: 'rgba(0, 0, 0, 0.4)',
  buttonSurface: '#FFFFFF',
  buttonText: '#111827',
};
