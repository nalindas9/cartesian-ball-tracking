"""@package docstring

Implements an aiortc server 
"""
import cv2
import argparse
import numpy as np
import math

import uuid
import asyncio
from asyncio.runners import run
from typing import final

from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCIceCandidate
from aiortc import RTCSessionDescription
from aiortc.rtcrtpsender import RTP_HISTORY_SIZE
from numpy.testing._private.utils import measure

from multiprocessing import Queue

class BallBounceStreamTrack(MediaStreamTrack):
    """
    A Media Stream Track that transmits continuous 2D image of
    a ball bouncing across screen

    Attributes: 
        None (None): None 
    """
    def __init__(self):
        """
        Constructor for BallBounceStreamTrack class

        Parameters: 
            None (None): None 
          
        Returns: 
            None (None): None 
        """
        super().__init__()

    async def recv(self):
        """
        Method that generates a continous 2D image of ball bouncing
        across screen

        Parameters: 
            None (None): None  
          
        Returns: 
            actual_coordinates: Queue of the actual coordinates of the ball
        """
        img = np.zeros((480, 480, 3), dtype = 'uint8')
        x, y = 100, 100
        dx, dy = 1, 1
        actual_coordinates = Queue()
        fourcc = cv2.VideoWriter_fourcc(*'XVID') 
        out = cv2.VideoWriter('ball_bounce_video.avi',fourcc, 20.0, (480,480))
        num_frames = 0
        while num_frames < 1000:
            num_frames = num_frames + 1 
            img = np.zeros((480, 480, 3), dtype = 'uint8')
            x = x + dx
            y = y + dy
            actual_coordinates.put(str(x) + ' , ' + str(y))
            img = cv2.circle(img, (x, y), 20, (0, 255, 0), -1)
            cv2.namedWindow('ball_bounce', cv2.WINDOW_NORMAL)
            cv2.imshow('ball_bounce', img)
            out.write(img)
            delay = cv2.waitKey(10)
            if y >= 480:
                dy *= -1
            elif y <= 0:
                dy *= -1
            if x >= 480:
                dx *= -1
            elif x <= 0:
                dx *= -1
        cv2.destroyAllWindows()
        return actual_coordinates

async def consume_signaling(pc, signaling):
    """
    Sends local description to signalling and sends answer

    Parameters: 
    pc (RTCPeerConnection): RTCPeerConnection object
    signaling (TcpSocketSignaling): TcpSocketSignaling object
  
    Returns: 
    None: None 
    """
    while True:
        obj = await signaling.receive()

        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)

            if obj.type == "offer":
                
                await pc.setLocalDescription(await pc.createAnswer()) # send answer
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            print("Exiting")
            break

def channel_log(channel, t, message):
    """
    Prints message information on the outputs stream for given channel

    Parameters: 
    channel (DataChannel): Data channel 
    t (string): String
    message (string): Message
  
    Returns: 
    None: None 
    """
    print("channel(%s) %s %s" % (channel.label, t, message))

def channel_send(channel, message):
    """
    Sends message on given channel

    Parameters: 
    channel (DataChannel): Data channel 
    message (string): Message
  
    Returns: 
    None: None
    """
    channel_log(channel, ">", message)
    channel.send(message)

async def run_offer(pc, signaling, file):
    """
    Runs the aiortc offer

    Parameters: 
    pc (RTCPeerConnection): RTCPeerConnection object
    signaling (TcpSocketSignaling): TcpSocketSignaling object
    file (BallBounceStreamTrack): BallBounceStreamTrack object
  
    Returns: 
    None: None
    """
    actual_coordinates = await file.recv()

    await signaling.connect()
    channel_data = pc.createDataChannel("datachannel")
    channel_log(channel_data, "-", "created by local party")

    async def send_pings():
        while True:
            channel_send(channel_data, "pinging client")
            await asyncio.sleep(1)

    @channel_data.on("open")
    def on_open():
        asyncio.ensure_future(send_pings())

    @channel_data.on("message")
    def on_message(message):
        actual_coordinate = actual_coordinates.get()
        actual_coordinate  = actual_coordinate.split()
        actual_x, actual_y = float(actual_coordinate[0]), float(actual_coordinate[2])
        coordinate = message.split()
        x, y = float(coordinate[0]), float(coordinate[2])
        error = math.sqrt(
            (actual_x - x)*(actual_x - x) + 
            (actual_y - y)*(actual_y - y)
        )
        channel_log(channel_data, ": Receieved coordinates <", message)
        channel_log(channel_data, " Coordinates error: ", str(error))

    done_reading = False
    channel = pc.createDataChannel("filexfer")
    
    await pc.setLocalDescription(await pc.createOffer()) # Send offer
    await signaling.send(pc.localDescription)

    await consume_signaling(pc, signaling)

if __name__ == "__main__":
    """
    Main function

    Parameters: 
    None (None): None
  
    Returns: 
    None: None
    """
    parser = argparse.ArgumentParser(
        description="Data transfer arguments"
    )
    parser.add_argument(
        "--signaling_host", 
        default="127.0.0.1", 
        help="Signaling host (tcp-socket only)"
    )
    parser.add_argument(
        "--signaling_port", 
        default=1234, 
        help="Signaling port (tcp-socket only)"
    )
    arguments = parser.parse_args()
    print(arguments)
    print("")

    signaling = TcpSocketSignaling(
        arguments.signaling_host,
        arguments.signaling_port
    )

    pc = RTCPeerConnection()
    
    ball_bounce_video = BallBounceStreamTrack()

    print('Sending offer ...')
    print("")
    offer = run_offer(pc, signaling, ball_bounce_video)

    loop = asyncio.get_event_loop() # Run Event Loop
    try:
        loop.run_until_complete(offer)
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(pc.close())
        loop.run_until_complete(signaling.close())












