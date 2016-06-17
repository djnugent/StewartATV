
import serial
import time
from Queue import Empty
from multiprocessing import Queue, Process, Value, Array, Lock

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



Max stream rates(hz):
set_pos = 300;
set_pos = 100; pos+pres = 33
set_pos = 100; pos = 100
set_pos = 100; pres = 50
'''



class SPCS2_USB():

    def __init__(self,port):
        #serial config
        self.ser = None
        self.port = port
        #controller state
        self.command_source = 1
        #controller feeback
        self.outgoing = Queue()
        self.incoming = Queue()
        self._serial_number = Value('i',-1)
        self._position = Value('i',-1)
        self._pressure = Array('i',2)
        self._pressure[0] = -1
        #callbacks
        self.serial_number_callback = None
        self.position_callback = None
        self.pressure_callback = None
        self.misc_callback = None
        #processes
        self.IO_process = None
        self.running = False
        self.lock = Lock()

    @property
    def serial_number(self):
        return self._serial_number.value
    @property
    def position(self):
        return self._position.value
    @property
    def pressure(self):
        return [self._pressure[0],self._pressure[1]]

    def open(self,wait_serial_number = True):

        #start incoming data process
        self.running = True
        self.IO_process = Process(target=self.process_IO)
        self.IO_process.daemon = True
        self.IO_process.start()

        #request serial_number
        self.request_serial_number()
        WAIT_TIMEOUT = 2
        if wait_serial_number:
            start = time.time()
            while self._serial_number.value == -1 and (time.time()-start) < WAIT_TIMEOUT:
                time.sleep(0.1)

    def close(self):
        self.running = False
        try:
            #stop process
            self.IO_process.join()
            #clear I/O buffers
            self.ser.flushInput()
            self.ser.flushOutput()
            #close serial port
            self.ser.close()
        except AttributeError:
            pass


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

        #create command and queue it up
        command = self.pack_command(88,value)
        self.outgoing.put(command)
        self.incoming.put("set_position")


    # set_command_source - set the command source (0: PC, 1: Analog)
    def set_command_source(self,source):
        #parameter check
        if source < 0 or source > 1:
            raise ValueError("{} is out of range(0 or 1)".format(source))

        #create command and queue it up
        command = self.pack_command(89,source)
        self.outgoing.put(command)
        self.incoming.put("set_command_source")
        self.command_source = source

    # set_proportional - set the proportional gain 0-100% (0 - 1000)
    def set_proportional(self,value):
        #parameter check
        if value < 0 or value > 1000:
            raise ValueError("{} is out of range(0-1000)".format(value))

        #create command and queue it up
        command = self.pack_command(1,value)
        self.outgoing.put(command)
        self.incoming.put("set_proportional")

    # set_derivative - set the derivative gain 0-100% (0 - 1000)
    def set_derivative(self,value):
        #parameter check
        if value < 0 or value > 1000:
            raise ValueError("{} is out of range(0-1000)".format(value))

        #create command and queue it up
        command = self.pack_command(2,value)
        self.outgoing.put(command)
        self.incoming.put("set_derivative")

    # set_force_damping - set the force damping constant (0 - 1000)
    def set_force_damping(self,value):
        #parameter check
        if value < 0 or value > 1000:
            raise ValueError("{} is out of range(0-1000)".format(value))

        #create command and queue it up
        command = self.pack_command(8,value)
        self.outgoing.put(command)
        self.incoming.put("set_force_damping")

    # set_offset- set the position offset (-1000 - 1000)
    def set_offset(self,value):
        #parameter check
        if value < -1000 or value > 1000:
            raise ValueError("{} is out of range(-1000 - 1000)".format(value))

        #create command and queue it up
        command = self.pack_command(15,value)
        self.outgoing.put(command)
        self.incoming.put("set_offset")

    # request_position- get the position feedback of controller (returns 0 - 4095)
    def request_position(self):
        #create request and queue it up
        command = self.pack_command(153,4369)
        self.outgoing.put(command)
        self.incoming.put("position_req")


    # request_pressure - get the pressure feedback of controller (returns array[2] 0 - 4095)
    def request_pressure(self):
        #create request and queue it up
        command = self.pack_command(154,4369)
        self.outgoing.put(command)
        self.incoming.put("pressure1_req")
        #create request and queue it up
        command = self.pack_command(155,4369)
        self.outgoing.put(command)
        self.incoming.put("pressure2_req")


    # request_serial_number - get controller serial number
    def request_serial_number(self):
        #create request and queue it up
        command = self.pack_command(147,4369)
        self.outgoing.put(command)
        self.incoming.put("serial_number_req")

    def process_IO(self):

        self.ser = serial.Serial(port = self.port,
                                baudrate = 115200,
                                timeout = 0.5)
        #clear I/O buffers
        self.ser.flushInput()
        self.ser.flushOutput()
        time.sleep(0.3)


        temp_pressure1 = None
        last_write = 0
        write_period = 1/500.0
        while self.running:
            if self.outgoing.qsize() > 20:
                print "WARNING: WRITING too fast, queued packets = {} ".format(self.outgoing.qsize())
                time.sleep(0.5)
            elif self.incoming.qsize() > 20:
                print "WARNING: READING to slow, queued packets = {} bytes available = {}".format(self.incoming.qsize(),self.ser.inWaiting())
                time.sleep(0.5)
            try:
                #send next available outgoing message
                if time.time() - last_write > write_period:
                    packet = self.outgoing.get(block = False)
                    self.ser.write(packet)
                    last_write = time.time()
                    #print self.outgoing.qsize()
            except Empty:
                pass

            #check for a response
            if self.ser.inWaiting() > 5:
                #process response
                raw = self.ser.read(6)
                data = self.unpack_response(raw)
                typ = self.incoming.get()
                #print self.incoming.qsize()

                #serial number response
                if typ == "serial_number_req":
                    #with self._serial_number.get_lock():
                    self._serial_number.value = data
                    if self.serial_number_callback is not None:
                        self.serial_number_callback(data)
                #pressure1 response
                elif typ == "pressure1_req":
                    #pressure1 should always be requested before pressure2
                    temp_pressure1 = data
                #pressure2 response
                elif typ == "pressure2_req":
                    #with self._pressure.get_lock():
                    self._pressure[0] = temp_pressure1
                    self._pressure[1] = data
                    if self.pressure_callback is not None:
                        self.pressure_callback([temp_pressure1,data])
                #position response
                elif typ == "position_req":
                    #with self._position.get_lock():
                    self._position.value = data
                    if self.position_callback is not None:
                        self.position_callback(data)

                #handle all other responses
                else:
                    if self.misc_callback is not None:
                        self.misc_callback(data)
            else:
                time.sleep(0.01)



if __name__ == "__main__":
    #connect to controller
    port = raw_input(">>Please enter device port: ")
    controller = SPCS2_USB(port)
    controller.open()
    print("Connected to {} on {}".format(controller.serial_number,port))

    try:
        print("Available Programs:")
        print("    1. Set position + read data")
        print("    2. Sweep")
        print("    3. Set parameters")
        program = int(raw_input(">>Please enter program: "))

        #set position
        if program == 1:
            print "here"
            controller.set_command_source(0)
            print("Enabled USB control")
            while True:
                value = int(raw_input(">>Please enter a piston position(0-4095): "))
                controller.set_position(value)
                time.sleep(0.25) #wait for piston to move
                position = controller.position
                pressure = [None,None]#controller.pressure
                print("Position: {}, Pressure1: {}, Pressure2: {}".format(position,pressure[0],pressure[1]))

        #Sweep
        elif program == 2:
            rate = 60
            controller.set_command_source(0)
            print("Enabled USB control")
            speed = int(raw_input(">>Please enter a sweep speed: steps per 10 ms (10-600): "))
            while True:
                for i in range(200,3500,speed):
                    controller.set_position(i)
                    time.sleep(1.0/rate)
                print "top"
                for i in range(3500,200, -speed):
                    controller.set_position(i)
                    time.sleep(1.0/rate)
                print "bottom"
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
