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
# main.py
# Copyright (C) 2022 Kyle Nahas

"""Receive DMX data and transmit it to connected clients via websockets."""

import getopt
import textwrap
import sys
import threading

from ola.ClientWrapper import ClientWrapper


import asyncio
import websockets
import netifaces

QUEUE_DEPTH = 100
# dmx_frame_queue = asyncio.queues.LifoQueue(maxsize=1000) # Moved within scope of event loop
ws_active_connections = set()
ws_addresses = dict()
sys_ip_address = netifaces.ifaddresses('enp0s3')[netifaces.AF_INET][0].get('addr') # Get the IP address of the first network card


async def serve_data_to_all_clients():
    while True:
        frame = await dmx_frame_queue.get()
        if len(ws_active_connections):
            await asyncio.sleep(0.1)
            for websocket in ws_active_connections:
                # print("Sending to: " + str(websocket.id))
                # print("Data: " + str(frame[0:3]))
                offset = ws_addresses[websocket.id] - 1
                color = 'rgb(' + str(frame[0 + offset]) + ', ' + str(frame[1 + offset]) + ', ' + str(
                    frame[2 + offset]) + ')'
                try:
                    await websocket.send(color)
                except websockets.ConnectionClosed:
                    ws_active_connections.remove(websocket)
                    print("Tried to send to a websocket that no longer exists")
                    print(" -> Removed: " + str(websocket.id))
                    break
        else:
            await asyncio.sleep(0.5)


async def start_server():
    print("WebSockets Server Started:")
    print(" -> Using IP Address: " + sys_ip_address)
    async with websockets.serve(ws_handler, sys_ip_address, 5678):
        await asyncio.Future()  # run forever


async def ws_handler(websocket):
    ws_active_connections.add(websocket)
    ws_addresses[websocket.id] = 1  # Sane default == 1
    print("New ws client: " + str(websocket.id))
    print("There are now " + str(len(ws_active_connections)) + " client(s) connected.")
    try:
        message = await websocket.recv()
        ws_addresses[websocket.id] = int(message)
        assert(0 < ws_addresses[websocket.id] < 511)
        print("Client: " + str(websocket.id) + " assigned to address: " + str(ws_addresses.get(websocket.id)))
    except ValueError:
        print("Invalid address specified for: " + str(websocket.id) + ". Ignored, address == 1")
    except AssertionError:
        print("Out of bounds address specified for: " + str(websocket.id) + ". Ignored, address == 1")

    try:
        await websocket.wait_closed()
        ws_active_connections.remove(websocket)
    except websockets.ConnectionClosed:
        print("Removed ws client: " + str(websocket.id))


async def ws_main_loop():
    global dmx_frame_queue
    dmx_frame_queue = asyncio.queues.LifoQueue(maxsize=QUEUE_DEPTH)
    await asyncio.gather(
        start_server(),
        serve_data_to_all_clients()
    )


def NewData(data):
    try:
        dmx_frame_queue.put_nowait(data)
    except asyncio.queues.QueueFull:
        while dmx_frame_queue.qsize():
            dmx_frame_queue.get_nowait()
        dmx_frame_queue.put_nowait(data)
        print("DMX Queue Dumped")


def Usage():
  print(textwrap.dedent("""
  Usage: ola_recv_dmx.py --universe <universe>

  Display the DXM512 data for the universe.

  -h, --help                Display this help message and exit.
  -u, --universe <universe> Universe number."""))


def ola_main_loop():
    print("OLA Server Started:")
    universe = 3
    print(" -> Subscribed to universe: " + str(universe))
    # try:
    #     opts, args = getopt.getopt(sys.argv[1:], "hu:", ["help", "universe="])
    # except getopt.GetoptError as err:
    #     print(str(err))
    #     Usage()
    #     sys.exit(2)
    #
    #
    # for o, a in opts:
    #     if o in ("-h", "--help"):
    #       Usage()
    #       sys.exit()
    #     elif o in ("-u", "--universe"):
    #       universe = int(a)

    wrapper = ClientWrapper()
    client = wrapper.Client()
    client.RegisterUniverse(universe, client.REGISTER, NewData)
    wrapper.Run()


if __name__ == "__main__":

    ola_thread = threading.Thread(target=ola_main_loop)

    ola_thread.start()

    asyncio.run(ws_main_loop())





