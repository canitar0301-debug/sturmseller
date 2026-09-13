import asyncio
import logging
from bot.vinted_monitor import VintedMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)


async def main():
  monitor = VintedMonitor("config.json")
  await monitor.start()


if __name__ == "__main__":
  asyncio.run(main())
