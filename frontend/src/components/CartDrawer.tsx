import type { CartEntry, Product } from "../types";
import { formatPrice } from "../utils/format";

interface CartDrawerProps {
  items: CartEntry[];
  products: Product[];
  onClose: () => void;
  onCheckout: () => void;
  onIncrement: (productId: number) => void;
  onDecrement: (productId: number) => void;
  onRemove: (productId: number) => void;
}

export function CartDrawer({
  items,
  products,
  onClose,
  onCheckout,
  onIncrement,
  onDecrement,
  onRemove,
}: CartDrawerProps) {
  const productMap = new Map(products.map((product) => [product.id, product]));
  const totalCount = items.reduce((sum, item) => sum + item.quantity, 0);
  const total = items.reduce((sum, item) => {
    const product = productMap.get(item.productId);
    return sum + (product ? product.price * item.quantity : 0);
  }, 0);

  return (
    <div className="overlay" role="dialog" aria-modal="true">
      <div className="sheet sheet--cart">
        <div className="sheet__header">
          <h2>Корзина ({totalCount})</h2>
          <button className="text-button" type="button" onClick={onClose}>
            Закрыть
          </button>
        </div>

        <div className="cart-list">
          {items.length === 0 ? (
            <div className="empty-state">
              <p>Корзина пока пустая.</p>
              <span>Добавьте сюда товары из каталога, и мы быстро соберём заказ.</span>
            </div>
          ) : null}

          {items.map((item) => {
            const product = productMap.get(item.productId);
            if (!product) {
              return null;
            }
            return (
              <article className="cart-item" key={item.productId}>
                {product.photos[0] ? (
                  <img className="cart-item__image" src={product.photos[0]} alt={product.title} />
                ) : (
                  <div className="cart-item__placeholder">ST</div>
                )}
                <div className="cart-item__content">
                  <h3>{product.title}</h3>
                  <div className="cart-item__price">{formatPrice(product.price)}</div>
                  <div className="cart-item__availability">Доступно: 1 шт.</div>
                  <div className="cart-item__controls">
                    <button type="button" onClick={() => onDecrement(product.id)}>
                      −
                    </button>
                    <span>{item.quantity}</span>
                    <button type="button" onClick={() => onIncrement(product.id)} disabled={item.quantity >= 1}>
                      +
                    </button>
                    <button className="cart-item__remove" type="button" onClick={() => onRemove(product.id)}>
                      Удалить
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>

        <div className="sheet__footer">
          <div className="sheet__total">
            <span>Итого</span>
            <strong>{formatPrice(total)}</strong>
          </div>
          <button className="checkout-button" type="button" onClick={onCheckout} disabled={!items.length}>
            Оформить заказ
          </button>
        </div>
      </div>
    </div>
  );
}
