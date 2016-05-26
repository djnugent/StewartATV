import socket
import time
import json
import thread
from SPCSSerial import SPCS2_USB

class platformNode():

    def init(self):
        self.sock = None
        self.usb_map = {}
        self.controllers = [None,None,None,None,None]

        #read config File
        config = open("/home/pi/platform.config", "r")
        while True:
            line = config.readline()
            controller_number = int(line[0])
            serial_number = int(line[2:].strip()) #remove controller_number and newline char
            usb_map[serial_number] = controller_number #map serial number to
            if '\n' not in line: #EOF
                break

    def connect_to_platform(self):
        #connect to controllers
        for i in range(0,len(usb_map)):
            device = "/dev/ttyUSB" + i
            print "Connecting to " + device
            controller = SPCS2_USB(device)
            controller.set_command_source(0)
            serial_number = control.get_serial_number()
            self.controllers[self.usb_map[serial_number]] = controller

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
        return True

    def receive_command(self):
        data = self.sock.recv(1024)
        print data
        return
        json = json.loads(data)
        msg_id = json["msg_id"]
        if msg_id == "request_feedback_stream":
            self.stream_rate = json["stream_rate"]
            self.do_stream_position = json["do_stream_position"]
            self.do_stream_pressure = json["do_stream_pressure"]
        elif msg_id == "pressure_stream":
            self.pres_stream_rate = json["stream_rate"]
        elif msg_id == "set_value":
            value_type = json["value_type"]
            target_id = json["target_id"]
            values = json["values"]
            for i in range(0,len(values)):
                value = int(values[i])
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
        last_heartbeat_time = time.time()
        while self.running:
            #send heartbeat
            if time.time() - last_heartbeat_time > 1:
                last_heartbeat_time = time.time()
                packet = json.dumps({"msg_id":"heartbeat"})
                self.sock.send(packet)

            #send sensor feedback
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
                for ctrl in controllers:
                    if self.do_stream_position:
                        position += ctrl.get_position()
                    if self.do_stream_pressure:
                        pressure += ctrl.get_pressure()
                #pack data
                stream = {}
                stream["msg_id"] = "heartbeat"
                stream["position"] = position
                stream["pressure"] = pressure
                packet = json.dumps(stream)

                #send data
                self.sock.send(packet)

    def run(self):
        try:
            #start streaming feedback in the background
            thread.start_new_thread(self.stream_feedback)

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
    #node.connect_to_platform()
    node.connect_to_server("172.16.68.106")
    while True:
        node.receive_command()
