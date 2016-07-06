
class AnimationManager{

  Animation current_animation;
  PVector current_position;
  PVector target_position;
  boolean running = true;
  boolean reached_target = true;
  float max_displacement = 0.5;
  
    
  public AnimationManager(PVector start){
   current_position = start; 
  }
  
  
  
  //the max distance the platform can move between animation steps cycles
  public void set_max_displacement(float inches){
    max_displacement = inches;    
  }
  
  public void set_animation_time(float time){
   if(current_animation != null){
    current_animation.set_animation_time(time);
   } 
  }
  
  //call continously at steps_per_second rate
  public PVector run(){
    if(running && current_animation != null){      
      //progress animation if we arrive at last step
      if(reached_target){
        target_position = current_animation.step();
      }
      
      //smooth/constrain trajectory
      PVector next_position;
      PVector disp = PVector.sub(target_position,current_position);
      if(disp.mag() > max_displacement){
          disp.normalize();
          disp.mult(max_displacement);
          next_position = PVector.add(current_position, disp);
          reached_target = false;
      }
      else{
         next_position = target_position; 
         reached_target = true;
      }
      
      //update controllers
      current_position = next_position;
      return next_position;
      
    }
    else{
      return current_position;
    }
  }
  
  public void pause(){
    running = false;
  }
  
  public void play(){
    running = true;
  }
 
  //load up a new animation
  public void set_animation(Animation animation){
     //initialize animation to closest point
     ArrayList<PVector> full_animation = animation.get_full_animation();
     int nearest_step = 0;
     float nearest_dist = 100000000;
     for(int i = 0; i < full_animation.size(); i++){
       PVector animation_position = full_animation.get(i);
       float dist = current_position.dist(animation_position);
       if(current_position.dist(animation_position) < nearest_dist){
         nearest_step = i;
         nearest_dist = dist;
       }
     }
     
     animation.initialize(nearest_step);
     current_animation = animation;
     reached_target = true;
     
  }
    
  
}




abstract class Animation{
  protected int steps_per_second = 60;
  protected float animation_time = 0; 
  
  //Steps per Second setter
  public void set_steps_per_second(int sps){
    steps_per_second = sps;
  }
  
  //Animation time setter
  public void set_animation_time(float time){
    animation_time = time;
  }
  
  //methods to be overriden
  public abstract void initialize(int step);
  public abstract PVector step();
  public abstract ArrayList<PVector> get_full_animation();
  
}



/*
Circle Animation
*/

class CircleAnimation extends Animation{
  
  
  public String name = "CircleAnimation";  
 
  private float animation_angle = 0;
  private float animation_radius = 5;
  private PVector animation_origin = new PVector(0,0,0);
  
  
  public CircleAnimation(int animation_time){
    this.animation_time = animation_time;
  }
  
  //Initialize animation to a specific step
  public void initialize(int step){
     animation_angle =  step * 360.0 / (animation_time * steps_per_second);
     animation_angle = animation_angle%360;
  }
  
  public void config(float radius, PVector origin){
    animation_radius = radius;
    animation_origin = origin;
  }
  
  //Calculates the next platform position along animation
  public PVector step(){
    
    //increment animation
    float deg_per_step = 360.0 / (animation_time * steps_per_second);
    animation_angle += deg_per_step;
    animation_angle = animation_angle%360;
    
    return transform(animation_angle, animation_radius, animation_origin);
   
    
  }
  
  //Calculates the platform position at a give angle
  private PVector transform(float angle, float radius, PVector origin){
     //calculate position
    PVector pos = new PVector();
    pos.x = origin.x;
    pos.y = radius * cos(radians(angle)) + origin.y;
    pos.z = radius * sin(radians(angle)) + origin.z;
    return pos;
  }
  
  //return a list of all the steps along the animation(in it's current configuration)
  public ArrayList<PVector> get_full_animation(){
    int total_steps = int(animation_time * steps_per_second);
    ArrayList<PVector> full_animation = new ArrayList<PVector>();
    
    for(int i = 0; i < total_steps; i++){
        float angle =  i * 360.0 / (animation_time * steps_per_second);
        angle = angle%360;
        full_animation.add(transform(angle,animation_radius, animation_origin));
    }
    return full_animation;
  }
  
}





/*
Manual Animation
*/

class ManualAnimation extends Animation{
  
  
  public String name = "ManualAnimation";  
 
  private PVector animation_position = new PVector(0,0,0);
  
  
  public ManualAnimation(){
  }
  
  //Initialize animation to a specific step
  public void initialize(int step){
  }
  
  public void config(PVector position){
    animation_position = position;
  }
  
  //Calculates the next platform position along animation
  public PVector step(){
    return animation_position;
  }
  
  //return a list of all the steps along the animation(in it's current configuration)
  public ArrayList<PVector> get_full_animation(){
    ArrayList<PVector> full_animation = new ArrayList<PVector>();
    full_animation.add(animation_position);
    return full_animation;
  }
  
}


/*
Walk Animation
*/

class WalkAnimation extends Animation{
  
  
  public String name = "WalkAnimation";  
 
  private float animation_angle = 0;
  
  private float animation_floor_height;
  private float animation_stride_length;
  private float animation_wheel_base;
  
  
  public WalkAnimation(int animation_time){
    this.animation_time = animation_time;
  }
  
  //Initialize animation to a specific step
  public void initialize(int step){
     animation_angle =  step * 360.0 / (animation_time * steps_per_second);
     animation_angle = animation_angle%360;
  }
  
  public void config(float floor_height, float stride_length, float wheel_base){
    animation_floor_height = floor_height;
    animation_stride_length = stride_length;
    animation_wheel_base = wheel_base;
  }
  
  //Calculates the next platform position along animation
  public PVector step(){
    
    //increment animation
    float deg_per_step = 360.0 / (animation_time * steps_per_second);
    animation_angle += deg_per_step;
    animation_angle = animation_angle%360;
    
    return transform(animation_angle,animation_floor_height, animation_stride_length, animation_wheel_base);
   
    
  }
  
  //Calculates the platform position at a give angle
  private PVector transform(float angle,float floor_height, float stride_length, float wheel_base){
     //calculate position
    PVector pos = new PVector();
    //stride
    if(angle > 180){
      pos.x = wheel_base;
      pos.y = ((angle-180)/180.0 * stride_length) - stride_length/2.0;
      pos.z = floor_height;
    }
    //lift
    else{
      pos.x = wheel_base;
      pos.y = stride_length/2.0 * cos(radians(angle));
      pos.z = stride_length/2.0 * sin(radians(angle)) + floor_height;
    }
    return pos;
  }
  
  //return a list of all the steps along the animation(in it's current configuration)
  public ArrayList<PVector> get_full_animation(){
    int total_steps = int(animation_time * steps_per_second);
    ArrayList<PVector> full_animation = new ArrayList<PVector>();
    
    for(int i = 0; i < total_steps; i++){
        float angle =  i * 360.0 / (animation_time * steps_per_second);
        angle = angle%360;
        full_animation.add(transform(angle,animation_floor_height, animation_stride_length, animation_wheel_base));
    }
    return full_animation;
  }
  
}
