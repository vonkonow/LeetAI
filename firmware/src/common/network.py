"""
Network components for the core module.

This module provides network communication functionality for the application.
"""

import time
import config.config as config

class NetworkError(Exception):
    """Base class for network-related errors."""
    pass

class PacketSendError(NetworkError):
    """Error occurred while sending a packet."""
    pass

class PacketReadError(NetworkError):
    """Error occurred while reading a packet."""
    pass

class SongSendError(NetworkError):
    """Error occurred while sending a song."""
    pass

class PacketHandler:
    """
    A class for handling network packet communication.
    
    Attributes:
        esp: ESP-NOW instance
        instrument_id: ID of the current instrument
        peer_broadcast: Broadcast peer for sending packets
    """
    
    def __init__(self, esp, instrument_id: int, peer_broadcast):
        """
        Initialize a new packet handler.
        
        Args:
            esp: ESP-NOW instance
            instrument_id: ID of the current instrument
            peer_broadcast: Broadcast peer for sending packets
        """
        self.esp = esp
        self.instrument_id = instrument_id
        self.peer_broadcast = peer_broadcast
        self.PAYLOAD = config.EXTRA_PAYLOAD

    def send_packet(self, id: str, payload: bytes, addr=None, retransmission: int = None):
        """
        Send a packet over the network, with optional retransmission.
        
        Args:
            id: Packet type identifier
            payload: Packet payload
            addr: Target address (defaults to broadcast)
            retransmission: Number of times to retransmit (defaults to config value)
            
        Raises:
            PacketSendError: If packet sending fails
        """
        try:
            packet = bytearray(id, 'utf-8')
            packet.extend(payload)
            target = addr if addr else self.peer_broadcast
            retransmission = retransmission or config.NETWORK_PACKET_RETRANSMISSION
            for _ in range(retransmission):
                self.esp.send(packet, target)
                if retransmission > 1:
                    time.sleep(config.NETWORK_PACKET_DELAY)
        except Exception as e:
            raise PacketSendError(f"Failed to send packet {id}: {e}") from e

    def send_verified_packet(self, id: str, payload: bytes, addr=None):
        """
        Send a packet and wait for an 'a' (ack) response, retrying up to 10 times.
        
        Args:
            id: Packet type identifier
            payload: Packet payload
            addr: Target address (defaults to broadcast)
            
        Returns:
            bool: True if ack received, False otherwise
            
        Raises:
            PacketSendError: If packet sending fails
        """
        try:
            packet = bytearray(id, 'utf-8')
            packet.extend(payload)
            target = addr if addr else self.peer_broadcast
            for retries in range(10):
                self.esp.send(packet, target)
                send_time = time.monotonic()
                while time.monotonic() < (send_time + 0.5):
                    try:
                        read_packet = self.esp.read()
                    except Exception:
                        continue
                    else:
                        if read_packet and read_packet.msg[0] == ord('a'):
                            return True
            return False
        except Exception as e:
            raise PacketSendError(f"Failed to send verified packet {id}: {e}") from e

    def send_song(self, id, byte_song, debug, hw):
        """
        Send a song to a device.
        
        Args:
            id: Target device ID
            byte_song: Song data
            debug: Debug display object
            hw: Hardware interface
            
        Raises:
            SongSendError: If song sending fails
        """
        try:
            # broadcast clear song
            self.send_packet('c', [id], retransmission=2)
            time.sleep(0.01)
            debug.show_debug_message("sending")
            hw.display.refresh()

            # send header
            packet = bytearray('h','utf-8')
            packet.extend(byte_song[:11])
            self.esp.send(bytearray(packet), self.peer_broadcast)

            # send song events
            for i in range(11, len(byte_song), 7):
                packet = bytearray('e','utf-8')
                if byte_song[i + 4] == id or id == 255:
                    packet.extend(byte_song[i: i + 7])
                    self.esp.send(bytearray(packet), self.peer_broadcast)
                    # prevent packet loss
                    time.sleep(0.004)

            debug.show_debug_message("done")
            hw.display.refresh()

            # broadcast display update
            self.send_packet('u', self.PAYLOAD, retransmission=2)

            # broadcast reset
            self.send_packet('r', self.PAYLOAD, retransmission=2)
        except Exception as e:
            raise SongSendError(f"Failed to send song to device {id}: {e}") from e

    def send_pair(self) -> None:
        """Send a pair request packet."""
        self.send_packet('p', [self.instrument_id])

    def read_packet(self):
        """
        Read a packet from the network.
        
        Returns:
            The received packet or None if no packet is available
            
        Raises:
            PacketReadError: If packet reading fails
        """
        try:
            return self.esp.read()
        except Exception as e:
            raise PacketReadError(f"Failed to read packet: {e}") from e

    def send_scale(self, scale_start: int, scale: list):
        """
        Send a scale packet to update the scale and chord notes.
        
        Args:
            scale_start: Starting note of the scale (e.g., 60 for C4)
            scale: List of scale intervals (e.g., [0, 2, 4, 5, 7, 9, 11] for major scale)
            
        Raises:
            PacketSendError: If packet sending fails
        """
        try:
            # Format: 'n' + reserved + scale_start + scale_intervals
            packet = bytearray('n', 'utf-8')
            packet.append(0)  # Reserved byte
            packet.append(scale_start)
            packet.extend(scale[:7])  # Ensure we only send 7 intervals
            self.send_packet('n', packet[1:])
        except Exception as e:
            raise PacketSendError(f"Failed to send scale packet: {e}") from e

    def handle_packet(self, packet):
        """
        Handle a received packet.
        
        Args:
            packet: The received packet
            
        Returns:
            tuple: Packet type and arguments, or None if packet is invalid
        """
        if not packet:
            return None

        packet_types = config.NETWORK_PACKET_TYPES
        msg = packet.msg

        # check if the packet is an "event" packet
        if msg[0] == packet_types['event']:
            tick_start = int.from_bytes(msg[1:3], "big")
            tick_end = int.from_bytes(msg[3:5], "big")
            ch = msg[5]
            note = msg[6]
            intensity = msg[7]
            return ('event', ch, tick_start, tick_end, note, intensity)

        # check if the packet is a "live" packet
        elif msg[0] == packet_types['live']:
            ch = msg[1]
            note = msg[2]
            intensity = msg[3]
            return ('live', ch, note, intensity)

        # check if the packet is a "pair_request" packet
        elif msg[0] == packet_types['pair']:
            id = msg[1]
            return ('pair', id)

        # check if the packet is a "tick" packet
        elif msg[0] == packet_types['tick']:
            tick = int.from_bytes(msg[1:3], "big")
            return ('tick', tick)

        # check if the packet is a "begin" packet
        elif msg[0] == packet_types['begin']:
            return ('begin',)

        # check if the packet is a "stop" packet
        elif msg[0] == packet_types['stop']:
            return ('stop',)

        # check if the packet is a "header" packet
        elif msg[0] == packet_types['header']:
            ticks_per_beat = int.from_bytes(msg[1:3], "big")
            max_ticks = int.from_bytes(msg[3:7], "big")
            tempo = int.from_bytes(msg[7:9], "big")
            numerator = msg[9]
            denominator = msg[10]
            nr_instruments = msg[11]
            return ('header', ticks_per_beat, max_ticks, tempo, numerator, denominator, nr_instruments)

        # check if the packet is a "mute" packet
        elif msg[0] == packet_types['mute']:
            ch = msg[1]
            intensity = msg[2]
            return ('mute', ch, intensity)

        # check if the packet is an "update" packet
        elif msg[0] == packet_types['update']:
            return ('update',)

        # check if the packet is a "reset" packet
        elif msg[0] == packet_types['reset']:
            return ('reset',)

        # check if the packet is a "clear" packet
        elif msg[0] == packet_types['clear']:
            id = msg[1]
            return ('clear', id)

        # check if the packet is a "scale" packet
        elif msg[0] == packet_types['scale']:
            if len(msg) >= 10:  # Ensure we have enough bytes
                scale_start = msg[2]
                scale = list(msg[3:10])  # Get 7 scale intervals
                return ('scale', scale_start, scale)
            return None

        return None

    def check_packets(self):
        """
        Check for and handle incoming packets.
        
        Returns:
            bool: True if a packet was handled, False otherwise
        """
        if not self.esp:
            return False

        try:
            packet = self.read_packet()
            if packet:
                result = self.handle_packet(packet)
                return result is not None
        except ValueError:
            pass
        return False 