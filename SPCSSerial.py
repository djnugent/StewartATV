
import serial
import time

'''
TODO
    - figure out how to save parameters
Weird behavior
    - When p = 14 -> Position feedback = position desired + (force damping/offset)
    - when offest is present -> decreasing P increases steady state error

8 Byte Command Packet
    1st Byte                '$'
    2nd Byte                'C'
    3rd Byte                Command Byte (0 - 255)
    4th Byte                Lower Data Byte (0 - 255)
    5th Byte                Upper Data Byte (0 - 255)
    6th Byte                '#'
    7th Byte                Lower CRC Byte (0 - 255)
    8th Byte                Upper CRC Byte (0 -255)

6 Byte Response Packet
    1st Byte                '+'
    2nd Byte                Lower Data (lower 8 bits)
    3rd Byte                Upeer Data (upper 8 bits)
    4th Byte                '#'
    5th Byte                Lower CRC (lower 8 bits)
    6th Byte                Upper CRC (upper 8 bits)


Command List
    1            Set Proportional (0 to 1000)
    2            Set Derivative (0 to 1000)
    8            Forced Damping(0 to 1000)
    15           Offset ( -1000 to 1000)
    88           Set Command (0 to 4095)
    89           SET_COMMAND_SOURCE (0/1)
    112          *undocumented - startup command
    113          *undocumented - startup command
    119          *undocumented - startup command
    126          *undocumented - startup command
    128          *undocumented - startup command
    129          *undocumented - startup command
    130          *undocumented - startup command
    131          *undocumented - startup command
    132          *undocumented - startup command
    134          *undocumented - startup command
    135          *undocumented - startup command
    136          *undocumented - startup command
    137          *undocumented - startup command
    138          *undocumented - startup command
    139          *undocumented - startup command
    140          *undocumented - startup command
    144          *undocumented - startup command
    146          *undocumented - startup command
    149          *undocumented - startup command
    148          *undocumented - startup command
    147          Get Serial Number
    152          Get Analog Set Point (returns 0 to 4095)
    153          Get Feedback  (returns 0 to 4095)
    154          Get Pressure 1 (returns 0 to 4095)
    155          Get Pressure 2 (returns 0 to 4095)
    161          *undocumented - startup command
    162          *undocumented - startup command
    163          *undocumented - startup command
    164          *undocumented - startup command
'''



class SPCS2_USB():

    def __init__(self,port, feedback_mode = 0):
        #serial config
        self.ser = None
        self.port = port
        #feedback config
        self.feedback_rate = 50
        self.feedback_mode = feedback_mode #0:no feedback 1: pos + pres, 2: just pos, 3: just pres
        #controller state
        self.command_source = 1
        #controller feeback
        self.serial_number = None
        self.position = None
        self.pressure = None
        #callbacks
        self.serial_number_callback = None
        self.position_callback = None
        self.pressure_callback = None
        self.misc_callback = None
        #threads
        self.read_thread = None
        self.request_thread = None
        self.running = False

    def open(self,wait_serial_number = True, wait_feedback = False):
        #connect to serial port
        self.ser = serial.Serial(port = self.port,
                                baudrate = 115200,
                                timeout = 0.5)
        #clear I/O buffers
        self.ser.flushInput()
        self.ser.flushOutput()
        #TODO reallign data

        time.sleep(0.3)

        #start incoming data thread
        self.running = True
        self.read_thread = threading.Thread(target=self.read_incoming)
        self.read_thread.start()

        #start feedback thread
        self.request_thread = threading.Thread(target=self.request_feedback)
        self.request_thread.start()

        #request serial_number
        self.request_serial_number()
        WAIT_TIMEOUT = 5
        if wait_serial_number:
            start = time.time()
            while self.serial_number is None and (time.time()-start) < WAIT_TIMEOUT:
                time.sleep(0.1)

        #wait for feedback fields to populate
        if wait_feedback and self.feedback_mode != 0 and self.feedback_rate > 0:
            while (time.time()-start) < WAIT_TIMEOUT:
                if self.feedback_mode == 1 and self.position is not None and self.pressure is not None:
                    break
                elif self.feedback_mode == 2 and self.position is not None:
                    break
                elif self.feedback_mode == 3 and self.pressure is not None:
                    break
                else:
                    time.sleep(.1)

        print(self.port + " connected")

    def close(self):
        #stop threads
        self.running = False
        self.feedback_thread.join()
        self.read_thread.join()
        #clear I/O buffers
        self.ser.flushInput()
        self.ser.flushOutput()
        #close serial port
        self.ser.close()

    def config_feedback(self, feedback_mode, feedback_rate):
        if feedback_rate > 0:
            self.feedback_mode = feedback_mode
            self.feedback_rate = feedback_rate
        else:
            self.feedback_mode = 0

    @classmethod
    # pack_command - packages a command
    def pack_command(cls, command, value):
        packet = bytearray(['$',                            #header
                            'C',                            #header
                            command & 0xFF,                 #command
                            value & 0xFF,                   #lower data
                            (value >> 8) & 0xFF,            #upper data
                            '#'])                           #stop

        crc = cls.compute_CRC(packet,6)

        packet += bytearray([crc & 0xFF,                    #lower crc
                            (crc >> 8) & 0xFF])             #upper crc

        return packet

    @classmethod
    # compute_CRC - computes CRC of packet
    def compute_CRC(cls, packet, length):
            crc16reg = 0xFFFF
            u16Poly16 = 0xA001
            u16MsgByte = 0
            for j in range(0,length):
                try:
                    u16MsgByte = 0x00FF & ord(packet[j])
                except:
                    u16MsgByte = 0x00FF & int(packet[j])
                for i in range(0,8):
                    if (crc16reg ^ u16MsgByte) & 0x0001:
                        crc16reg = (crc16reg >> 1) ^ u16Poly16
                    else:
                        crc16reg = crc16reg >> 1
                    u16MsgByte >>= 1
            return crc16reg

    @classmethod
    # unpack_response - decodes a response packet from controller
    def unpack_response(cls, packet):
        #check for complete packet
        if len(packet) < 6:
            raise RuntimeError("Incomplete or empty Packet")
        #check missing for header or footer
        if packet[0] != '+' or packet[3] != '#':
            raise RuntimeError("Misaligned data")

        #extract data
        data_lower =  ord(packet[1])
        data_upper = ord(packet[2])
        data = (data_upper << 8) | (data_lower & 0x00FF)
        #extract crc
        crc_lower = ord(packet[4])
        crc_upper = ord(packet[5])
        crc_packet = (crc_upper << 8) | (crc_lower & 0x00FF)
        #crc check
        crc_data = cls.compute_CRC(packet,4)
        if crc_data != crc_packet:
            raise RuntimeError('CRC mismatch')

        return data

    # set_position - set the position from a PC (0 - 4095)
    def set_position(self,value):
        #state check
        if self.command_source != 0:
            raise RuntimeError("Controller not under PC control")
        #parameter check
        if value < 0 or value > 4095:
            raise ValueError("{} is out of range(0-4095)".format(value))

        self.outgoing.put("set_position")
        command = self.pack_command(88,value)
        self.ser.write(command)

    # set_command_source - set the command source (0: PC, 1: Analog)
    def set_command_source(self,source):
        #parameter check
        if source < 0 or source > 1:
            raise ValueError("{} is out of range(0 or 1)".format(source))

        self.outgoing.put("set_command_source")
        command = self.pack_command(89,source)
        self.command_source = source
        self.ser.write(command)

    # set_proportional - set the proportional gain 0-100% (0 - 1000)
    def set_proportional(self,value):
        #parameter check
        if value < 0 or value > 1000:
            raise ValueError("{} is out of range(0-1000)".format(value))

        self.outgoing.put("set_proportional")
        command = self.pack_command(1,value)
        self.ser.write(command)

    # set_derivative - set the derivative gain 0-100% (0 - 1000)
    def set_derivative(self,value):
        #parameter check
        if value < 0 or value > 1000:
            raise ValueError("{} is out of range(0-1000)".format(value))

        self.outgoing.put("set_derivative")
        command = self.pack_command(2,value)
        self.ser.write(command)

    # set_force_damping - set the force damping constant (0 - 1000)
    def set_force_damping(self,value):
        #parameter check
        if value < 0 or value > 1000:
            raise ValueError("{} is out of range(0-1000)".format(value))

        self.outgoing.put("set_force_damping")
        command = self.pack_command(8,value)
        self.ser.write(command)

    # set_offset- set the position offset (-1000 - 1000)
    def set_offset(self,value):
        #parameter check
        if value < -1000 or value > 1000:
            raise ValueError("{} is out of range(-1000 - 1000)".format(value))

        self.outgoing.put("set_offset")
        command = self.pack_command(15,value)
        self.ser.write(command)

    # request_position- get the position feedback of controller (returns 0 - 4095)
    def request_position(self):
        #queue request for proper response handling
        self.outgoing.put("position_req")

        #request data
        command = self.pack_command(153, 4369)
        self.ser.write(command)


    # request_pressure - get the pressure feedback of controller (returns array[2] 0 - 4095)
    def request_pressure(self):
        #queue request for proper response handling
        self.outgoing.put("pressure1_req")
        self.outgoing.put("pressure2_req")

        #request data
        command = self.pack_command(154,4369) #pres 1
        self.ser.write(command)
        command = self.pack_command(155 ,4369) #pres2
        self.ser.write(command)

    # request_serial_number - get controller serial number
    def request_serial_number(self):
        #queue request for proper response handling
        self.outgoing.put("serial_number_req")

        #request data
        command = self.pack_command(147, 4369)
        self.ser.write(command)

    # read_incoming - handle incoming serial data
    def read_incoming(self):
        temp_pressure1 = None
        while self.running:
            if self.ser.inWaiting() > 5:
                raw = self.ser.read(6)
                data = self.unpack_response(raw)
                sent = self.outgoing.get()
                #serial number response
                if sent == "serial_number_req":
                    self.serial_number = data
                    if self.serial_number_callback is not None:
                        self.serial_number_callback(data)
                #pressure1 response
                elif sent == "pressure1_req":
                    #pressure1 should always be requested before pressure2
                    temp_pressure1 = data
                #pressure2 response
                elif sent == "pressure2_req":
                    self.pressure = [temp_pressure1, data]
                    if self.pressure_callback is not None:
                        self.pressure_callback([temp_pressure1,data])
                #position response
                elif sent == "position_req":
                    self.position = data
                    if self.position_callback is not None:
                        self.position_callback(data)

                #set command_source response
                elif sent == "set_command_source":
                    self.command_source = data

                #handle all other responses
                else:
                    if self.misc_callback is not None:
                        self.misc_callback(data)

    # request_feedback - continuously request a feedback stream
    def request_feedback(self):
        last_feedback_time = 0
        while self.running:
            if feedback_rate > 0:
                period = 1.0/self.feedback_rate

                if time.time() - last_feedback_time > period:
                    last_feedback_time = time.time()

                    #1 - stream position and pressure
                    if self.feedback_mode == 1:
                        self.request_position()
                        self.request_pressure()
                    #2 - stream position
                    elif self.feedback_mode == 2:
                        self.request_position()
                    #3 - stream pressure
                    elif self.feedback_mode == 3:
                        self.request_pressure()
                else:
                    time.sleep(period/4.0)
            else:
                time.sleep(0.25)







if __name__ == "__main__":
    #connect to controller
    port = raw_input(">>Please enter device port: ")
    controller = SPCS2_USB(port)
    print("Connected on {}".format(port))

    try:
        print("Available Programs:")
        print("    1. Set position + read data")
        print("    2. Sweep")
        print("    3. Set parameters")
        program = int(raw_input(">>Please enter program: "))

        #set position
        if program == 1:
            controller.set_command_source(0)
            print("Enabled USB control")
            while True:
                value = int(raw_input(">>Please enter a piston position(0-4095): "))
                controller.set_position(value)
                time.sleep(0.25) #wait for piston to move
                position = controller.get_position()
                pressure = controller.get_pressure()
                print("Position: {}, Pressure1: {}, Pressure2: {}".format(position,pressure[0],pressure[1]))

        #Sweep
        elif program == 2:
            controller.set_command_source(0)
            print("Enabled USB control")
            speed = int(raw_input(">>Please enter a sweep speed: steps per 10 ms (10-600): "))
            while True:
                for i in range(200,3500,speed):
                    controller.set_position(i)
                    time.sleep(0.01)

                for i in range(3500,200, -speed):
                    controller.set_position(i)
                    time.sleep(0.01)
        #set parameters
        elif program == 3:
            print("Available parameters:")
            print("    p -- proportional gain     (0 - 1000)        Ex: p10")
            print("    d -- derivative gain       (0 - 1000)        Ex: d142")
            print("    f -- force dampening gain  (0 - 1000)        Ex: f213")
            print("    o -- offset                (-1000 - 1000)    Ex: o-267")
            while True:
                raw = raw_input(">>Please enter a parameter (p/d/f/o)(value): ")

                param = raw[0].lower()
                if param == 'p':
                    value = int(raw[1:])
                    controller.set_proportional(value)
                    print("Set proportional gain to {}".format(value))
                elif param == 'd':
                    value = int(raw[1:])
                    controller.set_derivative(value)
                    print("Set derivative gain to {}".format(value))
                elif param == 'f':
                    value = int(raw[1:])
                    controller.set_force_damping(value)
                    print("Set force dampening to {}".format(value))
                elif param == 'o':
                    value = int(raw[1:])
                    controller.set_offset(value)
                    print("Set offset to {}".format(value))
                else:
                    print("invalid parameter")

        else:
            print("invalid program number")

    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    finally:
        controller.close()
        print("Closed connection")
