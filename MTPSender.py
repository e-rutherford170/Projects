##  Name: Evan Rutherford
## 	  G#: G01077323
## Class: CS 455-002

# import (add more if you need)
import threading
import unreliable_channel
import zlib
import socket
import struct
import sys

## define and initialize
global windowSize
global windowEnd
global seqNum
global ack_seqNum # oldest ack seq num
global ack_data

windowSeq = [-1] * 700
windowSend = [-1] * 700
windowStart = 0
packetData = struct.Struct('!IiI1456sI')
packetCheck = 0
ack_seqNum = -1
buf = [str] * 686
bufSeq = [-1] * 686

## we will need a lock to protect against concurrent threads
lock = threading.Lock()


def create_packet(file,sNum):
	# Create ACK packet
	
	data = struct.pack('!III1456s',0,sNum,1472, bytes(file.encode('utf-8')))

	packetCheck = zlib.crc32(data)

	packet = packetData.pack(0,sNum,1472, bytes(file.encode('utf-8')),packetCheck)

	return packet, packetCheck


def extract_packet_info(packet):
	# extract the packet data after receiving
	packetACK = struct.unpack('!IIII',packet)
	
	return packetACK


def	receive_thread(socket,send_log,winStart,winEnd,ackSeq):
	# global variables
	global ack_seqNum
	global windowStart
	global windowEnd
	global windowSeq
	global windowSend

	# initialize
	ack_seqNum = ackSeq
	windowStart = winStart
	windowEnd = winEnd
	packetseqNum = -1

	# Open log
	l = open(send_log,"a")

	try:
		# receive packet, but using our unreliable channel
		data = unreliable_channel.recv_packet(socket)
		packet_from_server = data[0]

		# call extract_packet_info
		packetACK = extract_packet_info(packet_from_server)
		packetType = packetACK[0]
		packetseqNum = packetACK[1]
		packetLen = packetACK[2]
		packetCheck = packetACK[3]

		# check for corruption, take steps accordingly
		status = "NOT CORRUPT"
		packet = struct.pack('!III', packetType, packetseqNum, packetLen)
		corrupt = zlib.crc32(packet)
		if(corrupt != packetCheck):
			status = "CORRUPT"	

		# update window size
		if(packetseqNum == ack_seqNum):
			ack_seqNum += 1
			windowStart += 1
			windowEnd += 1
			
		l.write("\nPacket received: type = ACK, seqNum = " + str(packetseqNum) + "; length = " + str(packetLen) + "; checksum_in_packet = " + str(packetCheck) + "; checksum_calculated = " + str(corrupt) +
		"; status = " + str(status) + ";\n\n")

		#print("window START = " + str(windowStart) + "; window END = " + str(windowEnd) + "\n")

	except Exception:
		#print("Timeout\n")
		pass

	l.close()

	return ack_seqNum, windowStart, windowEnd


def main():
	# global variables
	global windowSend
	global windowSeq
	global windowSize
	global windowStart
	global windowEnd
	global ack_seqNum
	global bufSeq
	global buf
	
	# read the command line arguments
	if len(sys.argv) == 6:
		ip = sys.argv[1]
		port = int(sys.argv[2])
		windowSize = int(sys.argv[3])
		inputFile = sys.argv[4]
		logFile = sys.argv[5]
		
		print("Command format correct\n")
	else:
		print("command format: python.exe ./MTPSender.py <receiver-IP> <receiver-port> <window-size> <input-file> <sender-log-file>\n")
		return

	# open log file and start logging
	l = open(logFile,"w")

	print("* Start Sender *\n")

	# open client socket and bind
	c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	c.bind((ip,65375))
	addr = (ip,port)
	c.settimeout(0.5)

	print("* Socket open *\n")

	# initialize variables
	seqNum = 0
	windowStart = 0
	ack_seqNum = 0
	windowEnd = windowSize - 1
	triple_dup = 0

	# start receive thread
	#recv_thread = threading.Thread(target=receive_thread,args=(c,logFile,windowStart,windowEnd))
	#recv_thread.start()

	# open and read the input file
	with open(inputFile, "r",encoding="utf8") as in_file:

		data = in_file.read(1456) # read 1456 bytes (1472 - MTP header)
		ack_data = data

		print("* Reading data and sending packets *\n")

		# infinite loop until all of data is read
		while True:
			
			# save oldest ack data and seqNum
			if(seqNum == windowStart):
				ack_seqNum = seqNum
				ack_data = data
			
			# queue to buffer
			if(windowEnd < seqNum or seqNum < windowStart):
				buf.insert(seqNum,data)
				bufSeq.append(seqNum)
				

			# Send packets from buffer if exists and in window 
			if(windowEnd >= seqNum and windowStart <= seqNum and bufSeq.count(-1) != 686):

				for a in bufSeq:

					if(a == -1):
						continue

					if(windowEnd >= a or windowStart <= a):
						try:
							bufData = buf.pop(a)
						except IndexError:
							break

						packetData, packetCheck = create_packet(bufData,a)
						l.write("Packet created (buffer) ...\n")
						windowSeq.insert(a,a)
						windowSend.insert(a,1)

						try:
							# send packets to server using our unreliable_channel.send_packet() 
							unreliable_channel.send_packet(c,packetData,addr)
							l.write("Packet sent: type = DATA; seqNum = " + str(a) + "; length = " + str(len(packetData)) + "; checksum = " + str(packetCheck) + "\n")
							windowSend.insert(a,0)

							# update the window size
							l.write("Window state: [")
							for x in range(windowStart,windowEnd+1):
								if(windowSeq[x] != -1):	
									l.write(str(windowSeq[x]) + "(" + str(windowSend[x]) + "), ")
							l.write("]\n")
						except Exception:
							l.write("Timeout buffer : seqNum = " + str(a) + "\n")
							resend = 0
							while(resend == 0):
								try:
									AckData, AckCheck = create_packet(ack_data,ack_seqNum)
									l.write("Packet created (oldest ack) ...\n")
									unreliable_channel.send_packet(socket,ack_data,addr)
									l.write("Packet sent: type = DATA; seqNum = " + str(ack_seqNum) + "; length = " + str(len(AckData)) + "; checksum = " + str(AckCheck) + "\n")
									windowSend.insert(ack_seqNum,0)

									# update the window size
									l.write("Window state: [")
									for x in range(windowStart,windowEnd+1):
										if(windowSeq[x] != -1):
											l.write(str(windowSeq[x]) + "(" + str(windowSend[x]) + "), ")
									l.write("]\n")

									resend = 1						
								except Exception:
									l.write("Timeout : seqNum =" + str(ack_seqNum) + "\n")

			
			# Send packets if in window range
			if(windowEnd >= seqNum and windowStart <= seqNum):
				#print(seqNum)
				packetData, packetCheck = create_packet(data,seqNum)
				l.write("Packet created (send) ...\n")
				windowSeq.insert(seqNum,seqNum)
				windowSend.insert(seqNum,1)

				try:
					# send packets to server using our unreliable_channel.send_packet() 
					unreliable_channel.send_packet(c,packetData,addr)
					l.write("Packet sent: type = DATA; seqNum = " + str(seqNum) + "; length = " + str(len(packetData)) + "; checksum = " + str(packetCheck) + "\n")
					windowSend.insert(seqNum,0)

					# Show the window state
					l.write("Window state: [")
					for x in range(windowStart,windowEnd+1):
						if(windowSeq[x] != -1):
							l.write(str(windowSeq[x]) + "(" + str(windowSend[x]) + "), ")
					l.write("]\n")
					
				except Exception:
					print("Timeout send : seqNum = " + str(seqNum) + "\n")
					resend = 0
					while(resend == 0):
						try:
							AckData, AckCheck = create_packet(ack_data,ack_seqNum)
							l.write("Packet created (oldest ack) ...\n")
							unreliable_channel.send_packet(socket,ack_data,addr)
							l.write("Packet sent: type = DATA; seqNum = " + str(ack_seqNum) + "; length = " + str(len(AckData)) + "; checksum = " + str(AckCheck) + "\n")
							windowSend.insert(ack_seqNum,0)

							# Show the window state
							l.write("Window state: [")
							for x in range(windowStart,windowEnd+1):
								if(windowSeq[x] != -1):
									l.write(str(windowSeq[x]) + "(" + str(windowSend[x]) + "), ")
							l.write("]\n")
							resend = 1	

						except Exception:
							#print("retry sending oldest ack\n")
							pass

			# start receiving
			temp_ack = ack_seqNum
			l.close()
			ack_seqNum, windowStart, windowEnd = receive_thread(c,logFile,windowStart,windowEnd,ack_seqNum)
			l = open(logFile,"a")

			if(temp_ack == ack_seqNum):
				triple_dup += 1	 # duplicate ACK count

			# resend oldest unacked packet
			if(triple_dup == 3):
				resend = 0
				AckData, AckCheck = create_packet(ack_data,ack_seqNum)
				l.write("Packet created (oldest ack) ...\n")

				while(resend == 0):
						try:
							unreliable_channel.send_packet(socket,ack_data,addr)
							l.write("Packet sent: type = DATA; seqNum = " + str(ack_seqNum) + "; length = " + str(len(AckData)) + "; checksum = " + str(AckCheck) + "\n")
							windowSend.insert(ack_seqNum,0)

							# update the window size
							l.write("Window state: [")
							for x in range(windowStart,windowEnd+1):
								if(windowSeq[x] != -1):
									l.write(str(windowSeq[x]) + "(" + str(windowSend[x]) + "), ")
							l.write("]\n")
							resend = 1	

						except Exception:
							l.write("Timeout : seqNum = " + str(ack_seqNum) + "\n")
							pass

				triple_dup = 0

			# only continue to read data if currently in window
			if(seqNum >= windowStart and seqNum < windowEnd):
				data = in_file.read(1456)
				seqNum += 1
			
			# Quit once all packets have been sent
			if(seqNum == 686):
				break

		in_file.close()
		l.write("Sent all " + str(seqNum) + " packets! ...\n")
		l.close()
	
	print("* All packets/data sent *\n")
	c.close()
	return

main()
print("* Exit sender *\n")
