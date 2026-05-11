import { useEffect, useMemo, useRef, useState } from "react";

import { createOrder, fetchCategories, fetchMeta, fetchProducts, validateWebApp } from "../api/client";
import { CartDrawer } from "../components/CartDrawer";
import { CheckoutSheet } from "../components/CheckoutSheet";
import { FavoritesDrawer } from "../components/FavoritesDrawer";
import { HeaderBanner } from "../components/HeaderBanner";
import { ProductCard } from "../components/ProductCard";
import { ProductModal } from "../components/ProductModal";
import { useCartStore } from "../store/cart";
import { useFavoritesStore } from "../store/favorites";
import type { Category, Product, StoreMeta, WebAppUser } from "../types";
import { getInitData, initializeTelegramWebApp } from "../utils/telegram";

type SortMode = "default" | "cheap" | "expensive" | "new" | "discount";

const categoryVisuals: Record<string, { title: string; subtitle: string }> = {
  SHOES: { title: "Обувь", subtitle: "Кроссовки, лоферы, boots" },
  CLOTHING: { title: "Одежда", subtitle: "Худи, куртки, футболки" },
  ACCESSORIES: { title: "Аксессуары", subtitle: "Сумки, ремни, мелкие детали" },
};

const sortOptions: Array<{ value: SortMode; label: string }> = [
  { value: "default", label: "По умолчанию" },
  { value: "cheap", label: "Сначала дешевле" },
  { value: "expensive", label: "Сначала дороже" },
  { value: "new", label: "Новые" },
  { value: "discount", label: "Со скидкой" },
];

export function StorePage() {
  const [meta, setMeta] = useState<StoreMeta | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [sortMode, setSortMode] = useState<SortMode>("default");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [showCart, setShowCart] = useState(false);
  const [showCheckout, setShowCheckout] = useState(false);
  const [showFavorites, setShowFavorites] = useState(false);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [webAppUser, setWebAppUser] = useState<WebAppUser | null>(null);
  const categoryScrollerRef = useRef<HTMLDivElement | null>(null);

  const cartItems = useCartStore((state) => state.items);
  const addItem = useCartStore((state) => state.addItem);
  const increment = useCartStore((state) => state.increment);
  const decrement = useCartStore((state) => state.decrement);
  const removeItem = useCartStore((state) => state.removeItem);
  const clearCart = useCartStore((state) => state.clearCart);
  const pruneCart = useCartStore((state) => state.pruneUnavailable);

  const favoriteIds = useFavoritesStore((state) => state.ids);
  const toggleFavorite = useFavoritesStore((state) => state.toggle);
  const hasFavorite = useFavoritesStore((state) => state.has);
  const pruneFavorites = useFavoritesStore((state) => state.pruneMissing);

  useEffect(() => {
    initializeTelegramWebApp();
    void loadData();
    void tryValidateTelegram();
  }, []);

  useEffect(() => {
    if (loading) {
      return;
    }
    const availableIds = products.map((product) => product.id);
    pruneCart(availableIds);
    pruneFavorites(availableIds);
    if (selectedProduct && !availableIds.includes(selectedProduct.id)) {
      setSelectedProduct(null);
    }
  }, [loading, products, pruneCart, pruneFavorites, selectedProduct]);

  async function loadData() {
    try {
      setLoading(true);
      const [metaData, categoryData, productData] = await Promise.all([fetchMeta(), fetchCategories(), fetchProducts()]);
      setMeta(metaData);
      setCategories(categoryData);
      setProducts(productData);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Не удалось загрузить каталог.");
    } finally {
      setLoading(false);
    }
  }

  async function tryValidateTelegram() {
    const initData = getInitData();
    if (!initData) {
      return;
    }
    try {
      const response = await validateWebApp(initData);
      setWebAppUser(response.user);
    } catch {
      setWebAppUser(null);
    }
  }

  const filteredProducts = useMemo(
    () =>
      products
        .filter((product) => {
          if (selectedCategory !== "ALL" && product.category !== selectedCategory) {
            return false;
          }
          if (!search.trim()) {
            return true;
          }
          const needle = search.trim().toLowerCase();
          return [product.title, product.description || "", product.category_label].join(" ").toLowerCase().includes(needle);
        })
        .sort((left, right) => {
          switch (sortMode) {
            case "cheap":
              return left.price - right.price;
            case "expensive":
              return right.price - left.price;
            case "new":
              return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
            case "discount":
              return Number(Boolean(right.old_price)) - Number(Boolean(left.old_price));
            default:
              return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
          }
        }),
    [products, search, selectedCategory, sortMode],
  );

  const activeCategoryLabel =
    selectedCategory === "ALL"
      ? "Все товары"
      : categories.find((category) => category.key === selectedCategory)?.label || "Категория";

  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);

  async function handleCheckoutSubmit(payload: {
    name: string;
    username: string;
    phone: string;
    comment: string;
  }) {
    const initData = getInitData();
    setCheckoutLoading(true);
    setCheckoutError(null);
    try {
      const response = await createOrder({
        init_data: initData || null,
        name: payload.name,
        username: payload.username,
        phone: payload.phone.trim() ? payload.phone.trim() : null,
        comment: payload.comment,
        contact_method: "TELEGRAM",
        items: cartItems.map((item) => ({
          product_id: item.productId,
          quantity: item.quantity,
        })),
      });
      clearCart();
      setShowCheckout(false);
      setShowCart(false);
      setSuccessMessage(response.message);
    } catch (submitError) {
      setCheckoutError(submitError instanceof Error ? submitError.message : "Не удалось создать заказ.");
    } finally {
      setCheckoutLoading(false);
    }
  }

  function scrollCategories(direction: -1 | 1) {
    categoryScrollerRef.current?.scrollBy({
      left: direction * 260,
      behavior: "smooth",
    });
  }

  return (
    <div className="app-shell">
      <div className="page-container">
        <HeaderBanner meta={meta} favoritesCount={favoriteIds.length} onOpenFavorites={() => setShowFavorites(true)} />

        <section className="search-section">
          <label className="search-input">
            <span className="search-input__icon">⌕</span>
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Поиск товаров..." />
          </label>
        </section>

        <section className="category-section">
          <div className="section-heading">
            <h2>Категории</h2>
            <span>{categories.length} раздела</span>
          </div>

          <div className="category-carousel">
            <button className="category-nav category-nav--prev" type="button" onClick={() => scrollCategories(-1)} aria-label="Прокрутить категории влево">
              ‹
            </button>

            <div className="category-scroller" ref={categoryScrollerRef}>
              <button
                className={`category-card ${selectedCategory === "ALL" ? "category-card--active" : ""}`}
                type="button"
                onClick={() => setSelectedCategory("ALL")}
              >
                <span>Все товары</span>
                <small>Full Demo Store catalog</small>
              </button>
              {categories.map((category) => (
                <button
                  key={category.key}
                  className={`category-card ${selectedCategory === category.key ? "category-card--active" : ""}`}
                  type="button"
                  onClick={() => setSelectedCategory(category.key)}
                >
                  <span>{categoryVisuals[category.key]?.title || category.label}</span>
                  <small>{categoryVisuals[category.key]?.subtitle || category.label}</small>
                </button>
              ))}
            </div>

            <button className="category-nav category-nav--next" type="button" onClick={() => scrollCategories(1)} aria-label="Прокрутить категории вправо">
              ›
            </button>
          </div>
        </section>

        <section className="products-section">
          <div className="products-toolbar">
            <div>
              <h2>{activeCategoryLabel}</h2>
              <span>{filteredProducts.length} товаров</span>
            </div>

            <div className="sort-panel">
              <span className="sort-panel__label">Сортировка</span>
              <div className="sort-chip-row">
                {sortOptions.map((option) => (
                  <button
                    key={option.value}
                    className={`sort-chip ${sortMode === option.value ? "sort-chip--active" : ""}`}
                    type="button"
                    onClick={() => setSortMode(option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {webAppUser ? <div className="welcome-note">Привет, {webAppUser.first_name || webAppUser.username || "друг"}.</div> : null}

          {error ? <div className="form-error form-error--page">{error}</div> : null}

          {loading ? (
            <div className="products-grid">
              {Array.from({ length: 8 }).map((_, index) => (
                <div className="product-skeleton" key={index} />
              ))}
            </div>
          ) : null}

          {!loading && !filteredProducts.length ? (
            <div className="empty-state">
              <p>Ничего не найдено.</p>
              <span>Попробуйте поменять категорию или уточнить поисковый запрос.</span>
            </div>
          ) : null}

          {!loading && filteredProducts.length ? (
            <div className="products-grid">
              {filteredProducts.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  isFavorite={hasFavorite(product.id)}
                  inCart={cartItems.some((item) => item.productId === product.id)}
                  onOpen={() => setSelectedProduct(product)}
                  onToggleFavorite={() => toggleFavorite(product.id)}
                  onAddToCart={() => {
                    if (product.status === "ACTIVE") {
                      addItem(product.id);
                    }
                  }}
                />
              ))}
            </div>
          ) : null}
        </section>
      </div>

      <button className="cart-fab" type="button" onClick={() => setShowCart(true)}>
        <span>🛒</span>
        {cartCount ? <strong>{cartCount}</strong> : null}
      </button>

      {selectedProduct ? (
        <ProductModal
          key={selectedProduct.id}
          product={selectedProduct}
          supportUrl={meta?.support_url || "#"}
          isFavorite={hasFavorite(selectedProduct.id)}
          inCart={cartItems.some((item) => item.productId === selectedProduct.id)}
          onClose={() => setSelectedProduct(null)}
          onToggleFavorite={() => toggleFavorite(selectedProduct.id)}
          onAddToCart={() => {
            if (selectedProduct.status === "ACTIVE") {
              addItem(selectedProduct.id);
            }
          }}
        />
      ) : null}

      {showCart ? (
        <CartDrawer
          items={cartItems}
          products={products}
          onClose={() => setShowCart(false)}
          onCheckout={() => setShowCheckout(true)}
          onIncrement={(productId) => increment(productId, 1)}
          onDecrement={decrement}
          onRemove={removeItem}
        />
      ) : null}

      {showFavorites ? (
        <FavoritesDrawer
          products={products}
          favoriteIds={favoriteIds}
          cartIds={cartItems.map((item) => item.productId)}
          onClose={() => setShowFavorites(false)}
          onOpenProduct={(product) => {
            setShowFavorites(false);
            setSelectedProduct(product);
          }}
          onToggleFavorite={toggleFavorite}
          onAddToCart={(productId) => addItem(productId)}
        />
      ) : null}

      {showCheckout ? (
        <CheckoutSheet
          loading={checkoutLoading}
          error={checkoutError}
          initialName={webAppUser?.first_name ?? ""}
          initialUsername={webAppUser?.username ? `@${webAppUser.username}` : ""}
          onClose={() => setShowCheckout(false)}
          onSubmit={handleCheckoutSubmit}
        />
      ) : null}

      {successMessage ? (
        <div className="overlay" role="dialog" aria-modal="true">
          <div className="sheet sheet--success">
            <div className="success-mark">✓</div>
            <h2>Заказ создан</h2>
            <p>{successMessage}</p>
            <p className="success-subtitle">Админ уже получил уведомление в Telegram.</p>
            <button className="checkout-button checkout-button--success" type="button" onClick={() => setSuccessMessage(null)}>
              Вернуться в каталог
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
