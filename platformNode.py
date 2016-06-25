import socket
import time
import json
import platform
from multiprocessing import Value, Process
from threading import Thread
from SPCSSerial import SPCS2_USB

class platformNode():

    def __init__(self):
        self.sock = None
        self.controllers = [None,None,None,None,None,None]
        self.running = True
        self.stream_rate = Value('i',0)
        self.stream_mode = Value('i',0)
        self.inbuffer = ''
        self.last_packet = 0
        self.sum = 0.0
        self.count = 0.0
        self.COM_ports = ["COM5","COM8","COM9","COM10","COM11","COM12"]
        self.p = 35.0
        self.d = 0.0
        self.f = 0.0

        #read config File
        self.config = json.load(open("platform.config"))
        self.id = self.config["id"]
        self.usb_map = self.config["usb_map"]

    def connect_to_platform(self):
        #connect to all controllers simultaneously
        connect_processes = []
        unordered_controllers = []
        for i in range(0,len(self.usb_map)):
            device = None
            if platform.system() == "Windows":
                device = self.COM_ports[i]
            else:
                device = "/dev/ttyUSB" + str(i)
            print "Connecting to " + device
            ctrl = SPCS2_USB(device,i)
            ctrl.open() #blocking
            ctrl.set_command_source(0)
            ctrl.set_proportional(int(self.p * 10))
            ctrl.set_derivative(int(self.d * 10))
            ctrl.set_force_damping(int(self.f * 10))
            serial_number = ctrl.serial_number
            if serial_number == -1:
                print ctrl.port + " Failed to connect"
                ctrl.close()
            else:
                self.controllers[self.usb_map[str(serial_number)]] = ctrl

    def connect_to_server(self, TCP_ip, TCP_port = 9876, timeout = 30):
        print "Connecting to server {}:{}".format(TCP_ip,TCP_port)
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
            rate = 1.0/(time.time()-self.last_packet)
            self.last_packet = time.time()
            self.sum += rate
            self.count += 1
            if self.count == 30:
                print "{}: {} hz".format(msg_id,self.sum/self.count)
                self.sum = 0.0
                self.count = 0.0

            if msg_id == "request_feedback_stream":
                self.stream_mode.value = obj["stream_mode"]
                self.stream_rate.value = obj["stream_rate"]

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
            #send heartbeat
            if time.time() - self.last_heartbeat_time > 1:
                self.send_heartbeat()

            #send sensor feedback
            if self.stream_rate.value > 0 and self.stream_mode.value != 0:
                stream_period =  1.0/self.stream_rate.value
                time_diff = time.time() - last_feedback_time
                if time_diff > stream_period:
                    #update timestamp
                    last_feedback_time = time.time()
                    #poll data
                    position = []
                    pressure = []
                    for ctrl in self.controllers:
                        if ctrl is None:
                            continue
                        if self.stream_mode.value == 1:
                            #request data
                            ctrl.request_position()
                            ctrl.request_pressure()
                            #grab data - wont always arrive in time so it may be old
                            position.append(ctrl.position)
                            pressure.append(ctrl.pressure)
                        if self.stream_mode.value == 2:
                            #request data
                            ctrl.request_position()
                            #grab data - wont always arrive in time so it may be old
                            position.append(ctrl.position)
                        if self.stream_mode.value == 3:
                            #request data
                            ctrl.request_pressure()
                            #grab data - wont always arrive in time so it may be old
                            pressure.append(ctrl.pressure)
                    #pack data
                    stream = {}
                    stream["msg_id"] = "stream"
                    stream["position"] = position
                    stream["pressure"] = pressure
                    packet = json.dumps(stream) + '\n'

                    #send data
                    self.sock.send(packet)
                else:
                    time.sleep(stream_period/4.0)
            else:
                time.sleep(0.25)

    def send_heartbeat(self):
        packet = json.dumps({"msg_id":"heartbeat","id":self.id,"timestamp":time.time()}) + '\n'
        self.sock.send(packet)
        self.last_heartbeat_time = time.time()


    def run(self):
        try:
            #start streaming feedback in the background
            self.stream_process = Thread(target=self.stream_feedback)
            #stream_process.daemon = True
            self.stream_process.start()
            #process incoming commands
            while self.running:
                self.receive_command()
                time.sleep(0.005)
        finally:
            self.close()

    def close(self):
        #stop streaming
        try:
            self.running = False
            self.stream_process.join()
        except:
            print "ERROR joining stream_process"

        #close socket connection
        try:
            self.sock.close()
        except:
            print "ERROR closing socket"

        #close serial drivers
        for ctrl in self.controllers:
            if ctrl is not None:
                try:
                    ctrl.close()
                except:
                    print "ERROR closing controller {}".format(ctrl.ID)




if __name__ == "__main__":
    node = platformNode()
    node.connect_to_platform()
    connected = node.connect_to_server("192.168.1.3")
    if connected:
        node.run()
