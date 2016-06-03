import Jama.Matrix; 


class Platform {
  private PVector translation, rotation, origin, attitude;
  private PVector[] base_joint, platform_joint, base, platform;
  float[] l;
  public int[] scaled_positions;
  public boolean over_extended = false;
  public boolean over_retracted = false;


  private final float base_angles[] = {
    53.82161, 66.17839, 173.82161, 186.17839, 293.82161, 306.17839
  };
  private final float platform_angles[]  = {
    21.7867, 98.2133, 141.7867, 218.2133, 261.7867, 338.2133
  };
  private final float base_radius = 13.937;
  private final float platform_radius = 4.041;
  private final float initial_height = 24;
  private final float rod_base = 26; //piston housing length
  private final float rod_throw = 18; //max piston travel
  private final float scale = 1.0;

  private Client client;
  private int stream_mode = 0;
  private int stream_rate = 10;

  public Platform(PVector origin, PVector attitude) {

    //Platform location
    this.origin = origin;
    this.attitude = attitude;


    //initialize variables
    translation = new PVector();
    rotation = new PVector();
    base_joint = new PVector[6];
    platform_joint = new PVector[7];
    base = new PVector[6];
    platform = new PVector[6];
    l = new float[6];
    scaled_positions = new int[6];
    

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
    platform_joint[6] = new PVector(0, 0, 7.5); 


    //fill arrays
    for (int i=0; i<6; i++) {
      base[i] = new PVector(0, 0, 0);
      platform[i] = new PVector(0, 0, 0);
    }

    transform(translation, rotation);
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
    PVector[] initial_local = {
      new PVector(0.0, 0.0, scale*initial_height)
      };
      PVector initial_global = rotate_mat_ZYX(attitude, initial_local)[0];
    platform = translate_mat(initial_global, platform);

    //translate base to origin
    base = translate_mat(origin, base);
    platform = translate_mat(origin, platform);

    //translate platform to final position
    platform = translate_mat(translation, platform);

    //calculate the length of the rods and scaled digital value
    over_extended = false;
    over_retracted = false;
    for (int i = 0; i <6; i++) {
      //rod length
      l[i] = PVector.sub(platform[i], base[i]).mag() - rod_base;
      //scale it to digital value
      scaled_positions[i] = int(map(l[i], 0, rod_throw ,0,4095));
      //check model constraints
      if(scaled_positions[i] > 4095){
        over_extended = true;
      }
      if(scaled_positions[i] < 0){
        over_retracted = true;
      }
    }
  }

  
  public void setClient(Client client) {
    //redirect callback to interal method
    Callback data_received = new Callback(){public void execute(Object... args){callback(args);}};
    this.client = client;
    //set callback
    this.client.set_onDataReceivedCallback(data_received);
    //request feedback
    request_feedback_stream(stream_mode, stream_rate);
  }
  
  public void request_feedback_stream(int stream_mode,int stream_rate){
    //request data stream
    JSONObject json = new JSONObject();
    json.setString("msg_id", "request_feedback_stream");
    json.setInt("stream_mode",stream_mode);
    json.setInt("stream_rate", stream_rate);
    client.send(json);
  }

  public void callback(Object... args){
    JSONObject json = (JSONObject)args[0];
    println(json);
  }
  
  public float[] get_length() {
    return l;
  }

  public PVector[] get_base() {
    return base;
  }

  public PVector[] get_platform() {
    return platform;
  }
  
  public void send_position(){
    //package data
    JSONObject json = new JSONObject();
    json.setString("msg_id", "set_value");
    json.setString("value_type", "position");
    JSONArray values = new JSONArray();
    for(int i = 0; i < 6; i++){
      JSONObject value = new JSONObject();
      value.setInt(i+"",scaled_positions[i]);
      values.setJSONObject(i,value);
    }
    json.setJSONArray("values",values);
    //check for connection and valid data
    if(client != null && !over_extended && !over_retracted){
      client.send(json);
    }
    
  }

  public void draw() {

    // draw Base
    fill(56);
    noStroke();
    beginShape();
    for (int i = 0; i < 6; i++) {
      vertex(base[i].x, base[i].y, base[i].z);
    }
    endShape(CLOSE);


    //draw platform
    noFill();
    stroke(255);
    strokeWeight(3);
    beginShape();
    for (int i = 0; i < 6; i++) {
      vertex(platform[i].x, platform[i].y, platform[i].z);
    }
    endShape(CLOSE);


    //draw cylinders
    PVector[] cylinder = new PVector[6];
    for (int i = 0; i <6; i++) {
      cylinder[i] = PVector.sub(platform[i], base[i]);
      cylinder[i].normalize();
      cylinder[i].mult(rod_base);
      cylinder[i].add(base[i]);
      if (l[i] < 0) {
        stroke(150, 0, 0);
      } else if (l[i] > rod_throw) {
        stroke(0, 0, 150);
      } else {
        stroke(0, 150, 0);
      }
      strokeWeight(3);
      line(base[i].x, base[i].y, base[i].z, cylinder[i].x, cylinder[i].y, cylinder[i].z);
    } 

    // draw rods
    for (int i=0; i<6; i++) {
      stroke(150);
      strokeWeight(1);
      line(cylinder[i].x, cylinder[i].y, cylinder[i].z, platform[i].x, platform[i].y, platform[i].z);
    }
  }

  public PVector[] rotate_mat_ZYX(PVector rotation, PVector[] mat) {

    //create rotation matrix
    double[][] z = {
      {
        cos(rotation.z), -sin(rotation.z), 0
      }
      , 
      {
        sin(rotation.z), cos(rotation.z), 0
      }
      , 
      {       
        0, 0, 1
      }
    };
    Matrix Z = new Matrix(z);
    double[][] y = {
      {
        cos(rotation.y), 0, sin(rotation.y)
        }
        , 
      {       
        0, 1, 0
      }
      , 
      {
        -sin(rotation.y), 0, cos(rotation.y)
        }
      };
      Matrix Y = new Matrix(y);
    double[][] x = {
      {
        1, 0, 0
      }
      , 
      {
        0, cos(rotation.x), -sin(rotation.x)
        }
        , 
      {
        0, sin(rotation.x), cos(rotation.x)
        }
      };
      Matrix X = new Matrix(x);
    //calculate rotation matrix
    Matrix rot = Z.times(Y).times(X);

    //apply rotation matrix to data set
    PVector[] product = new PVector[mat.length];

    for (int i = 0; i < mat.length; i++) {
      double[][] t = {
        {
          mat[i].x
        }
        , {
          mat[i].y
        }
        , {
          mat[i].z
        }
      };
      Matrix temp = new Matrix(t); //convert vector to matrix
      double[][] result = rot.times(temp).getArray(); //apply rotation
      product[i] = new PVector((float)result[0][0], (float)result[1][0], (float)result[2][0]); //convert back to vector
    }

    return product;
  }

  private PVector[] translate_mat(PVector translation, PVector[] mat) {
    PVector[] product = new PVector[mat.length];
    for (int i = 0; i < mat.length; i++) {
      product[i] = PVector.add(mat[i], translation);
    }
    return product;
  }
}

