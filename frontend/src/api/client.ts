import type { Category, OrderPayload, OrderResponse, Product, StoreMeta, WebAppUser } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });

  if (!response.ok) {
    let errorMessage = "Ошибка запроса.";
    try {
      const payload = (await response.json()) as { detail?: string };
      errorMessage = payload.detail || errorMessage;
    } catch {
      errorMessage = response.statusText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return (await response.json()) as T;
}

export function fetchMeta() {
  return request<StoreMeta>("/meta");
}

export function fetchCategories() {
  return request<Category[]>("/categories");
}

export function fetchProducts() {
  return request<Product[]>("/products");
}

export function fetchProduct(productId: number) {
  return request<Product>(`/products/${productId}`);
}

export async function validateWebApp(initData: string) {
  return request<{ ok: boolean; user: WebAppUser }>("/webapp/validate", {
    method: "POST",
    body: JSON.stringify({ init_data: initData }),
  });
}

export function createOrder(payload: OrderPayload) {
  return request<OrderResponse>("/orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
