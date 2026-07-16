import { useState } from "react";

import type { CryptoNetwork, DeliveryProvider, PaymentMethod, StoreMeta } from "../types";

interface CheckoutSheetProps {
  loading: boolean;
  error: string | null;
  meta: StoreMeta | null;
  metaLoading: boolean;
  metaError: string | null;
  initialName?: string;
  initialUsername?: string;
  onClose: () => void;
  onSubmit: (payload: { name: string; username: string; phone: string; comment: string; deliveryProvider: DeliveryProvider; deliveryAddress: string; paymentMethod: PaymentMethod; cryptoNetwork: CryptoNetwork | null }) => Promise<void>;
}

const deliveryOptions: Array<{ value: DeliveryProvider; label: string }> = [
  { value: "CDEK", label: "СДЭК" }, { value: "OZON", label: "Ozon" }, { value: "YANDEX", label: "Яндекс" },
];

export function CheckoutSheet({ loading, error, meta, metaLoading, metaError, initialName, initialUsername, onClose, onSubmit }: CheckoutSheetProps) {
  const [name, setName] = useState(initialName || "");
  const [username, setUsername] = useState(initialUsername || "");
  const [phone, setPhone] = useState("");
  const [comment, setComment] = useState("");
  const [deliveryProvider, setDeliveryProvider] = useState<DeliveryProvider | null>(null);
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | null>(null);
  const [cryptoNetwork, setCryptoNetwork] = useState<CryptoNetwork | null>(null);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  const cryptoNetworks = meta?.payment_options.crypto_networks || {};
  const hasCryptoNetworks = Object.keys(cryptoNetworks).length > 0;
  const copy = async (value: string) => { await navigator.clipboard.writeText(value); setCopyStatus("Скопировано"); window.setTimeout(() => setCopyStatus(null), 1500); };
  if (metaLoading) {
    return <CheckoutState onClose={onClose} message="Загружаем способы оплаты…" />;
  }
  if (metaError || !meta) {
    return <CheckoutState onClose={onClose} message="Не удалось загрузить способы оплаты. Обновите Mini App" />;
  }
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!deliveryProvider || !deliveryAddress.trim() || !paymentMethod || (paymentMethod === "CRYPTO" && !cryptoNetwork)) return;
    await onSubmit({ name, username, phone, comment, deliveryProvider, deliveryAddress: deliveryAddress.trim(), paymentMethod, cryptoNetwork: paymentMethod === "CRYPTO" ? cryptoNetwork : null });
  };

  return <div className="overlay" role="dialog" aria-modal="true" aria-label="Оформление заказа">
    <div className="sheet sheet--checkout"><div className="sheet__header"><h2>Оформление заказа</h2><button className="text-button" type="button" onClick={onClose}>Закрыть</button></div>
      <form className="checkout-form" onSubmit={submit}>
        <label>Имя<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
        <label>Username в Telegram<input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="@username" required /><small className="field-hint">Укажите @username, чтобы менеджер быстро связался с вами.</small></label>
        <label>Телефон для связи<input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+7 900 000-00-00" inputMode="tel" /><small className="field-hint">Необязательно.</small></label>
        <label>Комментарий<textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Размер, нюансы, удобное время для связи" rows={3} /></label>
        <fieldset className="checkout-choice"><legend>Выберите транспортную компанию</legend><div className="choice-grid">{deliveryOptions.map((option) => <button className={deliveryProvider === option.value ? "choice-card choice-card--active" : "choice-card"} type="button" key={option.value} onClick={() => setDeliveryProvider(option.value)} aria-pressed={deliveryProvider === option.value}>{option.label}</button>)}</div></fieldset>
        <label>Адрес пункта выдачи или доставки<input value={deliveryAddress} onChange={(e) => setDeliveryAddress(e.target.value)} placeholder="Укажите город, улицу и адрес выбранной ТК" maxLength={500} required /></label>
        <fieldset className="checkout-choice"><legend>Выберите способ оплаты</legend><div className="choice-grid">{meta.payment_options.card_available ? <button className={paymentMethod === "CARD" ? "choice-card choice-card--active" : "choice-card"} type="button" onClick={() => setPaymentMethod("CARD")}>Банковская карта</button> : null}{hasCryptoNetworks ? <button className={paymentMethod === "CRYPTO" ? "choice-card choice-card--active" : "choice-card"} type="button" onClick={() => setPaymentMethod("CRYPTO")}>Криптовалюта</button> : null}{meta.payment_options.phone_available ? <button className={paymentMethod === "PHONE_NUMBER" ? "choice-card choice-card--active" : "choice-card"} type="button" onClick={() => setPaymentMethod("PHONE_NUMBER")}>Перевод по номеру</button> : <span className="choice-card choice-card--disabled">Перевод по номеру<br /><small>Временно недоступно</small></span>}</div></fieldset>
        {paymentMethod === "CARD" && meta.payment_options.card_number ? <PaymentDetails label="Номер карты" value={meta.payment_options.card_number} holder={meta.payment_options.card_holder} onCopy={copy} /> : null}
        {paymentMethod === "PHONE_NUMBER" && meta.payment_options.phone_number ? <PaymentDetails label="Номер телефона" value={meta.payment_options.phone_number} holder={meta.payment_options.phone_holder} onCopy={copy} /> : null}
        {paymentMethod === "CRYPTO" && hasCryptoNetworks ? <fieldset className="checkout-choice"><legend>Выберите сеть</legend><div className="choice-grid">{(Object.keys(cryptoNetworks) as CryptoNetwork[]).map((network) => <button className={cryptoNetwork === network ? "choice-card choice-card--active" : "choice-card"} type="button" key={network} onClick={() => setCryptoNetwork(network)}>{network}</button>)}</div>{cryptoNetwork && cryptoNetworks[cryptoNetwork] ? <PaymentDetails label={`Кошелёк ${cryptoNetwork}`} value={cryptoNetworks[cryptoNetwork] || ""} onCopy={copy} /> : null}</fieldset> : null}
        {copyStatus ? <div className="copy-status" role="status">{copyStatus}</div> : null}{error ? <div className="form-error">{error}</div> : null}
        <button className="checkout-button checkout-button--success" type="submit" disabled={loading || !deliveryProvider || !deliveryAddress.trim() || !paymentMethod || (paymentMethod === "CRYPTO" && !cryptoNetwork)}>{loading ? "Создаём заказ..." : "Подтвердить заказ"}</button>
      </form></div></div>;
}

function CheckoutState({ message, onClose }: { message: string; onClose: () => void }) {
  return <div className="overlay" role="dialog" aria-modal="true" aria-label="Оформление заказа"><div className="sheet sheet--checkout"><div className="sheet__header"><h2>Оформление заказа</h2><button className="text-button" type="button" onClick={onClose}>Закрыть</button></div><p className="field-hint" role="status">{message}</p></div></div>;
}

function PaymentDetails({ label, value, holder, onCopy }: { label: string; value: string; holder?: string | null; onCopy: (value: string) => void }) {
  return <div className="payment-details"><strong>{label}</strong><code>{value}</code>{holder ? <span>Получатель: {holder}</span> : null}<button type="button" className="secondary-button" onClick={() => void onCopy(value)}>Скопировать</button><small className="field-hint">Оплату проверит менеджер.</small></div>;
}
