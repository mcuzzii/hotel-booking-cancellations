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

This builds and starts the required docker containers.

### 3. Initialize dependencies

```bash
make initialize
```

This installs all dependencies and the Jupyter server.

### 4. Start Jupyter Server

```bash
make notebook
```

Keep this terminal running. Copy the authenticated URL printed in the terminal. Press Ctrl/Cmd+D to end the session.

### 5. Connect VS Code

1. Open the cloned repository in VS Code.
2. Open a notebook in `notebooks/`.
3. Select the notebook kernel.
4. Choose **Select Another Kernel → Existing Jupyter Server**.
5. Enter the Jupyter Server URL printed in the previous step.

Select the `Python (Docker)` kernel if prompted.

You can now execute notebook cells directly in VS Code.

### 6. Stop the environment

```bash
make down
```

You may need to close the Jupyter server first by pressing `Ctrl/Cmd+C`. Notebooks and project files remain on your local filesystem. The Docker-managed Python environment persists in its named volume.

## Running a New Session

Simply run the following; no need to re-initialize.

```bash
make up
make notebook
```

End the session with `make down`.