import type { Product } from "../types";
import { ProductCard } from "./ProductCard";

interface FavoritesDrawerProps {
  products: Product[];
  favoriteIds: number[];
  cartIds: number[];
  onClose: () => void;
  onOpenProduct: (product: Product) => void;
  onToggleFavorite: (productId: number) => void;
  onAddToCart: (productId: number) => void;
}

export function FavoritesDrawer({
  products,
  favoriteIds,
  cartIds,
  onClose,
  onOpenProduct,
  onToggleFavorite,
  onAddToCart,
}: FavoritesDrawerProps) {
  const favoriteProducts = products.filter((product) => favoriteIds.includes(product.id));

  return (
    <div className="overlay" role="dialog" aria-modal="true">
      <div className="sheet sheet--favorites">
        <div className="sheet__header">
          <h2>Избранное ({favoriteProducts.length})</h2>
          <button className="text-button" type="button" onClick={onClose}>
            Закрыть
          </button>
        </div>

        {favoriteProducts.length ? (
          <div className="products-grid">
            {favoriteProducts.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                isFavorite
                inCart={cartIds.includes(product.id)}
                onOpen={() => onOpenProduct(product)}
                onToggleFavorite={() => onToggleFavorite(product.id)}
                onAddToCart={() => onAddToCart(product.id)}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>В избранном пока пусто.</p>
            <span>Сохраняйте понравившиеся позиции сердцем на карточке товара.</span>
          </div>
        )}
      </div>
    </div>
  );
}
