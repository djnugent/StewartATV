
import serial

class SPCS2_USB():

    def __init__(self,port,baudrate = 115200):
        self.ser = serial.Serial(port = port,
                                baudrate = baudrate,
                                timeout = 0.1)



    def sendCommand(self, command, value):
        packet = bytearray(['$',                            #header
                            'C',                            #header
                            command & 0xFF,                 #command
                            value & 0xFF,                   #lower data
                            (value >> 8) & 0xFF,            #upper data
                            '#'])                           #stop

        crc = self.computeCRC(packet)

        packet += bytearray([(crc >> 8) & 0xFF,             #upper crc
                            crc & 0xFF])                    #lower crc

        self.ser.write(packet)


    def computeCRC(self, packet):
            crc16reg = 0xffff
            u16Poly16 = 0xA001
            for j in range(0,len(packet)):
                u16MsgByte = 0x00FF & packet[j]
                for i in range(0,8):
                    if ((crc16reg ^ u16MsgByte) & 0x0001) > 1:
                        crc16reg = (crc16reg >> 1) ^ u16Poly16
                    else:
                        crc16reg = crc16reg >> 1
                    u16MsgByte >>= 1
            return crc16reg

if __name__ == "__main__":
    port = raw_input(">>Please enter device port: ")
    controller = SPCS2_USB(port)
    print("Connected on {}".format(port))

    controller.sendCommand(89,0)
    print("Enabled USB control")

    while True:
        value = int(raw_input(">>Please enter a piston position(0-4097): "))
        if(value >= 0 and value <= 4097):
            controller.sendCommand(88,value)
            print("{} sent".format(value))
        else:
            print("Failed to send: {} is out of range".format(value))
