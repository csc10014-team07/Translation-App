// Configurable backend API base URL.
// When testing on a physical device, set EXPO_PUBLIC_API_BASE_URL in mobile/.env
// e.g. EXPO_PUBLIC_API_BASE_URL=http://192.168.1.100:8000
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000';
