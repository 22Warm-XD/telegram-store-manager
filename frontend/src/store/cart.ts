import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { CartEntry } from "../types";

interface CartState {
  items: CartEntry[];
  addItem: (productId: number) => void;
  increment: (productId: number, maxQuantity?: number) => void;
  decrement: (productId: number) => void;
  removeItem: (productId: number) => void;
  pruneUnavailable: (availableProductIds: number[]) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      addItem: (productId) =>
        set((state) => {
          const existing = state.items.find((item) => item.productId === productId);
          if (existing) {
            return state;
          }
          return { items: [...state.items, { productId, quantity: 1 }] };
        }),
      increment: (productId, maxQuantity = 1) =>
        set((state) => ({
          items: state.items.map((item) =>
            item.productId === productId
              ? { ...item, quantity: Math.min(item.quantity + 1, maxQuantity) }
              : item,
          ),
        })),
      decrement: (productId) =>
        set((state) => ({
          items: state.items
            .map((item) =>
              item.productId === productId
                ? { ...item, quantity: Math.max(item.quantity - 1, 0) }
                : item,
            )
            .filter((item) => item.quantity > 0),
        })),
      removeItem: (productId) =>
        set((state) => ({
          items: state.items.filter((item) => item.productId !== productId),
        })),
      pruneUnavailable: (availableProductIds) =>
        set((state) => ({
          items: state.items.filter((item) => availableProductIds.includes(item.productId)),
        })),
      clearCart: () => set({ items: [] }),
    }),
    {
      name: "telegram-store-manager-cart",
    },
  ),
);
