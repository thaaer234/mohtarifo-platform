const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('mohtarifoSecurity', {
    onShowBlock: (callback) => ipcRenderer.on('show-security-block', callback),
    onHideBlock: (callback) => ipcRenderer.on('hide-security-block', callback)
});

// حقن سكريبت الحماية فور تحميل الصفحة
window.addEventListener('DOMContentLoaded', () => {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/js/all.min.js';
    document.head.appendChild(script);
});
