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
            online_users.append({"ip": message["reply_ip"], "name": message["reply_name"], "unread_messages": 0, "process": discover, "messages": []})
    except:
        discover.kill()
        pass
    
    


while True:
    for user in online_users:
        if user["process"].poll() != None:
            online_users.remove(user)
            render_online_users(online_users)
            break
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
                online_users.append({"ip": sender_ip, "name": message["sender_name"], "unread_messages": 0, "process": new_process, "messages": []})
                reply_discover = send_json(sender_ip, {"type": "REPLY_DISCOVER", "reply_ip": my_ip, "reply_name": username})
                render_online_users(online_users)
        except:
            pass        
    if len(online_users) > 0:
        render_online_users(online_users)
        user_index = input("Enter user index to send or enter R to refresh: ")
        while (not user_index.isdigit() and user_index != "R") or ((user_index != "R") and (int(user_index) < 1 or int(user_index) > len(online_users))):
            print("Invalid user index")
            user_index = input("Enter user index to send or enter R to refresh: ")
        if user_index == "R":
            continue
    
        user_index = int(user_index)
        user = online_users[user_index - 1]
        user["unread_messages"] = 0

        for message in user["messages"]:
            print(f"Chat with {user['name']}:")
            print(f"{message['sender']}: {message['message']}")
            input()
            

        message = input("Enter message: ")
        send_json(user["ip"], {"type": "MESSAGE", "sender": username, "message": message})        
    time.sleep(0.01)    