"""
Test script to demonstrate the pending requests registry functionality.

This script shows how the registry automatically cancels pending requests
when an error occurs.
"""

import asyncio
from gshock_api.pending_requests_registry import PendingRequestsRegistry
from gshock_api.cancelable_result import CancelableResult
from gshock_api.exceptions import GShockConnectionError


async def test_pending_requests_cancellation():
    """Test that pending requests are canceled when an error occurs."""
    
    print("Creating two pending requests...")
    
    # Simulate two pending requests
    result1 = CancelableResult[str](timeout=30.0)
    result2 = CancelableResult[int](timeout=30.0)
    
    # Register them
    PendingRequestsRegistry.register("TestRequest1", result1)
    PendingRequestsRegistry.register("TestRequest2", result2)
    
    print(f"Registered {PendingRequestsRegistry.get_pending_count()} pending requests")
    
    # Create tasks that wait for results
    async def wait_for_result1():
        try:
            result = await result1.get_result()
            print(f"Result 1 received: {result}")
        except GShockConnectionError as e:
            print(f"Result 1 canceled with error: {e}")
    
    async def wait_for_result2():
        try:
            result = await result2.get_result()
            print(f"Result 2 received: {result}")
        except GShockConnectionError as e:
            print(f"Result 2 canceled with error: {e}")
    
    # Start waiting tasks
    task1 = asyncio.create_task(wait_for_result1())
    task2 = asyncio.create_task(wait_for_result2())
    
    # Wait a bit to let tasks start waiting
    await asyncio.sleep(0.1)
    
    # Simulate an error occurring
    print("\nSimulating error occurrence...")
    PendingRequestsRegistry.cancel_all("Simulated watch communication error")
    
    # Wait for tasks to complete
    await task1
    await task2
    
    print(f"\nPending requests after cancellation: {PendingRequestsRegistry.get_pending_count()}")
    print("Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_pending_requests_cancellation())
