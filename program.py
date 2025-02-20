import json
import os
import subprocess
import time
import socket
import threading

global nc_command
nc_command = "ncat" if os.name == "nt" else "nc"


def get_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  
            return s.getsockname()[0] 
    except Exception as e:
        return "192.168.1.1"
    
def get_ip_subnet(ip):
    return ".".join(ip.split(".")[:-1])

def render_online_users(online_users):
    print("Online Users:")
    for i, user in enumerate(online_users):
        if (user["unread_messages"] == 0):
            print(f"{i + 1}. {user['name']}")
        else:    
            print(f"{i + 1}. {user['name']} ({user['unread_messages']} unread messages)")


def send_json(user, message):
    messageJson = json.dumps(message) + "\n"
    user["process"].stdin.write(messageJson.encode())
    user["process"].stdin.flush()


username = input("Enter your name: ")
server = subprocess.Popen([nc_command, '-lknp', '40000'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

my_ip = get_ip()
ip_subnet = get_ip_subnet(my_ip)
print("My IP:", my_ip)
print("IP Subnet:", ip_subnet)

discoverJson = json.dumps({"type": "DISCOVER", "sender_ip": my_ip, "sender_name": username}) + "\n"

online_users = []

for i in range(39,40):
    current_discover = ip_subnet + "." + str(i)
    if current_discover == my_ip:
        continue
    discover = subprocess.Popen([nc_command, current_discover, "40000"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    discover.stdin.write(discoverJson.encode())
    discover.stdin.flush()
    discover.kill()

    
renderState = 1
active_user = -1
thread_lock = threading.Lock()


def renderThread():
    global renderState
    global active_user
    while True:
        with thread_lock:
            if renderState == 1:
                print("\n\n\n")
                render_online_users(online_users)
                if (len(online_users) != 0):
                    print("Enter user index to view chat: ")
                renderState = 0
            elif renderState == 3:
                print("\n\n\n")
                print(f"Chat with {online_users[active_user]['name']}:")
                for message in online_users[active_user]["messages"]:
                    print(f"{message['sender']}: {message['message']}")
                print("Enter message or enter Q to go back to previous menu: ")    
                renderState = 2            
        time.sleep(0.3)

def disconnectThread():
    global renderState
    global active_user
    while True:
        with thread_lock:
            for i, user in enumerate(online_users):
                if user["process"].poll() != None:
                    online_users.remove(user)
                    if renderState == 0:
                        renderState = 1
                    if (renderState == 2 or renderState == 3) and active_user == i:
                        renderState = 1
                    break
        time.sleep(1)

def serverThread():
    global renderState
    global active_user
    while True:
        output = server.stdout.readline().decode()
        if output:
            try:
                message = output.strip()
                print(message)
                message = json.loads(message)
                message_type = message["type"]
                if (message_type == "DISCOVER"):
                    sender_ip = message["sender_ip"]
                    new_process = subprocess.Popen([nc_command, sender_ip, "40000"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print("Discover message received")
                    
                    with thread_lock:
                        print("Lock acquired for online users list")
                        online_users.append({"ip": sender_ip, "name": message["sender_name"], "unread_messages": 0, "process": new_process, "messages": []})
                        send_json(online_users[-1], {"type": "REPLY_DISCOVER", "reply_ip": my_ip, "reply_name": username})
                        if renderState == 0:
                            renderState = 1
                elif (message_type == "MESSAGE"):
                    sender_ip = message["sender_ip"]
                    message = message["message"]
                    sender_name = message["sender_name"]
                    with thread_lock:
                        for user in online_users:
                            if user["ip"] == sender_ip:
                                user["messages"].append({"sender": sender_name, "message": message})
                                if renderState != 2 and renderState != 3:
                                    user["unread_messages"] += 1
                                else:    
                                    renderState = 3  
                elif (message_type == "REPLY_DISCOVER"):
                    sender_ip = message["reply_ip"]
                    sender_name = message["reply_name"]
                    new_process = subprocess.Popen([nc_command, sender_ip, "40000"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    with thread_lock:
                        online_users.append({"ip": sender_ip, "name": sender_name, "unread_messages": 0, "process": new_process, "messages": []})
                        if renderState == 0:
                            renderState = 1
            except:
                pass

def inputThread():
    global renderState
    global active_user
    while True:
        userInput = input()
        with thread_lock:
            if renderState == 0 or renderState == 1:
                if len(online_users) <= 0:
                    continue
                if (not userInput.isdigit()) or (int(userInput) < 1 or int(userInput) > len(online_users)):
                    print("Invalid user index")
                    continue
                active_user = int(userInput) - 1
                renderState = 3
            else:
                message = userInput
                if message == "Q":
                    renderState = 1
                else:
                    online_users[active_user]["messages"].append({"sender": username, "message": message})
                    send_json(online_users[active_user], {"type": "MESSAGE", "sender_ip": my_ip, "sender_name": username, "message": message})
                    renderState = 3
        time.sleep(0.5)        

serverThread = threading.Thread(target=serverThread)
serverThread.daemon = True
serverThread.start()

renderThread = threading.Thread(target=renderThread)
renderThread.daemon = True
renderThread.start()

disconnectThread = threading.Thread(target=disconnectThread)
disconnectThread.daemon = True
disconnectThread.start()

inputThread = threading.Thread(target=inputThread)
inputThread.daemon = True
inputThread.start()

inputThread.join()