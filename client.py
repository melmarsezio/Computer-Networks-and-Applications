# Python version 3.7.4
# Created by: Chencheng Xie z5237028
import sys
import socket
import os
import time
import threading
import json

# check commandline input format
if len(sys.argv) != 4:
    print("Required arguments: server_IP server_port client_udp_port")
    sys.exit()
server_IP = sys.argv[1]
server_port = int(sys.argv[2])
client_udp_port = int(sys.argv[3])

zid = 'z5237028'
# define contactlog expired time
logExp = 3 # mins
# state of whether client should be shutdown or not
shutdown = False
# initialize tempID
tempID = None
# authentication process
def login():
    username = input('Username: ')
    while username == '':
        print('Username can not be empty')
        username = input('Username: ')
    sock.send(username.encode())

    while True:
        password = input('Password: ')
        while password == '':
            print('Password can not be empty')
            password = input('Password: ')
        sock.send(password.encode())
        msg = sock.recv(1024).decode()
        print(msg)
        if 'Welcome' in msg: # successfully login
            return True
        elif 'block' in msg: # account is blocked
            return False
        elif 'Invalid Username' in msg: # the username is invalid, login process terminate
            return False
# listening to other clients beacon
def beaconListen():
    while True:
        try:
            beaconMsg = beaconSocket.recv(1024).decode()
            print('received beacon:')
            print(beaconMsg)
            now = sec2str(time.time()) # get now in formated time string
            print(f'Current time is: {now}')
            if validTime(now, beaconMsg): # check Beacon message validation
                print('The beacon is valid')
                # modify the contactLog file
                contactLogFile = open(f'{zid}_contactlog.txt')
                txt = contactLogFile.read()
                contactLogFile.close()
                contactLogFile = open(f'{zid}_contactlog.txt','a')
                if txt:
                    contactLogFile.write(f'\n{beaconMsg}')
                else:
                    contactLogFile.write(f'{beaconMsg}')
                contactLogFile.close()
                contactLogExp.append(time.time()+logExp*60) # add expired timestamp to the list
            else:
                # Beacon message validation didn't go through
                print('The beacon is invalid.')
        except OSError:
            break
# convert formated time string to seconds since Epoch
def str2sec(timeString):
    return time.mktime(time.strptime(timeString,'%d/%m/%Y %H:%M:%S'))
# convert seconds since Epoch to formated time string
def sec2str(sec):
    return time.strftime('%d/%m/%Y %H:%M:%S',time.localtime(sec))
# check if a beacon msg is valid
def validTime(now, beaconMsg):
    beaconMsg = beaconMsg.split(',')
    timestampS = beaconMsg[1]
    timestampE = beaconMsg[2]
    nowSec = str2sec(now)
    if nowSec >= str2sec(timestampS) and nowSec <= str2sec(timestampE):
        return True
    else:
        return False
# check if any Log in contactLog is expired and delete them
def checkExp():
    global contactLogExp
    global shutdown
    while True:
        # get number of expired contactLog
        numOfDet = 0
        for LogExp in contactLogExp:
            if LogExp <= time.time(): # if expired timestamp is older than current time
                numOfDet += 1 # one more Log to delete
            else:
                break # logs are stored from oldest to newest, so if any log is not expired, the following logs must be valid
        # delete expired contact log
        if numOfDet:
            contactLogExp = contactLogExp[numOfDet:]
            contactLogFile = open(f'{zid}_contactlog.txt')
            contactLogtxt = contactLogFile.read().split('\n')
            contactLogFile.close()
            contactLogtxt = contactLogtxt[numOfDet:]
            contactLogFile = open(f'{zid}_contactlog.txt','w')
            contactLogFile.write('\n'.join(contactLogtxt))
            contactLogFile.close()
        time.sleep(0.1)
        if shutdown:
            break
# this function dumps data into json file
def packet(commandType, numOfSend=0, numOfRecv=0, data=''):
    sendData = {
        'commandType' : commandType,# the type of commands:'DT','UC','LO'
        'numOfSend' : numOfSend,    # indicate how many file will be sent next
        'numOfRecv' : numOfRecv,    # indicate how many file are expected to be recv
        'data' : data               # stores the actual payload
    }
    sendData = json.dumps(sendData)
    return sendData
# connect to server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((server_IP, server_port))
# authentication
if not login():
    # if authentication fails shutdown connectino and exit
    sock.close()
    sys.exit()
# connect beacon listening socket
beaconSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
beaconSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
beaconSocket.bind(('localhost', client_udp_port))
# prepare zid_contact_log.txt
contactLogFile = open(f'{zid}_contactlog.txt','w')
contactLogFile.close()
# stores the expire timestamp of each contactLog in order
contactLogExp = []
# thread for UDP listening
listenThread = threading.Thread(name="beaconThread",target=beaconListen)
# thread for checking expired contact log
checkExpThread = threading.Thread(name="checkExpThread",target=checkExp)
listenThread.start()
checkExpThread.start()
# main thread
while True:
    # take commands from standard input
    command = input()
    try:
        if command == 'Download_tempID':
            sendData = packet('DT',numOfRecv=1)
            sock.send(sendData.encode()) # send tempID request to server
            recvData = json.loads(sock.recv(1024).decode()) # receive tempID info generated by the server
            tempIDMsg = recvData['data'].split()
            tempID = tempIDMsg[1]
            timestampS = tempIDMsg[2]+' '+tempIDMsg[3] # start timestamp
            timestampE = tempIDMsg[4]+' '+tempIDMsg[5] # end timestamp
            print(f'TempID: {tempID}')
        elif command == 'Upload_contact_log':
            # open up contactLog file and see how many Logs in the LogFile
            logFile = open(f'{zid}_contactlog.txt')
            logList = logFile.read().split('\n')
            numOfLog = len(logList)
            logFile.close()
            # if logList[0] == '', the contactLog file is empty
            if not logList[0]:
                numOfLog = 0
            # send upload request with the number of Log will be sent
            sendData = packet('UC',numOfSend=numOfLog,numOfRecv=1)
            sock.send(sendData.encode())
            # make sure numOfRecv_Server matches sendData['numOfSend']
            # (client and server agree on number of logs)
            numOfRecv_Server = sock.recv(1024).decode()
            for i in range(numOfLog):
                logsplit = logList[i].replace(',',' ').split()
                logMsg = f'{logsplit[0]},{logsplit[1]} {logsplit[2]},{logsplit[3]} {logsplit[4]};'
                print(logMsg)
                sendData = packet('UC',numOfRecv=1,data=logMsg)
                sock.send(sendData.encode())
                # ack from server
                ACK = json.loads(sock.recv(1024).decode())['data']
        elif 'Beacon' in command and len(command.split())==3: # Beacon has to be in the format "Beacon IP UDP_port"
            if not tempID:
                # we called Beacon before "Download_tempID" which in reality is forbidden
                print('tempID unknown, can not Beacon neighbors')
                continue
            command = command.split() # parse command and get IP and UDP_port
            beaconIP = command[1]
            beaconPort = int(command[2])
            # send Beacon message to "IP/UDP_port"
            beaconClient = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            beaconClient.connect((beaconIP, beaconPort))
            beaconClient.send(f'{tempID},{timestampS},{timestampE},{1}'.encode())
            beaconClient.close()
        elif command == 'logout':
            # tell server I want to logout, so server can close down the connection
            sendData = packet('LO')
            sock.send(sendData.encode())
            sock.close() # this will terminate socket with client
            beaconSocket.close() # this will terminate the beacon listening socket
            shutdown = True # this will terminate the Log expiration check (3 min checking) thread
            break
        else:
            print('Error. Invalid command')
    except ConnectionResetError:
        # this happens when server is disconnected (ctrl C)
        # and reconnected, everything needs to start over again
        print('Server disconnected')
        sock.close()
        beaconSocket.close()
        shutdown = True
        break
