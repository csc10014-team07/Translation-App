import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  View,
  Image,
  Pressable,
  ActivityIndicator,
  AppState,
  Linking,
  LayoutChangeEvent,
  StyleSheet,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import type { CameraScreenProps } from '../navigation/types';
import { useTheme } from '../theme/ThemeProvider';
import { cameraColors } from '../theme/colors';
import ThemedText from '../theme/ThemedText';
import IconCircleButton from '../components/IconCircleButton';
import CornerFrame from '../components/CornerFrame';
import PrimaryButton from '../components/PrimaryButton';
import OutlineButton from '../components/OutlineButton';
import { strings } from '../constants/strings';
import { useTranslationStore, isNetworkError } from '../store/translationStore';
import { s, vs, ms, SCREEN_HEIGHT } from '../utils/scale';

type CamState = 'ready' | 'processing' | 'error' | 'noPermission';

/** Khoảng cách đáy khung ngắm theo từng trạng thái (dp). */
const FRAME_BOTTOM: Record<CamState, number> = {
  ready: 165,
  processing: 130,
  error: 165,
  noPermission: 165,
};

/** Màu khung ngắm theo từng trạng thái. */
const FRAME_COLOR: Record<CamState, string> = {
  ready: cameraColors.frameWhite,
  processing: cameraColors.frameYellow,
  error: cameraColors.frameRed,
  noPermission: cameraColors.frameWhite,
};

export default function CameraScreen({ navigation }: CameraScreenProps) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  // ── Quyền camera ──
  const [permission, requestPermission, getPermission] = useCameraPermissions();

  const [camState, setCamState] = useState<CamState>('ready');
  const [torchOn, setTorchOn] = useState(false);
  const [capturedUri, setCapturedUri] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>(strings.camera.failHint);
  // Chiều cao thực tế của thanh/panel dưới (đo bằng onLayout) để khung ngắm
  // không chồng lên trên máy thấp hoặc khi chữ hệ thống phóng to.
  const [bottomOverlayHeight, setBottomOverlayHeight] = useState(0);

  const runOcrOnly = useTranslationStore((st) => st.runOcrOnly);
  const requestAutoTranslate = useTranslationStore((st) => st.requestAutoTranslate);
  // Ngôn ngữ NGUỒN hiện tại. OCR KHÔNG tự đổi nguồn theo kết quả nhận dạng
  // (detect_language của backend dễ nhầm) — chỉ giữ nguyên lựa chọn của người dùng.
  const inputLanguage = useTranslationStore((st) => st.inputLanguage);

  const cameraRef = useRef<CameraView | null>(null);
  const capturingRef = useRef(false);
  // Phiên OCR: tăng mỗi lần bắt đầu/chụp lại/huỷ để bỏ kết quả về muộn.
  const ocrSessionRef = useRef(0);
  // Ngôn ngữ dùng cho phiên OCR hiện tại — để bỏ kết quả nếu nguồn đổi giữa chừng.
  const ocrLanguageRef = useRef(inputLanguage);
  // Cờ mounted để không set state / điều hướng sau khi màn đã đóng.
  const mountedRef = useRef(true);

  // Giữ tham chiếu mới nhất của getPermission để listener không cần re-subscribe.
  const getPermissionRef = useRef(getPermission);
  useEffect(() => {
    getPermissionRef.current = getPermission;
  }, [getPermission]);

  // ── Tắt đèn pin helper ──
  const turnOffTorch = useCallback(() => setTorchOn(false), []);

  // ── Trạng thái hiển thị ──
  // Chưa xác định quyền (permission === null): coi như đang chờ, chưa hiện noPermission.
  const showNoPermission = permission !== null && !permission.granted;
  const isCameraState = !showNoPermission;

  const statusBarStyle = isCameraState ? 'light' : 'auto';

  // ── Xin quyền khi mount (chỉ tự động hỏi 1 lần) ──
  const didAutoRequestRef = useRef(false);
  useEffect(() => {
    if (permission === null) return; // đang tải
    if (didAutoRequestRef.current) return;
    if (!permission.granted && permission.canAskAgain) {
      didAutoRequestRef.current = true;
      void requestPermission();
    }
  }, [permission, requestPermission]);

  // ── Khi quay lại app từ Cài đặt: kiểm tra lại quyền ──
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        void getPermissionRef.current?.();
      }
    });
    return () => sub.remove();
  }, []);

  // ── Dọn dẹp: tắt đèn, không giữ ref camera, đánh dấu đã unmount ──
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      ocrSessionRef.current += 1; // bỏ mọi kết quả OCR đang chờ
      turnOffTorch();
      cameraRef.current = null;
    };
  }, [turnOffTorch]);

  // Khi rời khỏi trạng thái camera (noPermission) → tắt đèn
  useEffect(() => {
    if (!isCameraState && torchOn) turnOffTorch();
  }, [isCameraState, torchOn, turnOffTorch]);

  // ── Nguồn đổi trong lúc đang OCR → bỏ kết quả cũ (huỷ phiên hiện tại) ──
  useEffect(() => {
    if (ocrLanguageRef.current === inputLanguage) return;
    ocrLanguageRef.current = inputLanguage;
    if (camState === 'processing') {
      ocrSessionRef.current += 1; // bỏ kết quả OCR đang chờ
      setCapturedUri(null);
      setErrorMessage(strings.camera.failHint);
      setCamState('ready');
    }
  }, [inputLanguage, camState]);

  // ── Nhận ảnh (chụp/thư viện) → chạy OCR ──
  const handleImagePicked = useCallback(
    (uri: string) => {
      const session = ocrSessionRef.current + 1;
      ocrSessionRef.current = session;
      // Ghi nhớ ngôn ngữ nguồn của phiên này để bỏ kết quả nếu người dùng đổi.
      ocrLanguageRef.current = inputLanguage;

      setCapturedUri(uri);
      setErrorMessage(strings.camera.failHint);
      setCamState('processing');
      turnOffTorch();

      void (async () => {
        try {
          const text = await runOcrOnly(uri);
          if (!mountedRef.current || session !== ocrSessionRef.current) return;
          if (text.length >= 1) {
            requestAutoTranslate(text);
            navigation.goBack();
            return;
          }
          // Chữ rỗng → lỗi "không nhận dạng được".
          setErrorMessage(strings.camera.failHint);
          setCamState('error');
        } catch (e) {
          if (!mountedRef.current || session !== ocrSessionRef.current) return;
          setErrorMessage(
            isNetworkError(e) ? strings.error.network : strings.camera.failHint,
          );
          setCamState('error');
        }
      })();
    },
    [runOcrOnly, requestAutoTranslate, navigation, turnOffTorch, inputLanguage],
  );

  // ── Nút "Chụp lại": quay lại xem trước ──
  const handleRetake = useCallback(() => {
    ocrSessionRef.current += 1; // bỏ kết quả OCR đang chờ
    setCapturedUri(null);
    setErrorMessage(strings.camera.failHint);
    setCamState('ready');
  }, []);

  // ── Nút chụp ──
  const handleCapture = useCallback(async () => {
    if (capturingRef.current) return; // chống bấm nhiều lần
    if (!cameraRef.current) return;
    capturingRef.current = true;
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.8,
        skipProcessing: false,
      });
      if (photo?.uri) {
        handleImagePicked(photo.uri);
      }
    } catch {
      // Bỏ qua lỗi chụp.
    } finally {
      capturingRef.current = false;
    }
  }, [handleImagePicked]);

  // ── Nút thư viện ──
  const handlePickFromLibrary = useCallback(async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
      });
      if (result.canceled) return;
      const uri = result.assets[0]?.uri;
      if (uri) handleImagePicked(uri);
    } catch {
      // Bỏ qua lỗi chọn ảnh.
    }
  }, [handleImagePicked]);

  // ── Nút đóng: huỷ phiên hiện tại rồi quay lại ──
  const handleClose = useCallback(() => {
    ocrSessionRef.current += 1; // bỏ kết quả OCR của phiên này
    turnOffTorch();
    navigation.goBack();
  }, [turnOffTorch, navigation]);

  // ── noPermission: mở Cài đặt ──
  const handleOpenSettings = useCallback(() => {
    void Linking.openSettings();
  }, []);

  // ── Đo chiều cao thanh/panel dưới để khung ngắm bám theo ──
  const handleBottomOverlayLayout = useCallback(
    (e: LayoutChangeEvent) => {
      setBottomOverlayHeight(e.nativeEvent.layout.height);
    },
    [],
  );

  // Mép dưới khung ngắm: giữ khoảng cách thiết kế (vs + inset) làm mức tối
  // thiểu, chỉ nâng lên khi thanh/panel dưới thực tế cao hơn (máy thấp, chữ
  // hệ thống phóng to) để khung không chồng lên nội dung. Kẹp lại để khung
  // luôn còn chiều cao dương trên màn rất thấp.
  const designFrameBottom = vs(FRAME_BOTTOM[camState]) + insets.bottom;
  const maxFrameBottom = Math.max(
    SCREEN_HEIGHT - (vs(93) + insets.top) - vs(60),
    designFrameBottom,
  );
  const frameBottom = Math.min(
    Math.max(designFrameBottom, bottomOverlayHeight),
    maxFrameBottom,
  );

  return (
    <View style={styles.root}>
      <StatusBar style={statusBarStyle} />

      {isCameraState ? (
        /* ═══════════ TRẠNG THÁI CAMERA (ready / processing / error) ═══════════ */
        <>
          {/* Nền xem trước: ảnh đã chụp (processing/error) hoặc camera (ready) */}
          <View style={[StyleSheet.absoluteFill, { backgroundColor: cameraColors.background }]}>
            {capturedUri !== null ? (
              <>
                <Image
                  source={{ uri: capturedUri }}
                  style={StyleSheet.absoluteFill}
                  resizeMode="cover"
                />
                {/* Lớp phủ đen mờ 40% */}
                <View style={[StyleSheet.absoluteFill, styles.dimOverlay]} />
              </>
            ) : (
              <CameraView
                ref={cameraRef}
                style={StyleSheet.absoluteFill}
                facing="back"
                enableTorch={torchOn}
              />
            )}
          </View>

          {/* Khung ngắm — bám theo thanh/panel dưới đo được để không chồng lên */}
          <CornerFrame
            color={FRAME_COLOR[camState]}
            top={93}
            topExtra={insets.top}
            bottomOverride={frameBottom}
          />

          {/* Nút đóng — góc trên-trái */}
          <View style={[styles.closeButtonWrap, { top: insets.top + vs(12) }]}>
            <IconCircleButton
              icon="close"
              size="small"
              variant="cameraClose"
              accessibilityLabel={strings.accessibility.close}
              onPress={handleClose}
            />
          </View>

          {/* Viên thuốc gợi ý — giữa phía trên */}
          <View style={[styles.pillWrap, { top: insets.top + vs(16) }]} pointerEvents="none">
            <View style={[styles.pill, { backgroundColor: cameraColors.pill }]}>
              <ThemedText style={styles.pillText}>{strings.camera.pill}</ThemedText>
            </View>
          </View>

          {/* Thanh dưới */}
          {camState === 'ready' && (
            <View
              onLayout={handleBottomOverlayLayout}
              style={[
                styles.bottomBar,
                styles.readyRow,
                {
                  height: vs(140) + insets.bottom,
                  paddingBottom: insets.bottom,
                  backgroundColor: cameraColors.bottomBar,
                },
              ]}
            >
              <IconCircleButton
                icon="image-outline"
                size="large"
                variant="cameraDark"
                accessibilityLabel={strings.accessibility.gallery}
                onPress={handlePickFromLibrary}
              />

              {/* Nút chụp */}
              <Pressable
                onPress={handleCapture}
                accessibilityRole="button"
                accessibilityLabel={strings.accessibility.shutter}
                style={({ pressed }) => [
                  styles.shutterOuter,
                  { opacity: pressed ? 0.85 : 1 },
                ]}
              >
                <View style={[styles.shutterInner, { backgroundColor: colors.primary }]} />
              </Pressable>

              <IconCircleButton
                icon={torchOn ? 'flashlight' : 'flashlight-outline'}
                size="large"
                variant="cameraDark"
                accessibilityLabel={strings.accessibility.torch}
                onPress={() => setTorchOn((prev) => !prev)}
              />
            </View>
          )}

          {camState === 'processing' && (
            <View
              onLayout={handleBottomOverlayLayout}
              style={[
                styles.bottomBar,
                styles.processingRow,
                {
                  minHeight: vs(104) + insets.bottom,
                  paddingBottom: insets.bottom,
                  backgroundColor: cameraColors.bottomBar,
                },
              ]}
            >
              <ActivityIndicator size={s(28)} color={cameraColors.text} />
              <ThemedText
                style={[
                  styles.processingLabel,
                  { marginLeft: s(14), flexShrink: 1 },
                ]}
              >
                {strings.camera.recognizing}
              </ThemedText>
              <ThemedText
                style={[
                  styles.processingHint,
                  { marginLeft: s(10), color: cameraColors.hintText, flexShrink: 1 },
                ]}
              >
                {strings.camera.recognizingHint}
              </ThemedText>
            </View>
          )}

          {camState === 'error' && (
            <View
              onLayout={handleBottomOverlayLayout}
              style={[
                styles.errorPanel,
                {
                  paddingBottom: s(21) + insets.bottom,
                  backgroundColor: cameraColors.bottomBar,
                },
              ]}
            >
              <View style={styles.errorHeader}>
                <Ionicons
                  name="alert-circle-outline"
                  size={ms(24)}
                  color={cameraColors.frameRed}
                  style={styles.errorIcon}
                />
                <View style={styles.errorTextCol}>
                  <ThemedText style={[styles.errorTitle, { color: cameraColors.text }]}>
                    {strings.camera.failTitle}
                  </ThemedText>
                  <ThemedText
                    style={[styles.errorBody, { color: cameraColors.descText, marginTop: vs(4) }]}
                  >
                    {errorMessage}
                  </ThemedText>
                </View>
              </View>

              <View style={{ marginTop: vs(14) }}>
                <OutlineButton
                  label={strings.camera.retake}
                  iconLeft="refresh"
                  tone="dark"
                  onPress={handleRetake}
                />
              </View>
            </View>
          )}
        </>
      ) : (
        /* ═══════════ TRẠNG THÁI noPermission ═══════════ */
        <View style={[styles.permissionSafe, { backgroundColor: colors.background }]}>
          {/* Nút đóng — góc trên-phải */}
          <View style={[styles.permissionCloseRow, { paddingTop: insets.top + vs(8) }]}>
            <IconCircleButton
              icon="close"
              size="small"
              variant="neutral"
              accessibilityLabel={strings.accessibility.close}
              onPress={handleClose}
            />
          </View>

          {/* Khối giữa màn */}
          <View style={styles.permissionBody}>
            <View style={[styles.permissionIconCircle, { backgroundColor: colors.primarySoft }]}>
              <Ionicons name="camera-outline" size={ms(32)} color={colors.primary} />
            </View>

            <ThemedText
              style={[styles.permissionTitle, { color: colors.textPrimary, marginTop: vs(18) }]}
            >
              {strings.camera.permissionTitle}
            </ThemedText>

            <ThemedText
              style={[styles.permissionDescription, { color: colors.textSecondary, marginTop: vs(12) }]}
            >
              {strings.camera.permissionBody}
            </ThemedText>
          </View>

          {/* Hai nút dưới cùng */}
          <View style={[styles.permissionActions, { paddingBottom: vs(30) + insets.bottom }]}>
            <PrimaryButton
              label={strings.camera.openSettings}
              onPress={handleOpenSettings}
            />
            <View style={{ height: vs(14) }} />
            <OutlineButton
              label={strings.camera.typeInstead}
              size="lg"
              onPress={handleClose}
            />
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: cameraColors.background,
  },

  // ── Camera: nút đóng + viên thuốc ──
  closeButtonWrap: {
    position: 'absolute',
    left: s(21),
  },
  pillWrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  pill: {
    minHeight: vs(37),
    borderRadius: vs(37) / 2,
    paddingHorizontal: s(26),
    paddingVertical: vs(6),
    alignItems: 'center',
    justifyContent: 'center',
  },
  pillText: {
    color: cameraColors.text,
    fontSize: ms(16),
    fontWeight: '700',
  },

  // ── Thanh dưới ──
  bottomBar: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
  },

  // Ready: 3 phần space-around
  readyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: s(30),
  },

  // Nút chụp
  shutterOuter: {
    width: s(80),
    height: s(80),
    borderRadius: s(80) / 2,
    borderWidth: s(5),
    borderColor: cameraColors.frameWhite,
    alignItems: 'center',
    justifyContent: 'center',
  },
  shutterInner: {
    width: s(70),
    height: s(70),
    borderRadius: s(70) / 2,
  },

  // Processing
  processingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: s(30),
  },
  processingLabel: {
    color: cameraColors.text,
    fontSize: ms(19),
    fontWeight: '700',
  },
  processingHint: {
    fontSize: ms(14),
    fontWeight: '400',
  },

  // Error
  errorPanel: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: s(21),
    paddingTop: s(21),
  },
  errorHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  errorIcon: {
    marginRight: s(12),
    marginTop: vs(2),
  },
  errorTextCol: {
    flex: 1,
  },
  errorTitle: {
    fontSize: ms(17),
    fontWeight: '700',
  },
  errorBody: {
    fontSize: ms(14),
    lineHeight: ms(20),
    fontWeight: '400',
  },

  // ── noPermission ──
  permissionSafe: {
    flex: 1,
  },
  permissionCloseRow: {
    alignItems: 'flex-end',
    paddingHorizontal: s(21),
  },
  permissionBody: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: s(21),
    paddingBottom: vs(120),
  },
  permissionIconCircle: {
    width: s(76),
    height: s(76),
    borderRadius: s(76) / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  permissionTitle: {
    fontSize: ms(23),
    fontWeight: '700',
    textAlign: 'center',
  },
  permissionDescription: {
    fontSize: ms(15),
    lineHeight: ms(22),
    fontWeight: '400',
    textAlign: 'center',
    maxWidth: s(330),
  },
  permissionActions: {
    paddingHorizontal: s(21),
  },

  // ── Lớp phủ đen mờ trên ảnh đã chụp (40%) ──
  dimOverlay: {
    backgroundColor: cameraColors.imageOverlay,
  },
});
