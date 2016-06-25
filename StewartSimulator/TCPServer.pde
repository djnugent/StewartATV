import java.io.*;
import java.net.*;


class Server implements Runnable {
  private Thread t;
  private ServerSocket serverSocket;
  private int port;
  public ArrayList<Client> clients;
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
        Client new_client = new Client(serverSocket.accept(),this);
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
  private Server server;
  private PrintWriter out;
  private BufferedReader in; 
  private Callback onDataReceivedCallback;
  private double last_heartbeat = 0;
  private boolean running = false;
  public int id = -1;
  public boolean error = false;


  public Client(Socket clientSocket, Server server) {
    this.clientSocket = clientSocket;
    this.server = server;

    try {
      this.clientSocket.setTcpNoDelay(true);
      out = new PrintWriter(clientSocket.getOutputStream(), true);
      in = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
    }
    catch(IOException e) {
      println("Unable to connect to client socket");
    }
   
  }

  public void run() {
    while (running) {
      try{
        //try to recv data
        JSONObject obj = readJSON();
        if (obj.size() > 0) {
          if (obj.getString("msg_id").equals("heartbeat")) {
            id = obj.getInt("id");
            last_heartbeat = millis()/1000.0;
          } else if (onDataReceivedCallback != null) {
            onDataReceivedCallback.execute(obj);
          }
        }
        //no data available
        else{
          if(!is_alive()){
            println("client has disconnected");
            stop();
            server.clients.remove(this);
          }
        }
      }
      catch(IOException e) {
            error = true;
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

  public JSONObject readJSON() throws IOException { 
    JSONObject obj = new JSONObject();
    if(in.ready()){  
      String line = in.readLine();
      if (line != null && line.length() > 0) {
        obj = parseJSONObject(line);
      }
    }
    return obj;
  }

  public void send(JSONObject json) {
    String data = json.toString().replace("\n", "").replace("\r", "");
    out.println(data);
    out.flush();
  }

  public boolean is_alive() {
    return !error && (millis()/1000.0 - last_heartbeat < 2) && running;
  }

  public void set_onDataReceivedCallback(Callback callback) {
    onDataReceivedCallback = callback;
  }
}


public interface Callback{
  public void execute(Object... args);
}

