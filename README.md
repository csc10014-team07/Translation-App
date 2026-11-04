# Translation-App

## Mobile Configuration

When testing on a physical mobile device, copy `mobile/.env.example` to `mobile/.env` and update `EXPO_PUBLIC_API_BASE_URL` with your server host IP:

```bash
cp mobile/.env.example mobile/.env
```

Whenever environment variables change, restart Expo with clear cache:

```bash
npx expo start -c
```
