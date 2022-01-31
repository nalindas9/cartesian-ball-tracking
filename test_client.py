"""@package docstring

Implements unit tests for testing client.py
"""
import pytest

import asyncio
from aiortc import RTCPeerConnection
from multiprocessing import Queue
from client import channel_log, channel_send, display_video

from server import BallBounceStreamTrack

def test_display_video_size():
    """
    Tests if size of frames queue size is greater than zero for display 
    video size method

    Parameters: 
    None (None): None
  
    Returns: 
    None: None 
    """
    queue = asyncio.run(display_video())
    assert queue.qsize() > 0 

