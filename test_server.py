"""@package docstring

Implements unit tests for testing server.py
"""
import pytest

import asyncio
from aiortc import RTCPeerConnection
from multiprocessing import Queue
from client import channel_log, channel_send

from server import BallBounceStreamTrack

def test_recv_size_coordinates_queue():
    """
    Tests if size of coordinates queue size is greater than zero for recv method

    Parameters: 
    None (None): None
  
    Returns: 
    None: None 
    """
    ball_bounce = BallBounceStreamTrack()
    actual_coordinates = asyncio.run(ball_bounce.recv())
    assert actual_coordinates.qsize() > 0 