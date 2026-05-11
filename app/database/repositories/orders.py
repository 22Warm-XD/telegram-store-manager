from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Order, OrderContactMethod, OrderItem, Product


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_order(
        self,
        *,
        telegram_id: int,
        telegram_username: str | None,
        telegram_first_name: str | None,
        customer_name: str,
        contact_username: str,
        phone: str | None,
        comment: str | None,
        contact_method: OrderContactMethod,
        items: list[tuple[Product, int]],
    ) -> Order:
        order = Order(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            telegram_first_name=telegram_first_name,
            customer_name=customer_name,
            contact_username=contact_username,
            phone=phone,
            comment=comment,
            contact_method=contact_method,
            total_amount=sum(product.price * quantity for product, quantity in items),
        )
        order.items = [
            OrderItem(
                product_id=product.id,
                product_title=product.title,
                price=product.price,
                quantity=quantity,
            )
            for product, quantity in items
        ]
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order, attribute_names=["items"])
        return order
