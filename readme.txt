This program was created to work with both Windows and Linux operating systems.
But windows subprocesses are unpredictable, therefore it only consistently works with Linux.
I tested the application with Ubuntu 20.04 and python 3.8.10.

I created a virtual enviroment for the application but its not useful since I didn't use any external libraries.
To run the application use the following command on ubuntu: 
python3 program.py

After entering your name the application will discover any other computers running the same app within your network.
Upon discovery, the online users will be listed. You can choose a user by their index and send messages to them.
Each message recieve, message send, user discovery and user disconnection will cause re renders. This makes the app display everything almost in real time.
