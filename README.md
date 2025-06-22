# SDN Video Streaming with Load Balancing

## Overview
This project implements a Software-Defined Networking (SDN) based video streaming platform with dynamic load balancing. Using Mininet for network emulation and a Ryu-based SDN controller, the system distributes client video requests across multiple servers using various load balancing algorithms. The project includes a real-time monitoring dashboard and a comprehensive test environment for validation.

---

## Architecture
- **Mininet Topology**: Custom topology with 1 border switch, 3 core switches, 3 leaf switches, 4 video servers, and 1 client.
- **SDN Controller**: Ryu application that intercepts client requests, applies load balancing, and manages OpenFlow rules.
- **Load Balancer**: Modular, supports Random, Round Robin, Weighted Round Robin, Bandwidth-Aware, and Request Demand algorithms.
- **Video Servers**: Python HTTP servers streaming video files.
- **Client**: Python script for listing and downloading videos.
- **Dashboard**: Flask-based web dashboard for real-time monitoring.
- **Test Environment**: Automated simulation and validation tools.

---

## Directory Structure
```
sdn-video-streaming/
│
├── topo/
│   └── custom_topo.py              # Mininet topology definition
│
├── controller/
│   ├── sdn_controller.py           # Ryu SDN controller
│   ├── load_balancer.py            # Load balancing logic
│   └── __init__.py
│
├── servers/
│   └── server.py                   # Video streaming server
│
├── client/
│   └── test_client.py              # Client for video requests
│
├── dashboard/
│   └── monitor.py                  # Flask dashboard
│   └── __init__.py
│
├── test/
│   └── test_environment.py         # Automated test environment
│   └── __init__.py
│
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
└── ...
```

---

## Setup Instructions

### 1. Prerequisites
- Python 3.7+
- Mininet (for network emulation)
- Ryu SDN Framework
- (Optional) Flask for dashboard

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Mininet Topology
Run the custom topology:
```bash
sudo python3 topo/custom_topo.py
```
This will launch the Mininet CLI and start HTTP servers on each video server node.

### 4. SDN Controller
In a separate terminal, start the Ryu controller:
```bash
ryu-manager controller/sdn_controller.py
```

### 5. Video Servers
Servers are started automatically by the topology script. To run standalone:
```bash
python3 servers/server.py
```

### 6. Client
Use the provided client to list and download videos:
```bash
python3 client/test_client.py --server http://<server-ip>:8000
```

### 7. Dashboard (Optional)
To launch the monitoring dashboard:
```bash
python3 dashboard/monitor.py
```
Access the dashboard at [http://localhost:5001](http://localhost:5001).

---

## Load Balancing Algorithms
- **Random**: Selects a server at random.
- **Round Robin**: Cycles through servers sequentially.
- **Weighted Round Robin**: Considers server weights and current connections.
- **Bandwidth-Aware**: Chooses the server with the lowest bandwidth usage.
- **Request Demand Based**: Selects based on current connections and response time.

Algorithm selection can be configured in `controller/sdn_controller.py`.

---

## Testing
The `test/test_environment.py` script simulates the network, servers, and client requests for automated testing and validation. It can be used to:
- Simulate video requests
- Validate load balancing logic
- Collect performance statistics

---

## Troubleshooting & Tips
- Ensure all dependencies are installed and Mininet is running with root privileges.
- Use `ryu-manager` for the controller and verify the correct OpenFlow version (1.3).
- Check log files (`controller.log`, `server.log`, `client.log`, `test_environment.log`) for detailed error messages.
- For network issues, use Mininet CLI tools (`pingall`, `iperf`, `dpctl dump-flows`).

---

---

