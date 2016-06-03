import peasy.*;
import controlP5.*;
import oscP5.*;

//GUI variables
ControlP5 cp5;
PeasyCam camera;
int camera_angle;
boolean ctlPressed = false;
float posX=0, posY=0, posZ=0, rotX=0, rotY=0, rotZ=0;

//Platform variables
ArrayList<Platform> platforms = new ArrayList<Platform>();

float ATV_width = 100;
float ATV_length = 100;
float platform_angle = 2*PI/3;

PVector whl_0_origin = new PVector(ATV_width/2,-ATV_length/2,0);
PVector whl_1_origin = new PVector(ATV_width/2,ATV_length/2,0);
PVector whl_2_origin = new PVector(-ATV_width/2,ATV_length/2,0);
PVector whl_3_origin = new PVector(-ATV_width/2,-ATV_length/2,0);
PVector whl_0_attitude = new PVector(PI,platform_angle - PI,0);
PVector whl_1_attitude = new PVector(PI,platform_angle - PI,0);
PVector whl_2_attitude = new PVector(0,-platform_angle,0);
PVector whl_3_attitude = new PVector(0,-platform_angle,0);

int step;
float speed = 100;
float radius = .1;


//network Variables and   callbacks
Server server;
int portNumber = 9876;
Callback client_connect = new Callback(){
      public void execute(Object... args){
        Client client = (Client)args[0];
        //wait for client to identify in a heartbeat packet
        while(client.id == -1){
          delay(2);
        }
        Platform platform = platforms.get(client.id);
        platform.setClient(client);
      }
};

void setup() {
  //initialize window
  size(1024, 768, P3D);
  smooth();
  textSize(20);
  frameRate(60);

  //initialize camera
  camera = new PeasyCam(this, 200);
  camera.setRotations(0.0, 0.0, 0.0);
  camera.lookAt(0,0,0);
  camera.setMinimumDistance(2);
  camera.setMaximumDistance(500); 
  camera_angle = 0;
 

  //create platforms
  platforms.add(new Platform(whl_0_origin, whl_0_attitude));
  platforms.add(new Platform(whl_1_origin, whl_1_attitude));
  platforms.add(new Platform(whl_2_origin, whl_2_attitude));
  platforms.add(new Platform(whl_3_origin, whl_3_attitude));

  //start server
  server = new Server(portNumber);
  server.set_onClientConnectCallback(client_connect);
  server.start();

  //create sliders
  cp5 = new ControlP5(this);
  cp5.addSlider("posX")
    .setPosition(20, 20)
    .setSize(180, 40).setRange(-1, 1);
  cp5.addSlider("posY")
    .setPosition(20, 70)
    .setSize(180, 40).setRange(-1, 1);
  cp5.addSlider("posZ")
    .setPosition(20, 120)
    .setSize(180, 40).setRange(-1, 1);
  cp5.addSlider("rotX")
    .setPosition(width-200, 20)
    .setSize(180, 40).setRange(-1, 1);
  cp5.addSlider("rotY")
    .setPosition(width-200, 70)
    .setSize(180, 40).setRange(-1, 1);
  cp5.addSlider("rotZ")
    .setPosition(width-200, 120)
    .setSize(180, 40).setRange(-1, 1);

  cp5.setAutoDraw(false);
  camera.setActive(true);
  
  
  
}

int last = 0;
void draw() {
  //println(1000.0/(millis() - last));
  last = millis();
  background(200);
  /*
  posX = 0.3;
  posY = radius * cos(step * 1.0 / speed);
  posZ = radius * sin(step * 1.0/ speed) + 0.2;
  step++;
  */
  
  
  int i = 0;
  for (Platform platform: platforms){
    if(i < 2){
    platform.transform(PVector.mult(new PVector(posX, posY, posZ), 50), 
      PVector.mult(new PVector(rotX, rotY, rotZ), PI/2));
    }
    else{
      platform.transform(PVector.mult(new PVector(-posX, posY, posZ), 50), 
      PVector.mult(new PVector(rotX, -rotY, rotZ), PI/2));
    }
    platform.draw();
    platform.send_position();
    i++;
  }
 //println(platforms.get(0).scaled_positions);
  
 
  
  hint(DISABLE_DEPTH_TEST);
  camera.beginHUD();
  cp5.draw();
  camera.endHUD();
  hint(ENABLE_DEPTH_TEST);
  
 }

void controlEvent(ControlEvent theEvent) {
  camera.setActive(false);
}
void mouseReleased() {
  camera.setActive(true);
}


void mouseDragged () {
  if (ctlPressed) {
    posX = map(mouseX, 0, width, -1, 1);
    posY = map(mouseY, 0, height, -1, 1);
  }
}


void keyPressed() {
  if (key == ' ') {
    
    switch(camera_angle){
      case 0: //wheel 0
        camera.setRotations(-PI, PI/2, PI/2);
        camera.lookAt(whl_0_origin.x, whl_0_origin.y, whl_0_origin.z);
        camera.setDistance(200);
      break;
      case 1: //wheel 1
        camera.setRotations(-PI, PI/2, PI/2);
        camera.lookAt(whl_1_origin.x, whl_1_origin.y, whl_1_origin.z);
        camera.setDistance(200);
      break;
      case 2: //wheel 2
        camera.setRotations(PI, -PI/2, -PI/2);
        camera.lookAt(whl_2_origin.x, whl_2_origin.y, whl_2_origin.z);
        camera.setDistance(200);
      break;
      case 3: //wheel 3
        camera.setRotations(PI, -PI/2, -PI/2);
        camera.lookAt(whl_3_origin.x, whl_3_origin.y, whl_3_origin.z);
        camera.setDistance(200);
      break;
      case 4: //top
        camera.setRotations(0.0, 0.0, 0.0);
        camera.lookAt(0, 0, 0);
        camera.setDistance(200);
      break;
      case 5: // front
        camera.setRotations(PI/2, 0, PI);
        camera.lookAt(0, 0, 0);
        camera.setDistance(200);
      break;
    }
    camera_angle = (camera_angle + 1) % 6;
    
  } else if (keyCode == CONTROL) {
    camera.setActive(false);
    ctlPressed = true;
  }
}

void keyReleased() {
  if (keyCode == CONTROL) {
    camera.setActive(true);
    ctlPressed = false;
  }
}

