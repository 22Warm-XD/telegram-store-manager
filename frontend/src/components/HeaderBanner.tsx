import type { StoreMeta } from "../types";
import { HeartIcon } from "./Icons";

interface HeaderBannerProps {
  meta: StoreMeta | null;
  favoritesCount: number;
  onOpenFavorites: () => void;
}

export function HeaderBanner({ meta, favoritesCount, onOpenFavorites }: HeaderBannerProps) {
  const shopName = meta?.shop_name || "Kuznetsky Store";

  return (
    <header className="store-header">
      <div
        className={`store-cover ${meta?.cover_url ? "store-cover--image" : ""}`}
        style={meta?.cover_url ? { backgroundImage: `url("${meta.cover_url}")` } : undefined}
      >
        <div className="store-cover__shade" />
        <div className="store-cover__wordmark">KUZNETSKY</div>
        <button className="icon-button store-cover__favorite" type="button" onClick={onOpenFavorites} aria-label="Открыть избранное">
          <HeartIcon />
          {favoritesCount > 0 ? <span className="icon-badge">{favoritesCount}</span> : null}
        </button>
      </div>
      <div className="store-profile">
        <img className="store-profile__avatar" src={meta?.avatar_url || "/kuznetsky-avatar.jpg"} alt={shopName} decoding="async" onError={(event) => { event.currentTarget.style.visibility = "hidden"; }} />
        <div className="store-profile__content">
          <p className="store-profile__label">Оригинальные позиции</p>
          <h1>{shopName}</h1>
          <p>Личная встреча в Стерлитамаке. Отправка через Авито, СДЭК, Яндекс и Почту России.</p>
          <div className="hero-card__links">
              <a className="hero-card__link" href={meta?.reviews_url || "#"} target="_blank" rel="noreferrer">
                Отзывы
              </a>
              <a className="hero-card__link" href={meta?.support_url || "#"} target="_blank" rel="noreferrer">
                Связь
              </a>
              <a className="hero-card__link" href={meta?.tiktok_url || "#"} target="_blank" rel="noreferrer">
                TikTok
              </a>
          </div>
        </div>
      </div>
    </header>
  );
}
