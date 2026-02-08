# Project Swarm3x - Multimodal Communication System

This project implements a multi-modal, multi-communication system for autonomous swarm agents. It features a separation of concerns between the immutable "Swarm Core" logic and the adaptable "Communication Controller".

## Structure

*   `swarm_core.py`: **StandardSwarmCore**. Immutable decision-making engine. Version 3.7-STANDARD.
*   `communication.py`: **CommunicationController**. Adaptable layer handling protocols (JSON/TCP), corrections, and sensor processing.
*   `agent.py`: Main entry point for the **Agent** (Robot). Connects to the Simulator/Server.
*   `simulator.py`: **GameSimulator**. PyGame-based visualization acting as the Server/Environment.

## Requirements

*   Python 3.x
*   PyGame (`pip install pygame`)

## How to Run

### 1. Start the Simulator (Server)

The simulator acts as the environment and server. It displays the agent and obstacles.

```bash
python Swarm3x/simulator.py
```

*   **Controls**: The simulator runs automatically.
*   **Visuals**:
    *   Blue Circle: Agent
    *   Grey Circles: Obstacles
    *   Green/Red Cones: Ultrasonic Sensors (Green=Clear, Red=Obstacle detected)
    *   Lines: Raycasts

### 2. Start the Agent (Client)

The agent connects to the simulator, receives sensor data, processes it through SwarmCore, and sends back movement commands.

```bash
python Swarm3x/agent.py --host 127.0.0.1 --port 8888
```

## Architecture

*   **Communication**: JSON over TCP.
*   **Protocol**:
    *   Sensor Data (Server -> Client): `dist_front`, `dist_left`, `dist_right`, `pos_x`, `pos_y`, `angle`.
    *   Command Data (Client -> Server): `speed_left`, `speed_right`, `action`, `zone`.
*   **SwarmCore**: Uses standard logic (Emergency Stop, Avoidance, Navigation) which is strictly separated from the communication layer.

## Future Expansion

*   **Serial Communication**: The `CommunicationController` is designed to support additional protocols like Serial/UART.
*   **Neural Network**: The `SwarmCore` can be extended or replaced (via the config) with a neural network-based decision engine without changing the communication infrastructure.
