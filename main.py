import sys
import asyncio
import logging
from dotenv import load_dotenv

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Load environment variables from .env file
load_dotenv()

from src.agent_controller import AgentController

async def main():
    agent = AgentController()
    
    try:
        await agent.start()
        
        print("Python Complete Agent is running in Autonomous Mode.")
        print("Reading from tasks.txt...")
        
        completed = await agent.run_autonomous_loop()
        print(f"Autonomous loop finished. Successfully completed {len(completed)} tasks.")
            
    except KeyboardInterrupt:
        print("Agent stopped by user.")
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
