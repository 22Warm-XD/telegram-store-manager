import { useState } from "react";

import type { Product } from "../types";
import { formatPrice } from "../utils/format";
import { ChevronIcon, CloseIcon, HeartIcon } from "./Icons";

interface ProductModalProps {
  product: Product;
  supportUrl: string;
  isFavorite: boolean;
  inCart: boolean;
  onClose: () => void;
  onToggleFavorite: () => void;
  onAddToCart: () => void;
}

export function ProductModal({
  product,
  supportUrl,
  isFavorite,
  inCart,
  onClose,
  onToggleFavorite,
  onAddToCart,
}: ProductModalProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const photos = product.photos.length ? product.photos : [""];

  return (
    <div className="overlay overlay--product" role="dialog" aria-modal="true">
      <div className="sheet sheet--product">
        <div className="product-modal__toolbar">
          <button className="icon-button" type="button" onClick={onClose} aria-label="Закрыть">
            <CloseIcon />
          </button>
          <button className="icon-button" type="button" onClick={onToggleFavorite} aria-label="Избранное">
            <HeartIcon filled={isFavorite} />
          </button>
        </div>
        <div className="product-modal__layout">
          <div className="product-modal__media-column">
            <div className="product-modal__gallery">
          {photos[currentIndex] ? (
            <img className="product-modal__image" src={photos[currentIndex]} alt={product.title} />
          ) : (
            <div className="product-card__placeholder product-modal__placeholder">STORE</div>
          )}

          {photos.length > 1 ? (
            <>
              <button
                className="carousel-button carousel-button--prev"
                type="button"
                onClick={() => setCurrentIndex((currentIndex - 1 + photos.length) % photos.length)}
                aria-label="Предыдущее фото"
              >
                <ChevronIcon direction="left" />
              </button>
              <button
                className="carousel-button carousel-button--next"
                type="button"
                onClick={() => setCurrentIndex((currentIndex + 1) % photos.length)}
                aria-label="Следующее фото"
              >
                <ChevronIcon direction="right" />
              </button>
              <div className="carousel-indicator">
                {currentIndex + 1} / {photos.length}
              </div>
            </>
          ) : null}
            </div>

            {photos.length > 1 ? (
              <div className="product-modal__thumbs">
            {photos.map((photo, index) => (
              <button
                key={`${photo}-${index}`}
                className={`product-modal__thumb ${index === currentIndex ? "product-modal__thumb--active" : ""}`}
                type="button"
                onClick={() => setCurrentIndex(index)}
                aria-label={`Фото ${index + 1}`}
              >
                <img src={photo} alt={`${product.title} ${index + 1}`} />
              </button>
            ))}
              </div>
            ) : null}
          </div>

          <div className="product-modal__content">
          <div className="product-modal__status">{product.status_label}</div>
          <h2 className="product-modal__title">{product.title}</h2>
          <div className="product-modal__price">
            {product.old_price ? <span className="price-old">{formatPrice(product.old_price)}</span> : null}
            <strong>{formatPrice(product.price)}</strong>
          </div>

          <dl className="product-modal__details">
            <div>
              <dt>Размер</dt>
              <dd>{product.size}</dd>
            </div>
            <div>
              <dt>Состояние</dt>
              <dd>{product.condition}</dd>
            </div>
            <div>
              <dt>Категория</dt>
              <dd>{product.category_label}</dd>
            </div>
            <div>
              <dt>Описание</dt>
              <dd>{product.description || "Менеджер добавит подробности по запросу."}</dd>
            </div>
          </dl>

          <div className="product-modal__actions">
            <button className="primary-button" type="button" onClick={onAddToCart} disabled={product.status === "SOLD"}>
              {product.status === "SOLD" ? "Продано" : inCart ? "Уже в корзине" : "Добавить в корзину"}
            </button>
            <a className="secondary-button" href={supportUrl} target="_blank" rel="noreferrer">
              Написать менеджеру
            </a>
          </div>
        </div>
      </div>
    </div>
    </div>
  );
}
