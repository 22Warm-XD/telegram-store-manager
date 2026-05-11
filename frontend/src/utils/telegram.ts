export function getTelegramWebApp() {
  return window.Telegram?.WebApp;
}

export function initializeTelegramWebApp() {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    return;
  }
  webApp.ready();
  webApp.expand();
  webApp.setHeaderColor?.("#140a1f");
  webApp.setBackgroundColor?.("#120916");
  webApp.disableVerticalSwipes?.();
}

export function getInitData(): string {
  return getTelegramWebApp()?.initData ?? "";
}
