import java.io.*;
import java.net.*;

Server ser;

void setup() {
  int portNumber = 9876;
  ser = new Server(portNumber);
  ser.start();
  
  
  Callback client_connect = new Callback(){
      public void execute(Object... args){
        println("we have a new client");
        Client c = ser.get_clients().get(0);
        c.send("hello");
      }
  };
  ser.set_onClientConnectCallback(client_connect);
  
  
}

void draw() {
}





class Server implements Runnable {
  private Thread t;
  private ServerSocket serverSocket;
  private int port;
  private ArrayList<Client> clients;
  private Callback onClientConnectCallback;


  public Server(int port) {
    this.port = port;
    clients = new ArrayList<Client>();
    try {
      serverSocket = new ServerSocket(this.port);
    }
    catch(IOException e) {
      println("Unable to start server, IO error");
    }
  }


  public void start() {
    println("Starting Server: Accepting clients on port " + port);
    if (t == null) {
      t = new Thread (this, "ServerListeningThread");
      t.start ();
    }
  }

  public void stop() {
    try {
      serverSocket.close();
    }
    catch(IOException e) {
      println("Unable to close socket. Was it ever opened?");
    }
  }


  public void run() {
    try {
      while (true) {
        //accept new clients
        Client new_client = new Client(serverSocket.accept());
        new_client.start();
        clients.add(new_client);

        //run onClientConnectCallback
        if (onClientConnectCallback != null) {
          onClientConnectCallback.execute(new_client);
        }
        
        
        
        
      }
    }
    catch(SocketException e) {
      println("Server closed");
    }
    catch(Exception e) {
      e.printStackTrace();
    }
  }

  public void set_onClientConnectCallback(Callback callback) {
    onClientConnectCallback = callback;
  }

  public ArrayList<Client> get_clients() {
    return clients;
  }
}


class Client implements Runnable {
  private Thread t;
  private Socket clientSocket;
  private PrintWriter out;
  private BufferedReader in; 
  private Callback onDataReceivedCallback;
  private double last_heartbeat = 0;
  private boolean running = false;

  public Client(Socket clientSocket) {
    this.clientSocket = clientSocket;
    try {
      out = new PrintWriter(clientSocket.getOutputStream(), true);
      in = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
    }
    catch(IOException e) {
      println("Unable to connect to client socket");
    }
  }

  public void run() {
    while (running) {
      JSONObject obj = readJSON();
      if (obj.size() > 0) {
        if (obj.getString("msg_id") == "heartbeat") {
          last_heartbeat = System.currentTimeMillis()/1000.0;
        } else if (onDataReceivedCallback != null) {
          onDataReceivedCallback.execute(obj);
        }
      }
    }
  }

  public void start() {
    running = true;
    println("Starting Client: Listening for incoming messages");
    if (t == null) {
      t = new Thread (this, "ClientListeningThread");
      t.start ();
    }
  }

  public void stop() {
    running = false;
  }

  private JSONObject readJSON() {
    String jsonData = "";
    String line;
    try {
      while ( (line = in.readLine ()) != null) {
        jsonData += line + "\n";
      }
    }
    catch(IOException e) {
      println("Error reading TCP packet");
    }
    JSONObject obj = new JSONObject();
    if (jsonData.length() > 0) {
      obj = parseJSONObject(jsonData);
    }
    return obj;
  }

  public void send(String data) {
    out.println(data);
    out.flush();
  }

  public boolean connected() {
    return (System.currentTimeMillis()/1000.0 - last_heartbeat < 2);
  }

  public void set_onDataRecievedCallback(Callback callback) {
    onDataReceivedCallback = callback;
  }
}


public interface Callback {
  public void execute(Object... args);
}

