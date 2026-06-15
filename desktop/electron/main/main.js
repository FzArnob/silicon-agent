const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = 8000;
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

let mainWindow = null;
let backendProcess = null;

function getPythonCommand() {
  return process.platform === "win32" ? "python" : "python3";
}

function startBackend() {
  const projectRoot = path.join(__dirname, "..", "..");
  const env = {
    ...process.env,
    PYTHONUNBUFFERED: "1",
    PYTHONPATH: projectRoot,
  };
  const python = getPythonCommand();

  backendProcess = spawn(python, [
    "-m",
    "uvicorn",
    "backend.app.main:app",
    "--host",
    BACKEND_HOST,
    "--port",
    String(BACKEND_PORT),
  ], {
    cwd: projectRoot,
    env,
    stdio: "pipe",
    windowsHide: true,
  });

  backendProcess.stdout.on("data", (data) => {
    process.stdout.write(`[backend] ${String(data)}`);
  });

  backendProcess.stderr.on("data", (data) => {
    process.stderr.write(`[backend] ${String(data)}`);
  });

  backendProcess.on("exit", (code) => {
    process.stdout.write(`[backend] exited with code ${code}\n`);
    backendProcess = null;
  });
}

async function waitForBackend(timeoutMs = 30000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/health`);
      if (response.ok) {
        return true;
      }
    } catch (error) {
      // Backend not ready yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    title: "Silicon Agent - Plansheet Desktop",
    autoHideMenuBar: true,
    backgroundColor: "#0f172a",
    webPreferences: {
      preload: path.join(__dirname, "..", "preload", "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  const rendererPath = path.join(__dirname, "..", "renderer", "index.html");
  mainWindow.loadFile(rendererPath);

  if (!app.isPackaged) {
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  startBackend();
  const backendOk = await waitForBackend();
  if (!backendOk) {
    process.stderr.write("Backend did not become ready in time.\n");
  }
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
