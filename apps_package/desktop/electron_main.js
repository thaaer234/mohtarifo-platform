const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');
const fs = require('fs');

const PLATFORM_URL = "https://pro-academy.pro/";

let mainWindow;

function createWindow() {
    Menu.setApplicationMenu(null); // إخفاء القوائم الافتراضية

    mainWindow = new BrowserWindow({
        width: 1366,
        height: 850,
        minWidth: 1024,
        minHeight: 700,
        title: "منصة محترفو التعليم - Pro Academy",
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            devTools: false
        },
        backgroundColor: '#080808',
        show: false
    });

    // 🔒 1. تفعيل حظر تصوير وتسجيل الشاشة الأصلي لنظامي ويندوز وماك
    mainWindow.setContentProtection(true);

    // 2. تحميل رابط المنصة الرسمي
    mainWindow.loadURL(PLATFORM_URL);

    // 3. حقن كود الحظر التلقائي للويب فيو فور اكتمال التحميل
    const guardScriptPath = path.join(__dirname, '../web_security_layer/anti_capture_guard.js');
    if (fs.existsSync(guardScriptPath)) {
        const guardCode = fs.readFileSync(guardScriptPath, 'utf8');
        mainWindow.webContents.on('did-finish-load', () => {
            mainWindow.webContents.executeJavaScript(guardCode);
        });
    }

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // عند فقدان التركيز (أدوات التسجيل والتقاط الشاشة)
    mainWindow.on('blur', () => {
        mainWindow.webContents.executeJavaScript(`
            if (typeof showSecurityWarning === 'function') {
                showSecurityWarning();
            } else {
                const ov = document.getElementById('mohtarifo-anti-capture-overlay');
                if (ov) ov.style.display = 'flex';
            }
        `).catch(() => {});
    });

    mainWindow.on('focus', () => {
        mainWindow.webContents.executeJavaScript(`
            const ov = document.getElementById('mohtarifo-anti-capture-overlay');
            if (ov) ov.style.display = 'none';
        `).catch(() => {});
    });
}

const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.focus();
        }
    });

    app.whenReady().then(createWindow);
}

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});
