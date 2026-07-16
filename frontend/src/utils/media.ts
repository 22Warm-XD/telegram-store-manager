export type MediaVariant = "card" | "detail" | "thumb";

export function mediaUrl(url: string, variant: MediaVariant): string {
  const parsed = new URL(url, window.location.origin);
  parsed.searchParams.set("variant", variant);
  return parsed.pathname + parsed.search;
}
