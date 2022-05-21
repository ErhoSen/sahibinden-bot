import asyncio
import logging
from typing import Dict, Optional

import sentry_sdk
from core import Product
from object_storage_adapter import ObjectStorageAdapter
from sahibinden import sahibinden_client
from settings import settings
from telebot.async_telebot import AsyncTeleBot

logging.basicConfig(level=logging.INFO)
sentry_sdk.init(settings.SENTRY_DSN, traces_sample_rate=1.0)

SOURCE_URL = "https://www.sahibinden.com/en/bicycles?address_town=655&address_city=48"


async def send_message(bot: AsyncTeleBot, product: Product):
    await bot.send_photo(
        chat_id=settings.TELEGRAM_CHANNEL_ID,
        photo=product.image,
        caption=product.to_message(),
        parse_mode="HTML",
    )


async def _handler(event: Optional[Dict], context: Optional[Dict]):
    products = await sahibinden_client.get_products(SOURCE_URL)
    logging.info(f"Sahibinden products: {[p.id for p in products]}")

    bot = AsyncTeleBot(settings.TELEGRAM_BOT_TOKEN, parse_mode=None)
    published_product_ids = []
    async with ObjectStorageAdapter(settings.AWS_BUCKET_NAME) as adapter:
        async for product in adapter.determine_new_products(products):
            await send_message(bot, product)
            published_product_ids.append(product.id)
        if published_product_ids:
            logging.info(f"Published sahibinden products: {published_product_ids}")
            await adapter.set_products_published(published_product_ids)
        await bot.close()


def handler(event: Optional[Dict], context: Optional[Dict]):
    """
    Synchronous wrapper of `_handler`, that can be called trough command line.
    Yandex.Function do it this way..
    """
    asyncio.run(_handler(event, context))


if __name__ == "__main__":
    handler(None, None)
