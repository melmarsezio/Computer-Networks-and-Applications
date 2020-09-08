# Python version 3.7.4
# Created by: Chencheng Xie z5237028
import sys
import socket
import os
import time
import threading
import random
import json

# check commandline input format
if len(sys.argv) != 3:
    print("Required arguments: server_port block_duration")
    sys.exit()
# check local support file
try:
    credFile = open('credentials.txt')
    cred_list = credFile.read().split('\n')
except FileNotFoundError:
    print('"credentials.txt" loss!! Check local file storage')
    sys.exit()
# get port number and block duration
server_port = int(sys.argv[1])
block_duration = int(sys.argv[2])
# define number of fail login allowed and how long the tempID will be valid
failAttempt = 3
tempIDduration = 15
# this function converts formated time string to seconds since Epoch
def str2sec(timeString):
    return time.mktime(time.strptime(timeString,'%d/%m/%Y %H:%M:%S'))
# this function converts seconds since Epoch to formated time string
def sec2str(sec):
    return time.strftime('%d/%m/%Y %H:%M:%S',time.localtime(sec))
# this function maps tempID into corresponding username
def checkLog(log, tempIDtext):
    log = log[:-1].split(',')
    tempID = log[0]
    timestampS = log[1]
    timestampE = log[2]
    for record in tempIDtext:
        if tempID in record:
            record = record.split()
            return f'{record[0]},{timestampS},{tempID};'
    #if tempID is unknown, return None
    return
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
# test client's authentication
def login(clientSock):
    try:
        username = clientSock.recv(1024).decode() # get username
        while True:
            password = clientSock.recv(1024).decode() # get password
            if password == '': # when client disconnect
                return False
            if time.time()-cred_state[username][0]<block_duration: # account still in block
                clientSock.send('Your account is blocked due to multiple login failures. Please try again later'.encode())
                return False
            else:
                if cred_password[username] != password: # incorrect password
                    cred_state[username][1] -= 1 # waste one attempt
                    if cred_state[username][1] == 0: # waste all attempt
                        cred_state[username][1] = failAttempt # reset fail attempt countdown on block
                        cred_state[username][0] = time.time() # reset block timestamp
                        clientSock.send('Invalid Password. Your account has been blocked. Please try again later'.encode())
                        return False
                    else:
                        clientSock.send('Invalid Password. Please try again'.encode())
                else:
                    # reset fail attempt countdown on successful login
                    cred_state[username][1] = failAttempt
                    clientSock.send('Welcome to the BlueTrace Simulator!'.encode())
                    return username # successfully login
    except KeyError: # when client input unknown username
        print(f'Unknown User Error')
        clientSock.send('Invalid Username'.encode())
    except ConnectionResetError:
        print(f'{username} ConnectionResetError')
    except BrokenPipeError:
        print(f'{username} BrokenPipeError')
    except OSError:
        print(f'{username} OSError')
# threadFunction that communicate with client
def ClientThread(clientSock, addr):
    # authentication returns username if successfully login
    username = login(clientSock)
    if not username: # if login fails, usename is "None", close down this connection
        clientSock.close()
        return

    while True:
        # take commands from client
        recvData = clientSock.recv(1024).decode()
        if recvData == '':
            break # this means client disconnected (by ctrl D or broken internet)
        recvData = json.loads(recvData)
        if recvData['commandType'] == 'DT':
            try:    # prepare tempIDs.txt
                tempIDFile = open('tempIDs.txt','r')
                tempIDtext = tempIDFile.read()
                tempIDFile.close()
            except FileNotFoundError:
                tempIDtext = ''
            now = time.time() # get current time
            random.seed(now)  # and use it as a seed to generate tempID
            # try to generated a tempID
            tempID = ''.join([str(random.randint(0,9)) for i in range(20)])
            while tempID in tempIDtext: # if it's a duplicate, generate another one
                tempID = ''.join([str(random.randint(0,9)) for i in range(20)])
            print(f'user: {username}\nTempID: {tempID}')
            # send back tempID with validation time frame to synchronize tempID validatoin
            tempIDMsg = f'{username} {tempID} {sec2str(now)} {sec2str(now+tempIDduration*60-1)}'
            if recvData['numOfRecv']: # send back tempID is client expect server to send something
                sendData = packet('DT',data=tempIDMsg)
                clientSock.send(sendData.encode())
            tempIDFile = open('tempIDs.txt','a') # append new tempID to tempIDs.txt
            if tempIDtext:
                tempIDFile.write(f'\n{tempIDMsg}')
            else:
                tempIDFile.write(tempIDMsg)
            tempIDFile.close()
        elif recvData['commandType'] == 'UC':
            print(f'received contact log from {username}')
            # let client know my understanding on the number of Logs is correct
            numOfLog = recvData['numOfSend']
            sendData = packet('UC',numOfRecv=numOfLog)
            clientSock.send(sendData.encode())
            if numOfLog == 0: # if numOfLog = 0, client's contactLog is empty
                print('empty contact log')
            else:
                logList = [] # store Logs for later check
                for i in range(numOfLog):
                    log = json.loads(clientSock.recv(1024).decode())['data']
                    clientSock.send(packet('UC',data='ACK').encode()) # send ACK after every Log
                    print(log)
                    logList.append(log) # add log to logList
                try: # try to get the list of all usernames with tempIDs
                    tempIDFile = open('tempIDs.txt','r')
                    tempIDtext = tempIDFile.read().split('\n')
                    tempIDFile.close()
                except FileNotFoundError:
                    tempIDtext = []
                # check contact log
                print('Contact log checking')
                for log in logList:
                    checkResult = checkLog(log,tempIDtext) # find the username for each tempID
                    if checkResult:
                        print(checkResult)
                    else: # if any tempID can not corresponding to a username
                        tempID = log.split(',')[0]
                        print(f'{tempID} not found') # show that this tempID is not understood
        elif recvData['commandType'] == 'LO':
            print(f'{username} logout')
            clientSock.close() # close down socket
            break
    clientSock.close()
# stores all username--password pairs
cred_password = {}
# stores [blockedTime, fail attempt countdown]
cred_state = {}
initial_time = time.time()
for cred in cred_list:
    cred = cred.split()
    cred_password[cred[0]] = cred[1]
    cred_state[cred[0]] = [initial_time-block_duration, failAttempt]
# create socket object
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# bind the socket to the port
sock.bind(('',server_port))
# listening for incoming request
sock.listen(1)
# main thread
while True:
    clientSock, addr = sock.accept() # wait for new connection
    # thread for each connection
    thread = threading.Thread(name="clientThread",target=ClientThread,args=(clientSock,addr))
    thread.start()

sock.close()        # close down server socket
credFile.close()    # close down credentials.txt
