### Stewart ATV Controller
Software that controls Jamie Hyneman's ATV with 4 stewart platforms and 24 servopneumatics actuators.

![jamie](http://danielnugent.net/img/projects/m5-jamie.jpg)

I spent the summer of 2016 hanging out with Jamie Hyneman(Mythbusters) at M5 Industries. M5 Industries is Jamie’s personal workspace/effects company and was home of Mythbusters for 14 years. Since the show has ended and the crew has parted ways, it’s become a place for Jamie to try out whatever crazy ideas pop into his head. I happen to meet him while working on another project the summer before, and he was generous enough to let me do an apprenticeship this past summer. While there I helped him on a few of his projects and took up a few projects of my own. It was an amazing experience working alongside one of my childhood idols and learning from such a skilled builder.

## Robotic ATV

[![Video](https://img.youtube.com/vi/68m_fg67_pU/0.jpg)](https://youtu.be/68m_fg67_pU)

*Sorry for the poor audio(I was focusing on my safety, not video quality)*

One project Jamie had envisioned was an ATV with a robotic suspension system that would allow it walk, jump, dance, or stand level on a hill. Each wheel would be supported by a Stewart platform, which is a 6 degree of freedom platform. That means it can move up/down, left/right, in/out, and rotate on all axis. Each platform was composed of 6 servo pneumatic actuators capable of 18 in of throw at 700 pounds of force. This meant the vehicle contained 24 independently controlled actuators.

Before I arrived, Jamie had constructed a single platform on a test bed. He controlled it using a waldo which is smaller version of the platform that allows master-slave control over the platform. The setup was jerky and often caused the platform to go into dangerous oscillations. The setup was obviously not scalable for a single person to control 4 of the platforms. That’s where I came in. I wrote software which allowed the platform to be controlled digitally. The platform could run through preset animations or the control could augmented using a HID(Human input device) like a joystick or control panel.

### Path planner

![sim](http://danielnugent.net/img/projects/m5-sim.gif)

I wrote a visualizer and path planner which calculated the length of the all the actuators given a x/y/z/roll/pitch/yaw pose of the wheel. This was central command for the system and for test purposes ran on my laptop.

### Platform Node

Each platform/wheel was controlled using a Raspberry pi type computer(Odroid) which was connected on a local wifi network to the central command software. This was necessary because each servo pneumatic controller ran off USB and 24 USB  connections into the central control computer was too much bandwidth. Also it solved the problem of running long USB cables all over the vehicle. Instead we only had 4/5 wifi or ethernet connections. I wrote the entire communication layer using TCP sockets and JSON. The platforms were self identifying and could connect/disconnect without system interruption.

### Servo Pneumatic Controllers

The servo pneumatic controllers were designed to take input from an analog signal(0-10v -> 0-18in) and provided no feedback. This was unacceptable for this day and age. However, I realized the controllers came with a configuration software which communicated over USB. So I sniffed the USB packets being sent between the software and platform and reverse engineered the protocol. They used the COM profile as their USB base protocol, which is nice because it is easy to reverse engineer, but bad because is super susceptible to buffer overflows and lock ups if not implemented properly. Sadly,  it was not implemented properly, and I was only able to push commands at 60hz and get feedback at 10hz with a ~350ms delay, otherwise I would lock up the controllers until the next reboot. Ideally, I would like to push commands at 200hz and get the feedback at 200hz with < 10ms delay.

### Status

I was able to program more animations and control methods. However the speed, responsiveness, and safety of the system were not up to spec. The project has been put on hold as Jamie desires for the project were outside the scope of my ability and time. I provided him with the best system he could get with the current hardware. He requested Boston Dynamics level of control, but the hardware and software (or PhDs!!!) weren’t there. If I could continue the project I would replace the servo pneumatic controllers with custom controllers, as the ones provided were too “black box” and their performance was poor and unpredictable.
 
 
### Dependencies:  
- [peasycam](http://mrfeinberg.com/peasycam/)  
- [controlP5](http://www.sojamo.de/libraries/controlP5/)  
- [oscP5](http://www.sojamo.de/libraries/oscP5/)
- python2.7
- pyserial
