import { create } from "zustand";
import { persist } from "zustand/middleware";

interface FavoritesState {
  ids: number[];
  toggle: (productId: number) => void;
  has: (productId: number) => boolean;
  pruneMissing: (availableProductIds: number[]) => void;
}

export const useFavoritesStore = create<FavoritesState>()(
  persist(
    (set, get) => ({
      ids: [],
      toggle: (productId) =>
        set((state) => ({
          ids: state.ids.includes(productId)
            ? state.ids.filter((id) => id !== productId)
            : [...state.ids, productId],
        })),
      has: (productId) => get().ids.includes(productId),
      pruneMissing: (availableProductIds) =>
        set((state) => ({
          ids: state.ids.filter((id) => availableProductIds.includes(id)),
        })),
    }),
    {
      name: "telegram-store-manager-favorites",
    },
  ),
);
