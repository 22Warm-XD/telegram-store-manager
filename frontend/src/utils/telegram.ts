export function getTelegramWebApp() {
  return window.Telegram?.WebApp;
}

export function initializeTelegramWebApp() {
  const webApp = getTelegramWebApp();
  if (!webApp?.initData) {
    return;
  }
  webApp.ready();
  webApp.expand();
  webApp.setHeaderColor?.("#505559");
  webApp.setBackgroundColor?.("#505559");
}

export function getInitData(): string {
  return getTelegramWebApp()?.initData ?? "";
}
