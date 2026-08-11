import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from dotenv import load_dotenv
load_dotenv()
from src.agent_controller import AgentController

async def test():
    a = AgentController()
    await a.initialize()
    await a.execute_task('scrape shopee https://shopee.vn/product/786481971/24229562723')
    await a.shutdown()

asyncio.run(test())
