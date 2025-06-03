

````markdown
# SDN Final Project: Video Streaming with Load Balancing (Mininet + Python)

## 📘 Section 1 – Project Overview (What You Need to Do)

This section provides a comprehensive breakdown of all tasks to complete the project successfully.

###  1. Build the Network: Mininet Topology
- You need to create a **custom network topology** using Mininet.
- The network should include:
  - 1 **border switch (S1)**
  - 2–3 **intermediate/core switches (S2–S4)**
  - 3 **leaf switches (S5–S7)**
  - 4 **video servers (Server1–Server4)**
  - At least 1 **client**
- This topology should be written in a Python file (e.g., `custom_topo.py`).

---

###  2. Implement the SDN Controller
- Use an SDN controller such as **POX** or **Ryu**.
- The controller should:
  - Act like a DNS system to intercept client requests (e.g., for "netflix.com").
  - Decide which server should handle the request.
  - Push the appropriate **flow rules** to the network switches.

---

###  3. Implement Load Balancing Logic
- Integrate a load balancing algorithm into your controller:
  - `Random`
  - `Round Robin`
  - `Weighted Round Robin`
  - `Bandwidth-Aware`
  - `Request Demand Based`
- Each incoming client request should be forwarded to the most appropriate server based on the selected algorithm.

---

###  4. Simulate Video Streaming
- On each server, run a lightweight HTTP server using Python:
  ```bash
  python3 -m http.server
````

* From the client node, request video files using tools like `curl` or `wget`.
* The controller should dynamically manage the routing of these requests.

---

###  5. Create a Dashboard or Logging System (Optional but Recommended)

* Build a simple monitoring interface to visualize:

  * Active servers
  * Server load statistics
  * Real-time traffic details (who requested what, and from which server)

---

###  6. Prepare Final Report & Presentation

* Prepare a short but clear report explaining:

  * Your architecture and flow
  * Chosen algorithms and rationale
  * Test results and screenshots
  * Challenges faced and how you overcame them

---

##  Section 2 – How to Do It (Languages, Tools, and Tips)

This section details the technologies you'll use and best practices to follow.

---

###  Languages & Tools to Use

| Component            | Language / Tool                |
| -------------------- | ------------------------------ |
| Network Topology     | Python (Mininet API)           |
| SDN Controller       | Python (POX or Ryu)            |
| Load Balancing Logic | Python                         |
| Video Servers        | Python (`http.server`)         |
| Client Testing       | Bash (`curl`, `wget`, `iperf`) |
| Dashboard (Optional) | Python (Flask/Dash) or HTML/JS |

---

### 🗂 Recommended Project Structure

```
sdn-video-streaming/
│
├── topo/
│   └── custom_topo.py              # Mininet topology definition
│
├── controller/
│   └── sdn_controller.py           # SDN controller with load balancing logic
│
├── servers/
│   ├── server1/
│   │   └── video.mp4
│   └── server2/ ...
│
├── client/
│   └── test_client.sh              # Shell script for client testing
│
├── dashboard/                      # Optional dashboard implementation
│   └── monitor.py
│
├── logs/
│   └── traffic_log.txt             # Logging traffic or results
│
└── README.md                       # This documentation
```

---

###  Key Considerations & Best Practices

1. **Flow Control**

   * Your controller must install correct flow rules for each new connection.
   * You can verify this using `dpctl dump-flows` or Ryu’s REST API.

2. **Connectivity Testing**

   * Test the connectivity between nodes using tools like `ping`, `iperf`, and `curl`.
   * You can inspect network traffic using `tcpdump` or `Wireshark`.

3. **Algorithm Strategy**

   * Start with simple algorithms like `round robin`.
   * If time allows, implement dynamic strategies based on bandwidth or latency.

4. **Time Management**

   * Begin with topology creation, then build the controller, and finally integrate load balancing.
   * Add the dashboard if there is time left.

---

###  Suggested Development Order

1. Create the Mininet topology.
2. Develop and run the Python-based SDN controller (POX or Ryu).
3. Add your load balancing algorithm.
4. Launch HTTP servers and test client requests.
5. Implement dashboard or logging (optional).
6. Document and finalize the report.

---

### 📚 Helpful Resources

* [Mininet Walkthrough](http://mininet.org/walkthrough/)
* [POX Controller Wiki](https://openflow.stanford.edu/display/ONL/POX+Wiki)
* [Ryu SDN Framework](https://osrg.github.io/ryu/)
* [Python HTTP Server](https://docs.python.org/3/library/http.server.html)

---

**Good luck! You’re building a real SDN-driven video service router 🚀**

```

---

