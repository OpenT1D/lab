'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('openT1DDesktop', Object.freeze({
  platform: process.platform,
  openProject: () => ipcRenderer.invoke('desktop:open-project'),
  confirmEditor: () => ipcRenderer.invoke('desktop:confirm-editor'),
  setView: view => ipcRenderer.send('desktop:view', view),
  quit: () => ipcRenderer.send('desktop:quit'),
  onCommand: callback => {
    const listener = (_event, command) => callback(command);
    ipcRenderer.on('desktop:command', listener);
    return () => ipcRenderer.removeListener('desktop:command', listener);
  },
  onPrepareClose: callback => {
    const listener = async (_event, { id, mode }) => {
      try {
        const answer = await callback(mode);
        ipcRenderer.send('desktop:close-answer', {
          id, canClose: answer?.canClose === true, busy: answer?.busy === true,
          message: String(answer?.message || '').slice(0, 1000),
        });
      } catch {
        ipcRenderer.send('desktop:close-answer', { id, canClose: false, message: 'The current study could not be saved.' });
      }
    };
    ipcRenderer.on('desktop:prepare-close', listener);
    return () => ipcRenderer.removeListener('desktop:prepare-close', listener);
  },
}));
