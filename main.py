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

dmx_frame_queue = Queue(maxsize=100)

async def time(websocket, path):
    while True:
        # now = datetime.datetime.utcnow().isoformat() + 'Z'
        # await websocket.send(now)
        color = 'rgb(' + str(random.randint(0, 255)) + ', ' + str(random.randint(0, 255)) + ', '\
                + str(random.randint(0, 255)) + ')'
        await websocket.send(color)
        await asyncio.sleep(random.random() * 3)


async def serve_latest_color(websocket, path):
    while True:
        if not dmx_frame_queue.empty():
            frame = dmx_frame_queue.get()
            print("Data: " + str(frame[0:3]))
            offset = 0
            color = 'rgb(' + str(frame[0+offset]) + ', ' + str(frame[1+offset]) + ', ' + str(frame[2+offset]) + ')'
            await websocket.send(color)


start_server = websockets.serve(serve_latest_color, '192.168.56.103', 5678)


def NewData(data):
    dmx_frame_queue.put(data)
    # print(data[0:3])


def Usage():
  print(textwrap.dedent("""
  Usage: ola_recv_dmx.py --universe <universe>

  Display the DXM512 data for the universe.

  -h, --help                Display this help message and exit.
  -u, --universe <universe> Universe number."""))


def ws_main_loop():
    # asyncio.get_event_loop().run_until_complete(start_server)
    # asyncio.get_event_loop().run_forever()
    asyncio.set_event_loop(start_server)
    asyncio.get_event_loop().run_forever()


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
    # ws_thread = threading.Thread(target=ws_main_loop)
    ola_thread = threading.Thread(target=ola_main_loop)

    # ws_thread.start()
    ola_thread.start()

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()




