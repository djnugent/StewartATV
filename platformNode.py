import socket
import time
import json
import thread
from SPCSSerial import SPCS2_USB

class platformNode():

    def __init__(self):
        self.sock = None
        self.controllers = [None,None,None,None,None,None]
        self.running = True
        self.stream_rate = 0
        self.inbuffer = ''

        #read config File
        self.config = json.load(open("platform.config"))
        self.id = self.config["id"]
        self.usb_map = self.config["usb_map"]

    def connect_to_platform(self):
        #connect to controllers
        for i in range(0,len(self.usb_map)):
            device = "/dev/ttyUSB" + str(i)
            print "Connecting to " + device
            controller = SPCS2_USB(device)
            time.sleep(0.1)
            controller.set_command_source(0)
            serial_number = controller.get_serial_number()
            self.controllers[self.usb_map[str(serial_number)]] = controller

    def connect_to_server(self, TCP_ip, TCP_port = 9876, timeout = 30):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print "Waiting for server to accept connection..."
        start = time.time()
        connected = False
        #attempt to connect to server
        while not connected and time.time() - start < timeout:
            connected = True
            try:
                self.sock.connect((TCP_ip, TCP_port))
            except socket.error:
                connected = False
                time.sleep(1)
        #failed to connect
        if not connected:
            print "Server connection timed out"
            return False

        print "Connected to server " + str(TCP_ip) + ':' + str(TCP_port)
        self.send_heartbeat()
        return True

    def receive_command(self):
        self.inbuffer += self.sock.recv(4096)

        complete_lines = self.inbuffer.count('\n')
        lines = self.inbuffer.split('\n')
        if len(lines) > complete_lines:
            self.inbuffer = lines[-1]
            del lines[-1]
        else:
            self.inbuffer = ""

        for line in lines:
            obj = json.loads(line)
            msg_id = obj["msg_id"]
            if msg_id == "request_feedback_stream":
                self.stream_rate = obj["stream_rate"]
                self.do_stream_position = obj["do_stream_position"]
                self.do_stream_pressure = obj["do_stream_pressure"]
            elif msg_id == "set_value":
                value_type = obj["value_type"]
                values = obj["values"]
                for i in range(0,len(values)):
                    if self.controllers[i] is None:
                        print "uninitialized controller"
                        continue
                    value = int(values[i][str(i)])
                    if value_type == "position":
                        self.controllers[i].set_position(value)
                    elif value_type == "proportional":
                        self.controllers[i].set_proportional(value)
                    elif value_type == "derivative":
                        self.controllers[i].set_derivative(value)
                    elif value_type == "offset":
                        self.controllers[i].set_offset(value)
                    elif value_type == "force_damping":
                        self.controllers[i].set_force_damping(value)
                    else:
                        print "invalid value_type"
            else:
                print "invalid command type"

    def stream_feedback(self):
        last_feedback_time = time.time()
        while self.running:
            
            if time.time() - self.last_heartbeat_time > 1:
                self.send_heartbeat()


            #send sensor feedback
            if self.stream_rate > 0:
                stream_period =  1.0/self.stream_rate
                time_diff = time.time() - last_feedback_time
                if time_diff > stream_period:
                    #update timestamp
                    last_feedback_time = time.time()
                    #check performance
                    if time_diff > 2 * stream_period:
                        print "Stream rate too fast!"
                    #poll data
                    position = []
                    pressure = []
                    for ctrl in self.controllers:
                        if ctrl is None:
                            continue
                        if self.do_stream_position:
                            position.append(ctrl.get_position())
                        if self.do_stream_pressure:
                            pressure.append(ctrl.get_pressure())
                    #pack data
                    stream = {}
                    stream["msg_id"] = "stream"
                    stream["position"] = position
                    stream["pressure"] = pressure
                    packet = json.dumps(stream) + '\n'

                    #send data
                    self.sock.send(packet)

    def send_heartbeat(self):
        packet = json.dumps({"msg_id":"heartbeat","id":self.id,"timestamp":time.time()}) + '\n'
        self.sock.send(packet)
        self.last_heartbeat_time = time.time()


    def run(self):
        try:
            #start streaming feedback in the background
            thread.start_new_thread(self.stream_feedback,())
            #process incoming commands
            while self.running:
                self.receive_command()
        finally:
            self.close()

    def close(self):
        self.running = False
        #close server
        self.sock.close()
        #close controllers
        for ctrl in self.controllers:
            if ctrl is not None:
                ctrl.close()


if __name__ == "__main__":
    node = platformNode()
    node.connect_to_platform()
    node.connect_to_server("172.16.68.106")
    try:
        node.run()
    finally:
        node.close()
