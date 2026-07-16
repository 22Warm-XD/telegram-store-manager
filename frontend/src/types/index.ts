export type ProductCategory = "SHOES" | "CLOTHING" | "ACCESSORIES";
export type ProductStatus = "ACTIVE" | "SOLD";
export type ContactMethod = "TELEGRAM" | "PHONE" | "WHATSAPP";
export type DeliveryProvider = "CDEK" | "OZON" | "YANDEX";
export type PaymentMethod = "CARD" | "CRYPTO" | "PHONE_NUMBER";
export type CryptoNetwork = "BEP20" | "TRC20" | "TON";

export interface Category {
  key: ProductCategory;
  label: string;
}

export interface Product {
  id: number;
  title: string;
  price: number;
  old_price: number | null;
  category: ProductCategory;
  category_label: string;
  size: string;
  condition: string;
  description: string | null;
  status: ProductStatus;
  status_label: string;
  photos: string[];
  photo_count: number;
  created_at: string;
  is_new: boolean;
}

export interface StoreMeta {
  shop_name: string;
  support_url: string;
  reviews_url: string;
  tiktok_url: string;
  mini_app_url: string | null;
  background_color: string;
  avatar_url: string | null;
  cover_url: string | null;
  payment_options: {
    card_available: boolean;
    card_number: string | null;
    card_holder: string | null;
    phone_available: boolean;
    phone_number: string | null;
    phone_holder: string | null;
    crypto_networks: Partial<Record<CryptoNetwork, string>>;
  };
}

export interface WebAppUser {
  id: number;
  first_name: string | null;
  username: string | null;
  last_name: string | null;
}

export interface CartEntry {
  productId: number;
  quantity: number;
}

export interface OrderItemPayload {
  product_id: number;
  quantity: number;
}

export interface OrderPayload {
  init_data: string | null;
  name: string;
  username: string;
  phone: string | null;
  comment: string;
  contact_method: ContactMethod;
  delivery_provider: DeliveryProvider;
  delivery_address: string;
  payment_method: PaymentMethod;
  crypto_network: CryptoNetwork | null;
  items: OrderItemPayload[];
}

export interface OrderResponse {
  ok: boolean;
  order_id: number;
  total_amount: number;
  message: string;
}
