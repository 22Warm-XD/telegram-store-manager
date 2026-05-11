import type { StoreMeta } from "../types";

interface HeaderBannerProps {
  meta: StoreMeta | null;
  favoritesCount: number;
  onOpenFavorites: () => void;
}

export function HeaderBanner({ meta, favoritesCount, onOpenFavorites }: HeaderBannerProps) {
  const shopName = meta?.shop_name || "Demo Store";

  return (
    <header className="hero-shell">
      <div className="topbar">
        <div>
          <div className="topbar__eyebrow">TELEGRAM MINI APP</div>
          <h1 className="topbar__title">{shopName}</h1>
          <p className="topbar__subtitle">Catalog of available products, discounts, and featured items.</p>
        </div>
        <button className="icon-button" type="button" onClick={onOpenFavorites} aria-label="Open favorites">
          <span>♡</span>
          {favoritesCount > 0 ? <span className="icon-badge">{favoritesCount}</span> : null}
        </button>
      </div>

      <div className="hero-card">
        <div className="hero-card__overlay" />
        <div className="hero-card__content">
          <div className="hero-card__avatar-wrap">
            <div className="hero-card__avatar hero-card__avatar--text">TSM</div>
          </div>
          <div className="hero-card__copyblock">
            <p className="hero-card__label">Premium storefront catalog</p>
            <h2 className="hero-card__heading">{shopName}</h2>
            <p className="hero-card__copy">
              A mobile storefront for clothing, shoes, and accessories that are ready to order.
            </p>
            <div className="hero-card__links">
              <a className="hero-card__link" href={meta?.reviews_url || "#"} target="_blank" rel="noreferrer">
                Reviews
              </a>
              <a className="hero-card__link" href={meta?.support_url || "#"} target="_blank" rel="noreferrer">
                Support
              </a>
              <a className="hero-card__link" href={meta?.tiktok_url || "#"} target="_blank" rel="noreferrer">
                TikTok
              </a>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
