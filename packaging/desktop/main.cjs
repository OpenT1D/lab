'use strict';

const { app, BrowserWindow, Menu, dialog, ipcMain, screen } = require('electron');
const { spawn } = require('node:child_process');
const { randomUUID, createHash } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

app.setName('OpenT1D');

function argument(name) {
  const index = process.argv.indexOf(name);
  return index < 0 ? undefined : process.argv[index + 1];
}
const workspaceArgument = argument('--workspace');
if (workspaceArgument && !path.isAbsolute(workspaceArgument)) throw new Error('Choose an absolute workspace path.');
const workspace = workspaceArgument || path.join(app.getPath('appData'), 'OpenT1D', 'Concept-v1', 'workspace');
const profile = workspaceArgument
  ? path.join(app.getPath('temp'), 'OpenT1D-Concept-profiles', createHash('sha256').update(workspace).digest('hex').slice(0, 16))
  : path.join(app.getPath('appData'), 'OpenT1D', 'Concept-v1', 'desktop');
fs.mkdirSync(profile, { recursive: true });
app.setPath('userData', profile);

let window, backend, ready, backendExit, finalQuit = false, quitting = false, rendererDead = false;
let currentView = 'startup', workspaceBounds = null, pendingClose = null;
const stderr = [];

function workspaceURL(value) {
  try {
    const url = new URL(value);
    return url.origin === ready?.origin && url.pathname === '/workbench' && !url.search;
  } catch { return false; }
}
function trusted(event) {
  return !!window && event.sender === window.webContents &&
    event.senderFrame === window.webContents.mainFrame &&
    workspaceURL(event.senderFrame.url);
}

function startBackend() {
  const root = app.isPackaged ? path.join(process.resourcesPath, 'backend') : argument('--backend');
  if (!root || !path.isAbsolute(root)) throw new Error('The bundled local service is missing.');
  const python = path.join(root, 'runtime', 'bin/python3.12');
  const environment = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
    !key.startsWith('PYTHON') && !key.startsWith('UV_') && !['VIRTUAL_ENV', '__PYVENV_LAUNCHER__', 'ELECTRON_RUN_AS_NODE'].includes(key)));
  backend = spawn(python, ['-I', '-B', '-S', path.join(root, 'entry.py'), '--workspace', workspace], {
    cwd: root, env: environment, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'],
  });
  backendExit = new Promise(resolve => backend.once('exit', (code, signal) => resolve({ code, signal })));
  backend.stderr.on('data', chunk => { stderr.push(chunk.toString()); while (stderr.join('').length > 8000) stderr.shift(); });
  return new Promise((resolve, reject) => {
    let buffer = '', settled = false;
    const timer = setTimeout(() => finish(new Error('The local service did not become ready.')), 30000);
    function finish(error, value) {
      if (settled) return;
      settled = true; clearTimeout(timer);
      backend.stdout.removeListener('data', data);
      error ? reject(error) : resolve(value);
    }
    function data(chunk) {
      buffer += chunk.toString();
      if (buffer.length > 16384) return finish(new Error('Unexpected local-service startup response.'));
      const end = buffer.indexOf('\n');
      if (end < 0) return;
      try {
        const message = JSON.parse(buffer.slice(0, end));
        const url = new URL(message.origin);
        if (message.schema !== 'opent1d.desktop-ready/1' || url.protocol !== 'http:' ||
            url.hostname !== '127.0.0.1' || !url.port || url.pathname !== '/' || url.search || url.hash ||
            url.username || url.password || !/^[a-f0-9]{64}$/.test(message.token)) throw new Error();
        finish(null, { origin: url.origin, token: message.token });
      } catch { finish(new Error('The bundled local service returned an invalid startup response.')); }
    }
    backend.stdout.on('data', data);
    backend.once('error', error => finish(error));
    backend.once('exit', () => finish(new Error('The local service stopped during startup.\n' + stderr.join(''))));
  });
}

function command(name) { if (window && !quitting) window.webContents.send('desktop:command', name); }
function setView(view) {
  if (!['startup', 'workspace'].includes(view) || currentView === view || !window) return;
  if (currentView === 'workspace') workspaceBounds = { bounds: window.getBounds(), maximized: window.isMaximized() };
  currentView = view;
  if (window.isMaximized()) window.unmaximize();
  if (view === 'workspace' && workspaceBounds) {
    window.setBounds(workspaceBounds.bounds);
    if (workspaceBounds.maximized) window.maximize();
  } else {
    const area = screen.getDisplayMatching(window.getBounds()).workAreaSize;
    const wanted = view === 'startup' ? [920, 420] : [1440, 900];
    window.setContentSize(Math.min(wanted[0], area.width - 32), Math.min(wanted[1], area.height - 32));
    window.center();
  }
}

function rendererClose(mode) {
  if (rendererDead || !window || window.webContents.isDestroyed()) return Promise.resolve({ canClose: true });
  return new Promise(resolve => {
    const id = randomUUID();
    const timer = setTimeout(() => { pendingClose = null; resolve({ canClose: false, unavailable: true, message: 'The workspace is not responding. You can keep OpenT1D open or quit with the last saved study.' }); }, 45000);
    pendingClose = { id, resolve: answer => { clearTimeout(timer); pendingClose = null; resolve(answer); } };
    window.webContents.send('desktop:prepare-close', { id, mode });
  });
}

async function stopBackend() {
  if (!backend || backend.exitCode !== null || backend.signalCode !== null) return;
  if (ready) {
    try {
      await fetch(ready.origin + '/api/shutdown', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Origin': ready.origin, 'X-OpenT1D-Token': ready.token },
        body: '{}', signal: AbortSignal.timeout(5000),
      });
    } catch { /* EOF also requests authenticated, locally owned service cleanup. */ }
  }
  backend.stdin.end();
  let timer;
  try {
    await Promise.race([backendExit, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('The local service is still finishing its work. Keep OpenT1D open and try quitting again.')), 65000); })]);
  } finally { clearTimeout(timer); }
}

async function requestQuit() {
  if (quitting || finalQuit) return;
  quitting = true;
  try {
    let answer = await rendererClose('check');
    if (answer.unavailable) {
      const { response } = await dialog.showMessageBox(window, { type: 'warning', title: 'Quit OpenT1D', message: answer.message, buttons: ['Keep OpenT1D open', 'Quit with saved work'], defaultId: 0, cancelId: 0 });
      if (response === 0) return;
      answer = { canClose: true };
    }
    if (!answer.canClose) {
      const options = answer.busy ? ['Keep working', 'Stop and quit'] : ['Save and quit', 'Discard unsaved changes and quit', 'Cancel'];
      const { response } = await dialog.showMessageBox(window, {
        type: 'question', title: 'Quit OpenT1D', message: answer.message || 'Save your changes before quitting?',
        buttons: options, defaultId: 0, cancelId: answer.busy ? 0 : 2,
      });
      if ((answer.busy && response === 0) || (!answer.busy && response === 2)) return;
      answer = await rendererClose(answer.busy || response === 1 ? 'discard' : 'save');
      if (!answer.canClose) { await dialog.showMessageBox(window, { type: 'warning', message: answer.message || 'The current study could not be saved.', buttons: ['Keep working'] }); return; }
    }
    await stopBackend();
    finalQuit = true;
    window?.destroy();
    app.quit();
  } catch (error) {
    await dialog.showMessageBox(window, { type: 'error', title: 'OpenT1D', message: error.message, buttons: ['Keep OpenT1D open'] });
  } finally { quitting = false; }
}

function installMenu() {
  const file = { label: 'File', submenu: [
    { label: 'New Project…', accelerator: 'CmdOrCtrl+N', click: () => command('new-project') },
    { label: 'Open Project…', accelerator: 'CmdOrCtrl+O', click: () => command('open-project') },
    { label: 'Save', accelerator: 'CmdOrCtrl+S', click: () => command('save') },
    { type: 'separator' }, { label: 'Close Project', accelerator: 'CmdOrCtrl+Shift+W', click: () => command('all-projects') },
  ] };
  if (process.platform !== 'darwin') file.submenu.push({ type: 'separator' }, { label: 'Exit', click: requestQuit });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    ...(process.platform === 'darwin' ? [{ label: 'OpenT1D', submenu: [{ role: 'about' }, { type: 'separator' }, { role: 'hide' }, { role: 'hideOthers' }, { role: 'unhide' }, { type: 'separator' }, { label: 'Quit OpenT1D', accelerator: 'Cmd+Q', click: requestQuit }] }] : []),
    file,
    { label: 'Edit', submenu: [{ role: 'undo' }, { role: 'redo' }, { type: 'separator' }, { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' }] },
    { label: 'View', submenu: [{ label: 'Project Explorer', click: () => command('toggle-explorer') }, { type: 'separator' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { type: 'separator' }, { role: 'togglefullscreen' }] },
  ]));
}

ipcMain.handle('desktop:open-project', async event => {
  if (!trusted(event)) throw new Error('Unknown application frame.');
  const result = await dialog.showOpenDialog(window, { title: 'Open OpenT1D project', properties: ['openDirectory'] });
  return result.canceled ? null : result.filePaths[0];
});
ipcMain.handle('desktop:confirm-editor', async event => {
  if (!trusted(event)) throw new Error('Unknown application frame.');
  const { response } = await dialog.showMessageBox(window, { type: 'question', title: 'Input changes', message: 'Save the input changes before leaving this editor?', buttons: ['Save changes', 'Discard changes', 'Cancel'], defaultId: 0, cancelId: 2 });
  return ['save', 'discard', 'cancel'][response] || 'cancel';
});
ipcMain.on('desktop:view', (event, view) => { if (trusted(event)) setView(view); });
ipcMain.on('desktop:quit', event => { if (trusted(event)) requestQuit(); });
ipcMain.on('desktop:close-answer', (event, answer) => {
  if (trusted(event) && pendingClose && answer?.id === pendingClose.id && typeof answer.canClose === 'boolean') pendingClose.resolve(answer);
});

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.show(); window.focus(); } });
  app.on('activate', () => { if (window) { if (window.isMinimized()) window.restore(); window.show(); } });
  app.on('before-quit', event => { if (!finalQuit) { event.preventDefault(); requestQuit(); } });
  app.whenReady().then(async () => {
    try {
      ready = await startBackend();
      if (finalQuit) return;
      app.setAboutPanelOptions({ applicationName: 'OpenT1D', applicationVersion: 'Concept v1 (internal)', copyright: 'OpenT1D contributors' });
      window = new BrowserWindow({
        title: 'OpenT1D', width: 920, height: 420, minWidth: 760, minHeight: 420,
        useContentSize: true, show: false, backgroundColor: '#111214',
        icon: path.join(process.resourcesPath, 'opent1d.png'),
        titleBarStyle: 'hiddenInset', trafficLightPosition: { x: 14, y: 16 },
        webPreferences: { preload: path.join(__dirname, 'preload.cjs'), nodeIntegration: false, contextIsolation: true, sandbox: true, webSecurity: true, navigateOnDragDrop: false, devTools: !app.isPackaged },
      });
      const session = window.webContents.session;
      session.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
      session.setPermissionCheckHandler(() => false);
      session.webRequest.onBeforeRequest((details, callback) => callback({ cancel: !details.url.startsWith(ready.origin + '/') }));
      window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
      window.webContents.on('will-navigate', (event, url) => { if (!workspaceURL(url)) event.preventDefault(); });
      window.webContents.on('will-attach-webview', event => event.preventDefault());
      window.webContents.on('render-process-gone', async () => {
        rendererDead = true;
        pendingClose?.resolve({ canClose: true });
        if (quitting || finalQuit) return;
        const { response } = await dialog.showMessageBox(window, { type: 'error', title: 'OpenT1D workspace', message: 'The workspace view stopped. Reload to recover the open workspace, or quit with your saved work.', buttons: ['Reload workspace', 'Quit'], defaultId: 0, cancelId: 1 });
        if (quitting || finalQuit || window.isDestroyed()) return;
        if (response === 0) {
          try { await window.loadURL(ready.origin + '/workbench'); rendererDead = false; }
          catch { requestQuit(); }
        } else requestQuit();
      });
      window.on('close', event => { if (!finalQuit) { event.preventDefault(); requestQuit(); } });
      backendExit.then(() => { if (!quitting && !finalQuit) { dialog.showErrorBox('OpenT1D stopped', 'The local service stopped. Your saved projects remain in the workspace.'); finalQuit = true; window?.destroy(); app.quit(); } });
      installMenu();
      window.once('ready-to-show', () => window.show());
      await window.loadURL(ready.origin + '/workbench');
    } catch (error) {
      if (backend?.stdin.writable) backend.stdin.end();
      dialog.showErrorBox('OpenT1D could not start', error.message);
      finalQuit = true; app.exit(1);
    }
  });
}
