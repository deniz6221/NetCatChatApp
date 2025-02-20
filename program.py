import json
import os
import subprocess
import time
import socket

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

def send_json(ip, message):
    messageJson = json.dumps(message)
    message = subprocess.Popen([nc_command, ip, "40000"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    message.stdin.write(messageJson.encode())
    message.stdin.close()

username = input("Enter your name: ")
server = subprocess.Popen([nc_command, '-lknp', '40000'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

my_ip = get_ip()
ip_subnet = get_ip_subnet(my_ip)
print("My IP:", my_ip)
print("IP Subnet:", ip_subnet)

discoverJson = json.dumps({"type": "DISCOVER", "sender_ip": my_ip, "sender_name": username})

online_users = []
discovers = []
for i in range(39,40):
    current_discover = ip_subnet + "." + str(i)
    if current_discover == my_ip:
        continue
    discover = subprocess.Popen([nc_command, current_discover, "40000"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    discover.stdin.write(discoverJson.encode())
    discovers.append(discover)

for discover in discovers:
    line = discover.stdout.readline().decode()
    try:
        message = json.loads(line.strip())
        if (message["type"] == "REPLY_DISCOVER"):
            online_users.append({"ip": message["reply_ip"], "name": message["reply_name"], "unread_messages": 0})
    except:
        discover.kill()
        pass        

    


while True:
    output = server.stdout.readline().decode()
    if output:
        try:
            message = output.strip()
            print(message)
            message = json.loads(message)
            message_type = message["type"]
            if (message_type == "DISCOVER"):
                online_users.append({"ip": message["sender_ip"], "name": message["sender_name"], "unread_messages": 0})
                reply_discover = send_json(message["sender_ip"], {"type": "REPLY_DISCOVER", "reply_ip": my_ip, "reply_name": username})
                render_online_users(online_users)
        except:
            pass        

    time.sleep(0.01)    