import os
import sys
import argparse
import socket
import math

from packet import Packet

# Writes the received content to file
def append_to_file(filename, data):
    file = open(filename, 'a')
    file.write(data)

def write_arrivallog(typ, seqnum):
    """
    Appends the packet information to the log file
    """
    with open('arrival.log', 'a') as arrivallog:
        if typ == 1: # data packet
            arrivallog.write('{}\n'.format(seqnum))
        elif typ == 2: # EOT packet
            arrivallog.write('{}\n'.format("EOT"))
        elif typ == 3: # SYN packet
            arrivallog.write('{}\n'.format("SYN"))
        elif typ == 0: # ACK packet
            print("ERROR: shouldn't write ack_packet to arrival.log (seqnum = {}).\n".format(seqnum))
        else:
            # unrecognized packet type
            print("ERROR: meet unrecognized packet (type = {}).\n".format(typ))
    
if __name__ == '__main__':
    # Parse args
    parser = argparse.ArgumentParser(description="Congestion Controlled GBN Receiver")
    parser.add_argument("ne_addr",type=str, help="network emulator's network address")
    parser.add_argument("ne_port", type=int, help="network emulator's UDP port number")
    parser.add_argument("recv_port", type=int, help="network emulator's network address")
    parser.add_argument("dest_filename", type=str, help="Filename to store received data")
    args = parser.parse_args()

    # Clear the output and log files
    open(args.dest_filename, 'w').close()
    open('arrival.log', 'w').close()

    expected_seq_num = 0 # Current Expected sequence number
    seq_size = 32 # Max sequence number
    max_window_size = 10 # Max number of packets to buffer
    buffer = {}  # Buffer to store the received data  key = seqnum, value = Packet
    should_receive = True
    
    print("Receiver open")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(('', args.recv_port))  # Socket to receive data
        packet = None
        addr = None

        while True:
            # Receive packets, log the seqnum, and send response
            if should_receive is True:
                packet, addr = s.recvfrom(args.recv_port)
            
            if addr is None:
                continue
            typ, seqnum, length, data = Packet(packet).decode()
            write_arrivallog(typ, seqnum)
            
            if typ == 3:
                # Got SYN
                print("Got syn request")
                syn = Packet(3, 0, 0, "")
                s.sendto(syn.encode(), (args.ne_addr, args.ne_port))
                print("Sent syn Ack")
                should_receive = True
            else:
                # not SYN
                if typ == 2:
                    # Got EOT
                    print("Got EOT packet")
                    eot = Packet(2, 0, 0, "")
                    s.sendto(eot.encode(), (args.ne_addr, args.ne_port))
                    print("EOT ACK sent, closing connection")
                    s.close()
                    break
                print(seqnum)
                if seqnum == expected_seq_num:
                    # if recived expected packet
                    print("Recived expected packet")
                    # write data to output
                    append_to_file(args.dest_filename, data)
                    # write to arrival.log
                    if len(buffer) != 0 and (seqnum + 1) % 32 in buffer:
                        # find the next expected packet in buffer
                        print("Have found the next expected packet in buffer...")
                        packet = buffer[(seqnum + 1) % 32]
                        # removed that packet
                        del buffer[(seqnum + 1) % 32]
                        expected_seq_num = (expected_seq_num + 1) % 32 
                        should_receive = False
                        continue
                    else:
                        # next expected packet not in buffer
                        ack = Packet(0, seqnum, 0, "")
                        # send ack back with seqnum = most last packet written to disk
                        s.sendto(ack.encode(), (args.ne_addr, args.ne_port))
                        print("Sent back ack {}\n".format(seqnum))
                        expected_seq_num = (expected_seq_num + 1) % 32
                        should_receive = True
                        continue
                else:
                    # if not recived expected packet
                    print("Recived non-expected packet")
                    next_ten_seqnum = []
                    for i in range(expected_seq_num, expected_seq_num + 11):
                        next_ten_seqnum.append(i % 32)
                    if seqnum in next_ten_seqnum:
                        # sequence number within next 10 sequence number, store into buffer
                        print("store into buffer")
                        buffer[seqnum] = packet
                    # send an ACK for the most recently received in-order packet
                    ack_seq = ((expected_seq_num - 1) + 32) % 32
                    ack = Packet(0, ack_seq, 0, "")
                    print("send ACK back...")
                    s.sendto(ack.encode(), (args.ne_addr, args.ne_port))
                    should_receive = True
                    continue
