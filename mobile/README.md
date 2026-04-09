# Resume Job Matcher — Mobile App

React Native (Expo) mobile app for iOS and Android. Upload your resume, configure API keys in Settings, and get AI-powered job recommendations with fit scores.

## Quick Start

### Prerequisites
- Node.js 18+
- Expo CLI: `npm install -g expo-cli`
- Expo Go app on your phone ([iOS](https://apps.apple.com/app/expo-go/id982107779) / [Android](https://play.google.com/store/apps/details?id=host.exp.exponent))

### Run

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with Expo Go on your phone.

## API Keys Setup

Open the app → **Settings tab** → enter your keys:

| Key | Where to get | Required? |
|-----|-------------|-----------|
| Anthropic API Key | [console.anthropic.com](https://console.anthropic.com) | Yes |
| SerpAPI Key | [serpapi.com](https://serpapi.com) | No (demo mode) |
| RapidAPI Key | [rapidapi.com](https://rapidapi.com) | No |

Keys are stored **encrypted on your device** using iOS Keychain / Android Keystore. They never leave your phone except to call the respective APIs directly.

## Build for Production

```bash
# Install EAS CLI
npm install -g eas-cli
eas login

# Build for Android (.apk)
eas build --platform android --profile preview

# Build for iOS
eas build --platform ios
```
