"""@package docstring

Implements an aiortc client 
"""
from queue import Empty
import cv2
import imutils
import argparse
import numpy as np
import time
import os

import uuid
import asyncio
from asyncio.runners import run
from typing import final

from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCIceCandidate
from aiortc import RTCSessionDescription
from aiortc.rtcrtpsender import RTP_HISTORY_SIZE

from multiprocessing import Process, Queue, Value, Array

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
                await pc.setLocalDescription(await pc.createAnswer()) # Send answer
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            print("Exiting")
            break

async def display_video():
    """
    Displays the video in OpenCV window

    Parameters: 
    None (None): None
  
    Returns: 
    None: None 
    """
    cap = cv2.VideoCapture('ball_bounce_video.avi')
    queue = Queue()
    while cap.isOpened():
        correct, frame = cap.read()
        if not correct:
            print("Can't receive frame (stream end?). Exiting ...")
            break
        cv2.imshow('frame', frame)
        queue.put(frame)
        if cv2.waitKey(1) == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    return queue

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

async def run_answer(pc, signaling):
    """
    Runs the aiortc answer

    Parameters: 
    pc (RTCPeerConnection): RTCPeerConnection object
    signaling (TcpSocketSignaling): TcpSocketSignaling object
  
    Returns: 
    None: None 
    """
    queue = await display_video()
    coordinates = Queue()
    p1 = Process(target = process_a, args = (queue, coordinates)) # Started process_a
    p1.start()
    time.sleep(30)
    p1.terminate()
    p1.join()
    cv2.destroyAllWindows()
    print('process id: ', os.getpid())
    await signaling.connect()
    
    @pc.on("datachannel")
    def on_datachannel(channel_data):
        channel_log(channel_data, "-", "created by remote party")
        @channel_data.on("message")
        def on_message(message):
            channel_send(channel_data, coordinates.get())
    await consume_signaling(pc, signaling)

def process_a(queue, coordinates):
    """
    Process a performs HSV masking and finds the x, y center coordinates 
    of the ball in the video sequence

    Parameters: 
    queue (multiprocessing.Queue): multiprocessing.Queue object that stores 
                                   video frames
    signaling (TcpSocketSignaling): TcpSocketSignaling object
  
    Returns: 
    None: None 
    """
    print('process_a started ...')

    while queue is not Empty:
        frame = queue.get()
        if frame is None:
            continue
        frame = np.asarray(frame)
        frame_original = frame.copy()
        frame = cv2.GaussianBlur(frame, (11, 11), 0) 
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(frame, (29, 86, 6), (64, 255, 255))
        mask = cv2.erode(mask, None, iterations = 2)
        mask = cv2.dilate(mask, None, iterations = 2)
        contours = cv2.findContours(
            mask.copy(), 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        contours = imutils.grab_contours(contours)
        
        for c in contours:
            # compute the center of the contour
            M = cv2.moments(c)
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            # draw the contour and center of the shape on the image
            cv2.drawContours(frame_original, [c], -1, (0, 0, 255), 2)
            cv2.circle(frame_original, (cX, cY), 7, (255, 0, 0), -1)
            cv2.putText(frame_original, "center", (cX - 20, cY - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            coordinates.put(str(cX) + ' , ' + str(cY))

        cv2.namedWindow('frame_original', cv2.WINDOW_NORMAL)
        cv2.imshow('frame_original', frame_original)
        cv2.waitKey(10)

    cv2.destroyAllWindows()

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
    
    print('Sending answer ...')
    print("")
    offer = run_answer(pc, signaling)
    
    loop = asyncio.get_event_loop() # run event loop
    try:
        loop.run_until_complete(offer)
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(pc.close())
        loop.run_until_complete(signaling.close())

    






