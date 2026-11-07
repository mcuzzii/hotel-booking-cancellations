## Downloading the Dataset

```bash
make download
```

## Running the Notebook

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Visual Studio Code](https://code.visualstudio.com/)
- VS Code extensions:
  - Python (Microsoft)
  - Jupyter (Microsoft)

No local Python or uv installation is required.

### 1. Clone the repository

```bash
git clone https://github.com/mcuzzii/hotel-booking-cancellations
cd hotel-booking-cancellations
```

### 2. Build and start the Docker environment

```bash
make up
```

This builds the Python environment and installs all dependencies using uv.

### 3. Start Jupyter Server

```bash
make notebook
```

Keep this terminal running. Copy the authenticated URL printed in the terminal. Press Ctrl/Cmd+D to end the session.

### 4. Connect VS Code

1. Open the cloned repository in VS Code.
2. Open a notebook in `notebooks/`.
3. Select the notebook kernel.
4. Choose **Select Another Kernel → Existing Jupyter Server**.
5. Enter the Jupyter Server URL printed in the previous step.

Select the `Python (Docker)` kernel if prompted.

You can now execute notebook cells directly in VS Code.

### 5. Stop the environment

```bash
make down
```

Your notebooks and project files remain on your local filesystem. The Docker-managed Python environment persists in its named volume.