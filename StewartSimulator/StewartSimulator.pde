import peasy.*; //<>//
import controlP5.*;
import oscP5.*;
import java.io.*;


float MAX_TRANSLATION = 50;
float MAX_ROTATION = PI/2;

ControlP5 cp5;
PeasyCam camera;
Platform platform1, platform2, platform3, platform4;


float posX=0, posY=0, posZ=0, rotX=0, rotY=0, rotZ=0;
boolean ctlPressed = false;

int camera_angle = 0;

float ATV_width = 100;
float ATV_length = 100;
float platform_angle = 2*PI/3;

PVector whl_1_origin = new PVector(ATV_width/2,-ATV_length/2,0);
PVector whl_2_origin = new PVector(ATV_width/2,ATV_length/2,0);
PVector whl_3_origin = new PVector(-ATV_width/2,ATV_length/2,0);
PVector whl_4_origin = new PVector(-ATV_width/2,-ATV_length/2,0);
PVector whl_1_attitude = new PVector(PI,platform_angle - PI,0);
PVector whl_2_attitude = new PVector(PI,platform_angle - PI,0);
PVector whl_3_attitude = new PVector(0,-platform_angle,0);
PVector whl_4_attitude = new PVector(0,-platform_angle,0);

void setup() {
  size(1024, 768, P3D);
  smooth();
  frameRate(60);
  textSize(20);

  camera = new PeasyCam(this, 666);
  camera.setRotations(0.0, 0.0, 0.0);
  camera.lookAt(8.0, -50.0, 80.0);

  platform1 = new Platform(whl_1_origin, whl_1_attitude);
  platform2 = new Platform(whl_2_origin, whl_2_attitude);
  platform3 = new Platform(whl_3_origin, whl_3_attitude);
  platform4 = new Platform(whl_4_origin, whl_4_attitude);

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

void draw() {
  background(200);
  platform1.transform(PVector.mult(new PVector(posX, posY, posZ), MAX_TRANSLATION), 
    PVector.mult(new PVector(rotX, rotY, rotZ), MAX_ROTATION));
  platform2.transform(PVector.mult(new PVector(posX, posY, posZ), MAX_TRANSLATION), 
    PVector.mult(new PVector(rotX, rotY, rotZ), MAX_ROTATION));
  platform3.transform(PVector.mult(new PVector(-posX, posY, posZ), MAX_TRANSLATION), 
    PVector.mult(new PVector(rotX, rotY, rotZ), MAX_ROTATION));
  platform4.transform(PVector.mult(new PVector(-posX, posY, posZ), MAX_TRANSLATION), 
    PVector.mult(new PVector(rotX, rotY, rotZ), MAX_ROTATION));
  platform1.draw();
  platform2.draw();
  platform3.draw();
  platform4.draw();
  
  float[] l = platform1.get_length();
  for(int i = 0; i < 6; i++){
    print(l[i]);
    print(", ");
  }
  println();

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
      case 0: //wheel 1
        camera.setRotations(-PI, PI/2, PI/2);
        camera.lookAt(whl_1_origin.x, whl_1_origin.y, whl_1_origin.z);
        camera.setDistance(200);
      break;
      case 1: //wheel 2
        camera.setRotations(-PI, PI/2, PI/2);
        camera.lookAt(whl_2_origin.x, whl_2_origin.y, whl_2_origin.z);
        camera.setDistance(200);
      break;
      case 2: //wheel 3
        camera.setRotations(PI, -PI/2, -PI/2);
        camera.lookAt(whl_3_origin.x, whl_3_origin.y, whl_3_origin.z);
        camera.setDistance(200);
      break;
      case 3: //wheel 4
        camera.setRotations(PI, -PI/2, -PI/2);
        camera.lookAt(whl_4_origin.x, whl_4_origin.y, whl_4_origin.z);
        camera.setDistance(200);
      break;
      case 4: //top
        camera.setRotations(0.0, 0.0, 0.0);
        camera.lookAt(0, 0, 0);
        camera.setDistance(400);
      break;
      case 5: // front
        camera.setRotations(PI/2, 0, PI);
        camera.lookAt(0, 0, 0);
        camera.setDistance(400);
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


