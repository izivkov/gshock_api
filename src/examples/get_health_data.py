#!/usr/bin/env python3
import asyncio
import sys
import os

# Add src to path so we can import gshock_api when running from here
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gshock_api.always_connected_watch_filter import (
    always_connected_watch_filter as watch_filter,
)
from gshock_api.connection import Connection
from gshock_api.gshock_api import GshockAPI
from gshock_api.iolib.health_data_io import HealthDataIO, DailyHealthData
from gshock_api.logger import logger
from gshock_api.watch_info import watch_info

def prompt() -> None:
    print("========================================================================")
    print("Press and hold lower-left button on your watch for 3 seconds to start...")
    print("========================================================================")
    print("")

async def main() -> None:
    prompt()
    
    try:
        logger.info("Waiting for connection to G-Shock watch...")
        connection = Connection()
        await connection.connect(watch_filter.connection_filter)
        logger.info("Connected!")

        api = GshockAPI(connection)
        
        # Check if the watch supports health data
        if not watch_info.hasHealthData:
            logger.info("This watch model does not support health data according to watch_info.")
            # We can still try to request it anyway, but it's good to warn
            
        logger.info("\n--- Requesting Health Data ---")
        
        # List to collect all incoming health records
        collected_data = []
        
        def on_health_update(data: DailyHealthData):
            # This callback is fired by HealthDataIO.on_received for every parsed record
            collected_data.append(data)
            snap = data.snapshots[0]
            logger.info(f"Received record for {data.date}: Steps={snap.steps}, Calories={snap.calories}, Distance={getattr(snap, 'distance', 0)}m")
            
        # Hook up the callback
        HealthDataIO.on_data_update = on_health_update
        
        # Trigger the request through the API
        await api.get_health_data()
        
        # Wait a sufficient amount of time for all requested indices to stream in.
        # The watch streams these slowly, often taking a few seconds per day.
        # The current implementation in HealthDataIO requests 5 indices, waiting 5 seconds between each.
        logger.info("Streaming data... Please wait ~30 seconds for all history to be received.")
        await asyncio.sleep(35.0)
        
        print("\n========================================================================")
        print("FINAL EXTRACTED HEALTH DATA")
        print("========================================================================")
        
        if not collected_data:
            print("No health data was received from the watch.")
        else:
            # Sort chronologically
            collected_data.sort(key=lambda d: d.date)
            
            # Print cleanly
            for record in collected_data:
                snap = record.snapshots[0]
                dist_str = f"{snap.distance}m" if hasattr(snap, "distance") and snap.distance > 0 else "N/A"
                print(f"Date: {record.date}")
                print(f"  Steps:    {snap.steps}")
                print(f"  Calories: {snap.calories} kcal")
                print(f"  Distance: {dist_str}")
                print("-" * 40)
                
    except Exception as e:
        logger.error(f"Error during health data extraction: {e}")
        
    finally:
        print("\nDisconnecting...")
        await connection.disconnect()
        print("Done.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
