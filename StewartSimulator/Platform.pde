import Jama.Matrix; 


class Platform {
  private PVector translation, rotation, origin, attitude;
  private PVector[] base_joint, platform_joint, base, platform;

  private final float base_angles[] = {50, 70, 170, 190, 290, 310};
  private final float platform_angles[]  = {10, 110, 130, 230, 250, 350};
  private final float base_radius = 36;
  private final float platform_radius = 15;
  private final float initial_height = 15;
  private final float cylinder_length = 13;
  private final float scale = 1.0;
  

  public Platform(PVector origin, PVector attitude) {
    //Platform location
    this.origin = origin;
    this.attitude = attitude;
    
    
    //initialize variables
    translation = new PVector();
    rotation = new PVector();
    base_joint = new PVector[6];
    platform_joint = new PVector[6];
    base = new PVector[6];
    platform = new PVector[6];


    //generate base
    for (int i=0; i<6; i++) {
      float mx = this.base_radius*cos(radians(this.base_angles[i]));
      float my = this.base_radius*sin(radians(this.base_angles[i]));
      base_joint[i] = new PVector(mx, my, 0);
    }
    
    //generate platform
    for (int i=0; i<6; i++) {
      float mx = this.platform_radius*cos(radians(this.platform_angles[i]));
      float my = this.platform_radius*sin(radians(this.platform_angles[i]));
      platform_joint[i] = new PVector(mx, my, 0);
    }
    
    //fill arrays
    for (int i=0; i<6; i++) {
      base[i] = new PVector(0, 0, 0);
      platform[i] = new PVector(0, 0, 0);
    }
    
    transform(translation,rotation);
  }


  private void transform(PVector t, PVector r) {
    rotation.set(r);
    translation.set(t);
    
    
    //rotate around base
    base = rotate_mat_ZYX(attitude, base_joint);
    platform = rotate_mat_ZYX(attitude, platform_joint);
    
    //rotate platform(global) -- apply rotation here for global cooridnates
    platform = rotate_mat_ZYX(rotation, platform);
    
    
    //extend platform to initial position(local frame)
    PVector[] initial_local = {new PVector(0.0,0.0,scale*initial_height)};
    PVector initial_global = rotate_mat_ZYX(attitude,initial_local)[0];
    platform = translate_mat(initial_global, platform);
    
    //translate base to origin
    base = translate_mat(origin, base);
    platform = translate_mat(origin,platform);
    
    //translate platform to final position
    platform = translate_mat(translation,platform);
  }


 public float[] get_length(){
   float[] l = new float[6];
   for(int i = 0; i <6; i++){
     l[i] = PVector.sub(platform[i], base[i]).mag() - cylinder_length;
    }
   return l;
 }


  public void draw() {
    
    // draw Base
    fill(56);
    beginShape();
    for (int i = 0; i < 6; i++) {
      vertex(base[i].x,base[i].y,base[i].z);
    }
    endShape(CLOSE);
      
      
    //draw platform
    noFill();
    stroke(255);
    strokeWeight(3);
    beginShape();
    for (int i = 0; i < 6; i++) {
      vertex(platform[i].x,platform[i].y,platform[i].z);
    }
    endShape(CLOSE);
  
    // draw rods
    for (int i=0; i<6; i++) {
       stroke(150);
       strokeWeight(1);
       line(base[i].x, base[i].y, base[i].z, platform[i].x, platform[i].y, platform[i].z);
     }
    
  }
  
  public PVector[] rotate_mat_ZYX(PVector rotation, PVector[] mat){

    //create rotation matrix
    double[][] z = {{cos(rotation.z),-sin(rotation.z),0},
                    {sin(rotation.z), cos(rotation.z),0},
                    {       0       ,        0       ,1}};
    Matrix Z = new Matrix(z);
    double[][] y = {{cos(rotation.y),0,sin(rotation.y)},
                    {       0       ,1,       0       }, 
                    {-sin(rotation.y),0,cos(rotation.y)}};
    Matrix Y = new Matrix(y);
    double[][] x = {{1,      0        ,        0       },
                    {0,cos(rotation.x),-sin(rotation.x)},
                    {0,sin(rotation.x), cos(rotation.x)}};
    Matrix X = new Matrix(x);
    //calculate rotation matrix
    Matrix rot = Z.times(Y).times(X);
    
    //apply rotation matrix to data set
    PVector[] product = new PVector[mat.length];
    
    for(int i = 0; i < mat.length; i++){
      double[][] t = {{mat[i].x},{mat[i].y},{mat[i].z}};
      Matrix temp = new Matrix(t); //convert vector to matrix
      double[][] result = rot.times(temp).getArray(); //apply rotation
      product[i] = new PVector((float)result[0][0],(float)result[1][0],(float)result[2][0]); //convert back to vector
    }
    
    return product;
  }
  
  private PVector[] translate_mat(PVector translation, PVector[] mat){
    PVector[] product = new PVector[mat.length];
    for(int i = 0; i < mat.length; i++){
      product[i] = PVector.add(mat[i],translation);
    }
    return product;
  }

}
