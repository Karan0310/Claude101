import * as SecureStore from 'expo-secure-store';
import { AppSettings } from '../types';

const SETTINGS_KEY = 'app_settings';

const DEFAULT_SETTINGS: AppSettings = {
  anthropicApiKey: '',
  serpapiKey: '',
  rapidApiKey: '',
  defaultLocation: '',
  maxResults: 10,
  remoteOk: true,
};

export async function saveSettings(settings: AppSettings): Promise<void> {
  await SecureStore.setItemAsync(SETTINGS_KEY, JSON.stringify(settings));
}

export async function loadSettings(): Promise<AppSettings> {
  const stored = await SecureStore.getItemAsync(SETTINGS_KEY);
  if (!stored) return DEFAULT_SETTINGS;
  return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
}

export async function clearSettings(): Promise<void> {
  await SecureStore.deleteItemAsync(SETTINGS_KEY);
}
