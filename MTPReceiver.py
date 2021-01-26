##  Name: Evan Rutherford
## 	  G#: G01077323
## Class: CS 455-002

# import (add more if you need)
import unreliable_channel
import struct
import sys
import socket
import zlib


# initialize and define
seqNum = 0
ackExpect = 0
ackPending = 0
packetType = 0
packetSeq = 0
packetLen = 0
packetData = 0
packetCheck = 0
packetACK = struct.Struct('!IiII')


def create_packet(seq):

	p = struct.pack('!IiI', 1, seq, 16)

	check = zlib.crc32(p)

	packet = packetACK.pack(1,seq,16,check)

	return packet, check


def extract_packet_info(data):

	# extract the packet data after receiving
	packetType = int.from_bytes(bytes(data[0:4]),"big")
	packetSeq = int.from_bytes(bytes(data[4:8]),"big")
	packetLen = int.from_bytes(bytes(data[8:12]),"big")
	packetData = data[12:1468]
	packetCheck = int.from_bytes(bytes(data[1468:1472]),"big")

	return packetType, packetSeq, packetLen, packetData, packetCheck
	

def main():
	# globals
	global seqNum

	# read the command line arguments
	if len(sys.argv) == 4:
		port = int(sys.argv[1])
		outputFile = sys.argv[2]
		logFile = sys.argv[3]
	else:
		print("command format: python.exe ./MTPReceiver.py <receiver-port> <output-file> <receiver-log-file>\n")
		return

	#initialize
	seqNum = -1
	ackExpect = -1
	numPending = 0
	ackPending = -1

	# open log file and start logging
	l = open(logFile,"w")

	print("* Start Receiver *\n")

	# open server socket and bind
	server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)	
	server.bind(('127.0.0.1',port))

	server.settimeout(0.5)

	print("* Socket open *\n")

	with open(outputFile, "w",encoding="utf8") as out_file:

		client_addr = (('127.0.0.1',65375))

		print("* Listening *\n")

		while True:
			
			try:
				# receive packet, but using our unreliable channel
				#packet_from_server, client_addr = unreliable_channel.recv_packet(s)
				data = unreliable_channel.recv_packet(server)
				packet_from_server = data[0]
				client_addr = (('127.0.0.1',65375))

				# call extract_packet_info
				packetType, packetSeq, packetLen, packetData, packetCheck = extract_packet_info(packet_from_server)
				
				seqNum = packetSeq
				if(ackExpect == -1):
					ackExpect = seqNum

				l.write("Packet received:\n \ttype = DATA;\n \tseqNum = " + str(seqNum) + ";\n \tlength = " + str(packetLen) + ";\n \tchecksum = " + str(packetCheck) + "\n")
				out_file.write(str(packetData.decode()))

			except Exception:
				#print("Timeout\n")
				pass
				

			# check for corruption and lost packets, send ack accordingly
			if(seqNum == ackExpect and numPending == 0 and ackExpect != -1):

				ackPending = seqNum
				numPending = 1
				
				try:
					# receive packet, but using our unreliable channel
					data = unreliable_channel.recv_packet(server)
					packet_from_server = data[0]
					client_addr = (('127.0.0.1',65375))

					# call extract_packet_info
					packetType, packetSeq, packetLen, packetData, packetCheck = extract_packet_info(packet_from_server)
					
					if(seqNum == packetSeq):
						raise Exception
					else:
						seqNum = packetSeq

					l.write("Packet received:\n \ttype = DATA;\n \tseqNum = " + str(packetSeq) + ";\n \tlength = " + str(packetLen) + ";\n \tchecksum = " + str(packetCheck) + "\n")
					out_file.write(str(packetData.decode()))
					ackExpect = packetSeq

				except Exception:
					numPending = 0

					packetACK, check = create_packet(ackExpect)
					unreliable_channel.send_packet(server,packetACK,client_addr)
					l.write("Packet sent:\n \ttype = ACK;\n \tseqNum = " + str(ackExpect) + ";\n \tlength = " + str(len(packetACK)) + ";\n \tchecksum = " + str(check) + "\n")
					ackExpect = -1

				finally:
					l.write("Pend / receive ...\n")
					pass


			if(seqNum == ackExpect and numPending == 1 and ackExpect != -1):
				packetACK, check = create_packet(ackPending)
				unreliable_channel.send_packet(server,packetACK,client_addr)
				l.write("Packet sent:\n \ttype = ACK;\n \tseqNum = " + str(ackPending) + ";\n \tlength = " + str(len(packetACK)) + ";\n \tchecksum = " + str(check) + "\n")

				numPending = 0

				packetACK, check = create_packet(ackExpect)
				unreliable_channel.send_packet(server,packetACK,client_addr)
				l.write("Packet sent:\n \ttype = ACK;\n \tseqNum = " + str(ackExpect) + ";\n \tlength = " + str(len(packetACK)) + ";\n \tchecksum = " + str(check) + "\n")
				ackExpect = -1

				l.write("Cumulative ack ...\n")
				pass


			if(seqNum > ackExpect and ackExpect != -1):
				packetACK, check = create_packet(ackExpect)
				unreliable_channel.send_packet(server,packetACK,client_addr)
				l.write("Packet sent:\n \ttype = ACK;\n \tseqNum = " + str(ackExpect) + ";\n \tlength = " + str(len(packetACK)) + ";\n \tchecksum = " + str(check) + "\n")
				ackExpect = -1
				
				l.write("Duplicate ack ...\n")
				pass

			if(seqNum == 685):
				break
	print("* Closing Connection *\n")
	out_file.close()	
	l.close()

main()
print("* Exit Receiver *\n")
