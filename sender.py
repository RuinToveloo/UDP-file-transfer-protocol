#!/usr/bin/env python3

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import time
import threading
import argparse
import socket

from packet import Packet

# ------------------------------------------------------------------------------------------------------------------------------
class Sender:
    def __init__(self, ne_host, ne_port, port, timeout, send_file, seqnum_file, ack_file, n_file, send_sock, recv_sock):

        self.ne_host = ne_host # Host address of the network emulator
        self.ne_port = ne_port # UDP port number for the network emulator to receive data
        self.port = port # UDP port for receiving ACKs from the network emulator
        self.timeout = timeout / 1000 # needs to be in seconds

        self.send_file = send_file # file object holding the file to be sent
        self.seqnum_file = seqnum_file # seqnum.log
        self.ack_file = ack_file # ack.log
        self.n_file = n_file # N.log

        self.send_sock = send_sock
        self.recv_sock = recv_sock

        # internal state
        self.lock = threading.RLock() # prevent multiple threads from accessing the data simultaneously
        self.window = [] # To keep track of the packets in the window
        self.window_size = 1 # Current window size (N)
        self.n = 1
        self.timer = threading.Timer(self.timeout, timeout) # Threading.Timer object that calls the on_timeout function
        self.timer_packet = None # The packet that is currently being timed
        self.current_time = -1 # Current 'timestamp' for logging purposes
        self.dataarr = []
        self.dataseqnum = []
        self.datastatus = []

    def run(self):
        self.recv_sock.bind(('', self.port))
        print("-----Handshaking starts-----")
        self.perform_handshake()
        print("-----Handshaking   ends-----")

        # write initial N to log
        self.write_nlog(self.current_time, self.n)
        self.current_time += 1

        print("-----Data transmission starts-----")
        self.store_data()
        self.perform_data_transmission()
        print("-----Data transmission   ends-----")
        
        print("-----Termination starts-----")
        self.perform_eot()
        print("-----Termination   ends-----")
        
        exit()

    def perform_handshake(self):
        syn = Packet(3, 0, 0, "") # create a syn Packet
        while True:
            self.transmit(syn)
            self.write_seqlog(-1, 0, 3) # write syn to seqnum.log
            print("Sent SYN packet...")
            try:
                self.recv_sock.settimeout(3) # start timer for receiveing 
                packet, addr = self.recv_sock.recvfrom(self.port)
                if packet is not None:
                    print("Got SYN ACK packet")
                    self.write_acklog(self.current_time, 0, 3)
                    break
            except socket.timeout:
                print("TIME OUT")
                continue
        self.current_time = self.current_time + 1
        return True
    
    def store_data(self):
        # store input file into arr
        self.dataarr = []
        s = ""
        while True:
            char = self.send_file.read(1)
            if not char:
                break
            s += char
            if len(s) == 500:
                self.dataarr.append(s)
                s = ""
        if s != "":
            self.dataarr.append(s)
        i = 0
        for iterator in self.dataarr:
            self.dataseqnum.append(i % 32)
            self.datastatus.append(False)
            i+=1
        data = Packet(1, 0, len(self.dataarr[0]), self.dataarr[0]) # create the first data Packet
        self.window.append(data)
        self.transmit(data)
        self.write_seqlog(self.current_time, 0, 1) # write data to seqnum.log
        self.current_time += 1
        print("Sent Data packet...")

        
    def perform_data_transmission(self):
        while True:
            
            with self.lock:
            
                # if window is empty and 
                if not self.window:
                    print("All ACK recieved!!! Exit!")
                    break
            
                try:
                    print("------------------------------------")
                    print("window size: {}\n".format(len(self.window)))
                    print("dataarr: {}\n".format(self.dataarr))
                    print("seq arr: {}\n".format(self.dataseqnum))
                    print("status: {}\n".format(self.datastatus))
                    print("--------------------------------------")
                    
                    self.recv_sock.settimeout(self.timeout) # start timer for receiveing 
                    packet, addr = self.recv_sock.recvfrom(self.port)
                    if packet is not None:
                        typ, seqnum, length, data = Packet(packet).decode()
                        print("Got Data ACK packet: {}\n".format(seqnum))
                        print(self.dataarr)
                        print(self.dataseqnum)
                        print(self.datastatus)
                        self.write_acklog(self.current_time, seqnum, 0)
                        self.current_time += 1
                        if typ == 0 and seqnum >= self.dataseqnum[0]:
                            can_delete = False
                            count = 0
                            for i in range(10):
                                if i < len(self.window):
                                    count += 1
                                    if self.dataseqnum[i] == seqnum:
                                        can_delete = True
                                        break
                            for i in range(count):
                                self.window.pop(0)
                                self.dataarr.pop(0)
                                self.dataseqnum.pop(0)
                                self.datastatus.pop(0)
                        if self.window_size < 10:
                            self.window_size += 1
                        if self.n < 10:
                            self.n += 1
                            self.write_nlog(self.current_time, self.n)
                        self.current_time += 1
                        index = len(self.window)
                        # refill window
                        for i in range(self.window_size - len(self.window)):
                            if index < len(self.dataseqnum):
                                # create the next data Packet
                                data = Packet(1, self.dataseqnum[index], len(self.dataarr[index]), self.dataarr[index])
                                index = index+1
                                print("Send seq = {}\n".format(self.dataseqnum[index-1]))
                                self.transmit(data)
                                self.window.append(data)
                        else:
                            print("ERROR: Invalid packet received!!")
            
                except socket.timeout:
                    if not self.window:
                        break
                    else:
                        # re-send first packet
                        print("send sequ = {}\n".format(self.dataseqnum[0]))
                        self.transmit(self.window[0])
                        self.write_seqlog(self.current_time, self.dataseqnum[0], 1)
                        self.write_nlog(self.current_time, 1)
                        self.n = 1
                        self.current_time = self.current_time + 1
                    

    def perform_eot(self):
        recv_sock.settimeout(None)
        eot = Packet(2, 0, 0, "") # create a EOT Packet
        while True:
            self.transmit(eot)
            self.write_seqlog(self.current_time, 0, 2) # write eot to seqnum.log
            self.current_time += 1
            print("Sent EOT packet...")
            
            try:
                self.recv_sock.settimeout(3) # start timer for receiveing 
                packet, addr = self.recv_sock.recvfrom(self.port)
                if packet is not None:
                    print("Got EOT ACK packet")
                    self.write_acklog(self.current_time, 0, 2)
                    break
            except socket.timeout:
                print("TIME OUT")
                continue
        # close connection
        recv_sock.close()
        send_sock.close()
        return True    

    def transmit(self, packet):
        send_sock.sendto(packet.encode(), (self.ne_host, self.ne_port))
        return True
    
    def write_seqlog(self, t, seq, typ):
        if typ == 1:
            # write data packet
            self.seqnum_file.write('t={} {}\n'.format(t, seq))
        elif typ == 2:
            # write EOT packet
            self.seqnum_file.write('t={} {}\n'.format(t, "EOT"))
        elif typ == 3:
            # write SYN packet
            self.seqnum_file.write('t={} {}\n'.format(t, "SYN"))
        elif typ == 0:
            # shouldn't write ACK
            print("ERROR: shouldn't write ACK to seqnum.log (seqnum = {}).\n".format(seq))
        else:
            # unrecognized packet type
            print("ERROR: meet unrecognized packet (type = {}).\n".format(typ))
    
    def write_nlog(self, t, n):
        self.n_file.write('t={} {}\n'.format(t, n))
        
    def write_acklog(self, t, seq, typ):
        if typ == 0:
            # write ack packet
            self.ack_file.write('t={} {}\n'.format(t, seq))
        elif typ == 2:
            # write EOT packet
            self.ack_file.write('t={} {}\n'.format(t, "EOT"))
        elif typ == 3:
            # write SYN packet
            self.ack_file.write('t={} {}\n'.format(t, "SYN"))
        elif typ == 1:
            # shouldn't data ACK
            print("ERROR: shouldn't write data_packet to ack.log (seqnum = {}).\n".format(seq))
        else:
            # unrecognized packet type
            print("ERROR: meet unrecognized packet (type = {}).\n".format(typ))
        
# --------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("ne_host", type=str, help="Host address of the network emulator")
    parser.add_argument("ne_port", type=int, help="UDP port number for the network emulator to receive data")
    parser.add_argument("port", type=int, help="UDP port for receiving ACKs from the network emulator")
    parser.add_argument("timeout", type=float, help="Sender timeout in milliseconds")
    parser.add_argument("filename", type=str, help="Name of file to transfer")
    args = parser.parse_args()
   
    with open(args.filename, 'r') as send_file, open('seqnum.log', 'w') as seqnum_file, \
            open('ack.log', 'w') as ack_file, open('N.log', 'w') as n_file, \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock, \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as recv_sock:
        sender = Sender(args.ne_host, args.ne_port, args.port, args.timeout, 
            send_file, seqnum_file, ack_file, n_file, send_sock, recv_sock)
        sender.run()
