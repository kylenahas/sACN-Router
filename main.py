#!/usr/bin/env python
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# ola_recv_dmx.py
# Copyright (C) 2005 Simon Newton

"""Receive DMX data."""

import getopt
import queue
import textwrap
import sys
import threading
from queue import Queue

from ola.ClientWrapper import ClientWrapper


import asyncio
import datetime
import random
import websockets
import netifaces

# dmx_frame_queue = Queue(maxsize=100)
dmx_frame_queue = asyncio.Queue(maxsize=10000)
ws_active_connections = set()
sys_ip_address = netifaces.ifaddresses('enp0s3')[netifaces.AF_INET][0].get('addr')


async def serve_data_to_all_clients():
    while True:
        print("Server")
        frame = await dmx_frame_queue.get()
        for websocket in ws_active_connections:
            print("Sending to: " + str(websocket.id))

            print("Data: " + str(frame[0:3]))
            offset = 0
            color = 'rgb(' + str(frame[0 + offset]) + ', ' + str(frame[1 + offset]) + ', ' + str(
                frame[2 + offset]) + ')'
            await websocket.send(color)

        # await asyncio.sleep(0.1)




async def serve_latest_color(websocket, path):
    while True:
        if not dmx_frame_queue.empty():
            frame = dmx_frame_queue.get()
            print("Data: " + str(frame[0:3]))
            offset = 0
            color = 'rgb(' + str(frame[0+offset]) + ', ' + str(frame[1+offset]) + ', ' + str(frame[2+offset]) + ')'
            await websocket.send(color)


async def start_server():
    print("WebSockets Server Started:")
    print(" -> Using IP Address: " + sys_ip_address)
    async with websockets.serve(ws_handler, sys_ip_address, 5678):
        await asyncio.Future()  # run forever

async def ws_handler(websocket):
    print("New ws client: " + str(websocket.id))
    ws_active_connections.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        print("Removed ws client: " + str(websocket.id))
        ws_active_connections.remove(websocket)


async def send(websocket, message):
    try:
        await websocket.send(message)
    except websockets.ConnectionClosed:
        pass

async def ws_main_loop():
    await asyncio.gather(
        start_server(),
        serve_data_to_all_clients()
    )
    # loop = asyncio.new_event_loop()
    # loop.run_until_complete(start_server())
    # loop.run_forever()
    # asyncio.get_event_loop().run_until_complete(start_server())
    # asyncio.get_event_loop().run_forever()
    # asyncio.set_event_loop(start_server())
    # asyncio.get_event_loop().run_forever()


def NewData(data):
    try:
        dmx_frame_queue.put_nowait(data)
    except asyncio.queues.QueueFull:
        print("DMX Queue full")
    # frame = data
    # print("Data: " + str(frame[0:3]))
    # offset = 0
    # color = 'rgb(' + str(frame[0 + offset]) + ', ' + str(frame[1 + offset]) + ', ' + str(frame[2 + offset]) + ')'
    # for websocket in ws_active_connections.copy():
    #     asyncio.create_task(send(websocket, color))
    # print(data[0:3])


def Usage():
  print(textwrap.dedent("""
  Usage: ola_recv_dmx.py --universe <universe>

  Display the DXM512 data for the universe.

  -h, --help                Display this help message and exit.
  -u, --universe <universe> Universe number."""))

async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)

def ola_main_loop():
  try:
      opts, args = getopt.getopt(sys.argv[1:], "hu:", ["help", "universe="])
  except getopt.GetoptError as err:
    print(str(err))
    Usage()
    sys.exit(2)

  universe = 1
  for o, a in opts:
    if o in ("-h", "--help"):
      Usage()
      sys.exit()
    elif o in ("-u", "--universe"):
      universe = int(a)

  wrapper = ClientWrapper()
  client = wrapper.Client()
  client.RegisterUniverse(universe, client.REGISTER, NewData)
  wrapper.Run()


if __name__ == "__main__":
    print("OLA Server Started:")
    ws_thread = threading.Thread(target=ws_main_loop)
    ola_thread = threading.Thread(target=ola_main_loop)

    # ws_thread.start()
    ola_thread.start()

    # to_thread(ola_main_loop())
    # to_thread(start_server())
    # ws_main_loop()
    # ws_main_loop()
    asyncio.run(ws_main_loop())

    # asyncio.get_event_loop().run_until_complete(start_server)
    # asyncio.get_event_loop().run_forever()




