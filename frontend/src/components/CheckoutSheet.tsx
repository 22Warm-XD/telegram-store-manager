import { useState } from "react";

interface CheckoutSheetProps {
  loading: boolean;
  error: string | null;
  initialName?: string;
  initialUsername?: string;
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    username: string;
    phone: string;
    comment: string;
  }) => Promise<void>;
}

export function CheckoutSheet({
  loading,
  error,
  initialName,
  initialUsername,
  onClose,
  onSubmit,
}: CheckoutSheetProps) {
  const [name, setName] = useState(initialName || "");
  const [username, setUsername] = useState(initialUsername || "");
  const [phone, setPhone] = useState("");
  const [comment, setComment] = useState("");

  return (
    <div className="overlay" role="dialog" aria-modal="true">
      <div className="sheet sheet--checkout">
        <div className="sheet__header">
          <h2>Оформление заказа</h2>
          <button className="text-button" type="button" onClick={onClose}>
            Закрыть
          </button>
        </div>

        <form
          className="checkout-form"
          onSubmit={async (event) => {
            event.preventDefault();
            await onSubmit({ name, username, phone, comment });
          }}
        >
          <label>
            Имя
            <input value={name} onChange={(event) => setName(event.target.value)} required />
          </label>

          <label>
            Username в Telegram
            <input value={username} onChange={(event) => setUsername(event.target.value)} placeholder="@username" required />
            <small className="field-hint">Это основной способ связи. Укажите ваш @username, чтобы менеджер быстро написал вам.</small>
          </label>

          <label>
            Телефон для связи
            <input
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="+7 900 000-00-00"
              inputMode="tel"
              autoComplete="tel"
            />
            <small className="field-hint">Необязательно. Можно оставить пустым, если удобнее общаться только в Telegram.</small>
          </label>

          <label>
            Комментарий
            <textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="Размер, нюансы, удобное время для связи"
              rows={4}
            />
          </label>

          {error ? <div className="form-error">{error}</div> : null}

          <button className="checkout-button checkout-button--success" type="submit" disabled={loading}>
            {loading ? "Создаём заказ..." : "Подтвердить заказ"}
          </button>
        </form>
      </div>
    </div>
  );
}
