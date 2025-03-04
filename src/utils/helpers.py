"""
Utility helper functions
"""

from typing import TypeVar, List

T = TypeVar('T')

def sleep(ms: int) -> None:
    """Sleep for specified milliseconds."""
    import asyncio
    return asyncio.sleep(ms / 1000)

def chunk(array: List[T], size: int) -> List[List[T]]:
    """Chunk an array into smaller arrays of specified size."""
    return [array[i:i + size] for i in range(0, len(array), size)] 