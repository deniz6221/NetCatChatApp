import json
import os
import subprocess
import time
import re
import threading
from datetime import datetime
global nc_command
nc_command = "ncat" if os.name == "nt" else "nc"


def get_ip():
    try:
        if os.name == "nt":  #Windows
            output = subprocess.run(["ipconfig"], capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout
            ip_addresses = re.findall(r'IPv4 Address[.\s]+: (\d+\.\d+\.\d+\.\d+)', output)
            gateways = re.findall(r'Default Gateway[.\s]+: (\d+\.\d+\.\d+\.\d+)', output)

            for ip in ip_addresses:
                if any(gw.startswith(ip.rsplit('.', 1)[0]) for gw in gateways):
                    return ip  

            return ip_addresses[0] if ip_addresses else "192.168.1.1"

        else:  # Linux/macOS
            output = subprocess.run(["ip", "-4", "addr", "show"], capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout
            matches = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)/\d+', output)

            for ip in matches:
                if not ip.startswith("127."):  
                    return ip

            return "192.168.1.1"
    
    except Exception:
        pass
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
    try:
        messageJson = json.dumps(message) + "\n"
        user["process"].stdin.write(messageJson.encode())
        user["process"].stdin.flush()
    except:
        pass    

username = ""
while username.strip() == "":
    username = input("Enter your name: ")
    
server = subprocess.Popen([nc_command, '-lknp', '40000'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

my_ip = get_ip()
ip_subnet = get_ip_subnet(my_ip)

discoverJson = json.dumps({"type": "DISCOVER_REQ", "sender_ip": my_ip, "sender_name": username}) + "\n"

online_users = []
print("Discovering users in the network, this might take a while...")

def discover_users(ip_start, ip_end):
    discovers = []
    for i in range(ip_start, ip_end):
        current_discover = ip_subnet + "." + str(i)
        if current_discover == my_ip:
            continue
        discover = subprocess.Popen([nc_command ,"-w", "1" , current_discover, "40000"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        discover.stdin.write(discoverJson.encode())
        discover.stdin.flush()

        discovers.append(discover)

    time.sleep(1)

    for discover in discovers:
        try:
            discover.stdin.close()
        except:
            pass
        finally:    
            discover.wait()

last = 0
for i in range(1, 255, 50):
    discover_users(last, i)
    last = i

discover_users(last, 255)

    
    
renderState = 1
active_user = -1
thread_lock = threading.Lock()



def renderThread():
    global renderState
    global active_user
    while True:
        with thread_lock:
            if renderState == 1:
                os.system('cls' if os.name == 'nt' else 'clear')
                render_online_users(online_users)
                print()
                if (len(online_users) != 0):
                    print("Enter user index to view chat: ")
                renderState = 0
            elif renderState == 3:
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"Chat with {online_users[active_user]['name']}:")
                for message in online_users[active_user]["messages"]:
                    print(f"{message['sender']}: {message['message']} ({datetime.fromtimestamp(int(message['timestamp'])).strftime('%d.%m.%Y %H:%M:%S')})")
                print()    
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
                message = json.loads(message)
                message_type = message["type"]
                if (message_type == "DISCOVER_REQ"):
                    sender_ip = message["sender_ip"]
                    new_process = subprocess.Popen([nc_command, sender_ip, "40000"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    with thread_lock:
                        online_users.append({"ip": sender_ip, "name": message["sender_name"], "unread_messages": 0, "process": new_process, "messages": []})
                        send_json(online_users[-1], {"type": "DISCOVER_RESP", "responder_ip": my_ip, "responder_name": username})
                        if renderState == 0:
                            renderState = 1
                elif (message_type == "MESSAGE"):

                    payload = message["payload"]
                    sender_name = message["sender_name"]

                    with thread_lock:
                        for user in online_users:
                            if user["name"] == sender_name:
                                user["messages"].append({"sender": sender_name, "message": payload, "timestamp": message["timestamp"]})
                                if renderState != 2 and renderState != 3:
                                    user["unread_messages"] += 1
                                    renderState = 1
                                else:    
                                    renderState = 3 
                                break         
                elif (message_type == "DISCOVER_RESP"):
                    sender_ip = message["responder_ip"]
                    sender_name = message["responder_name"]
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
                online_users[active_user]["unread_messages"] = 0
                renderState = 3
            else:
                message = userInput
                if message == "Q":
                    renderState = 1
                else:
                    online_users[active_user]["messages"].append({"sender": username, "message": message, "timestamp": f"{int(time.time())}"})
                    send_json(online_users[active_user], {"type": "MESSAGE", "sender_name": username, "payload": message, "timestamp": f"{int(time.time())}"})
                    renderState = 3
        time.sleep(0.5)        

serverThread = threading.Thread(target=serverThread)
serverThread.daemon = True
serverThread.start()



disconnectThread = threading.Thread(target=disconnectThread)
disconnectThread.daemon = True
disconnectThread.start()

inputThread = threading.Thread(target=inputThread)
inputThread.daemon = True
inputThread.start()

time.sleep(1)
os.system('cls' if os.name == 'nt' else 'clear')

renderThread = threading.Thread(target=renderThread)
renderThread.daemon = True
renderThread.start()

inputThread.join()