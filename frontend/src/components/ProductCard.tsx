import type { Product } from "../types";
import { formatPrice } from "../utils/format";

interface ProductCardProps {
  product: Product;
  isFavorite: boolean;
  inCart: boolean;
  onOpen: () => void;
  onToggleFavorite: () => void;
  onAddToCart: () => void;
}

export function ProductCard({
  product,
  isFavorite,
  inCart,
  onOpen,
  onToggleFavorite,
  onAddToCart,
}: ProductCardProps) {
  return (
    <article className="product-card" onClick={onOpen}>
      <div className="product-card__media">
        {product.photos[0] ? (
          <img className="product-card__image" src={product.photos[0]} alt={product.title} loading="lazy" />
        ) : (
          <div className="product-card__placeholder">STORE</div>
        )}

        {product.is_new ? <span className="badge badge--new">NEW</span> : null}
        {product.photo_count > 1 ? <span className="badge badge--count">1 / {product.photo_count}</span> : null}
        {product.status === "SOLD" ? <span className="badge badge--sold">Продано</span> : null}
      </div>

      <div className="product-card__body">
        <h3 className="product-card__title">{product.title}</h3>
        <p className="product-card__info">
          {product.category_label} · размер {product.size}
        </p>
        <p className="product-card__condition">{product.condition}</p>
        <div className="product-card__price">
          {product.old_price ? <span className="price-old">{formatPrice(product.old_price)}</span> : null}
          <strong>{formatPrice(product.price)}</strong>
        </div>
        <div className="product-card__meta">1 шт.</div>

        <div className="product-card__actions">
          <button
            className={`action-button action-button--cart ${inCart ? "action-button--active" : ""}`}
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onAddToCart();
            }}
            disabled={product.status === "SOLD"}
          >
            {product.status === "SOLD" ? "Продано" : inCart ? "В корзине" : "В корзину"}
          </button>
          <button
            className={`action-button action-button--favorite ${isFavorite ? "action-button--favorite-active" : ""}`}
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onToggleFavorite();
            }}
            aria-label="Добавить в избранное"
          >
            {isFavorite ? "♥" : "♡"}
          </button>
        </div>
      </div>
    </article>
  );
}
