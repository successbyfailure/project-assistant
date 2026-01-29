import asyncio
import logging
import sys
from src.server.mcp_server import ProjectAssistantServer
from src.config.coder import CoderSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Project Assistant...")
    
    coder_settings = CoderSettings()
    if not coder_settings.is_coder_workspace:
        logger.warning("Not running in a Coder workspace environment. Some features may be limited.")
    
    logger.info(f"Projects root: {coder_settings.projects_root}")
    
    server = ProjectAssistantServer(coder_settings)
    await server.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception("Fatal error")
        sys.exit(1)
