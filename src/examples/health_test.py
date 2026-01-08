import asyncio
import logging
import sys
from gshock_api.connection import Connection
from gshock_api.gshock_api import GshockAPI
from gshock_api.logger import logger

async def run_test():
    logger.info("========================================================================")
    logger.info("Press and hold lower-left button on your watch for 3 seconds to start...")
    logger.info("========================================================================")
    logger.info("")

    # If None, it will scan for G-Shock watches
    connection = Connection()
    api = GshockAPI(connection)
    
    logger.info("Waiting for connection...")
    if await connection.connect():
        try:
            logger.info("Connected!")
            
            # Step 1: Identification
            name = await api.get_watch_name()
            logger.info(f"Watch Name: {name}")
            
            # Step 2: Request Life Log
            logger.info("Requesting Life Log data (Health Data)...")
            await api.get_life_log()
            
            logger.info("Waiting for data notifications... (Press Ctrl+C to stop)")
            # Keep the connection open to receive notifications
            # We'll wait a generous amount of time or until Ctrl+C
            while True:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Test stopped by user.")
        except Exception as e:
            logger.error(f"Error during test: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            await connection.disconnect()
            logger.info("Disconnected.")
    else:
        logger.error("Failed to connect.")

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
