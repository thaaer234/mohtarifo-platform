const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, Browsers, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const express = require('express');
const QRCode = require('qrcode');
const qrcodeTerminal = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');
const pino = require('pino');

// Initialize configurations
const PORT = process.env.PORT || 3001;
const AUTH_PATH = path.join(__dirname, 'auth_info');
const API_SECRET = process.env.WHATSAPP_API_SECRET || 'mohtarifo_internal_secret_123';

let sock = null;
let connectionStatus = 'disconnected';
let latestQRData = null;

// Setup Logger
const logger = pino({ level: 'info' });

// Create Express App
const app = express();
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_PATH);

    // Fetch the latest WhatsApp Web version to prevent Noise handshake and Connection Failure errors
    let version = [2, 3000, 1033893291]; // Modern secure fallback version
    try {
        const latest = await fetchLatestBaileysVersion();
        if (latest && latest.version) {
            version = latest.version;
            console.log(`🚀 Successfully fetched latest WhatsApp Web version: ${version.join('.')}`);
        }
    } catch (e) {
        console.error('⚠️ Failed to dynamically fetch WA version, using secure fallback:', e);
    }

    sock = makeWASocket({
        version,
        auth: state,
        printQRInTerminal: false, 
        logger: logger, 
        browser: Browsers.ubuntu('Chrome'),
        markOnline: false,
        markOnlineOnConnect: false
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('New QR Code event');
            // Save base64 representation for Django frontend
            try {
                latestQRData = await QRCode.toDataURL(qr);
            } catch(e) { logger.error(e); }
        }

        if (connection === 'close') {
            connectionStatus = 'disconnected';
            const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
            
            if (shouldReconnect) {
                setTimeout(connectToWhatsApp, 5000);
            } else {
                // Completely logged out, clear local store
                console.log('Logged out remotely, cleaning auth data');
                latestQRData = null;
                try {
                   fs.rmSync(AUTH_PATH, { recursive: true, force: true });
                } catch(e){}
                setTimeout(connectToWhatsApp, 3000);
            }
        } else if (connection === 'open') {
            connectionStatus = 'connected';
            latestQRData = null; // Safe cleanup
            console.log('CONNECTED');
            
            // Set presence to unavailable after a 3-second delay to ensure authentication is finalized
            setTimeout(async () => {
                try {
                    if (sock) {
                        await sock.sendPresenceUpdate('unavailable');
                        console.log('Initial presence set to unavailable.');
                    }
                } catch (e) {
                    console.error('Failed to set initial presence:', e);
                }
            }, 3000);
        }
    });

    // Start a background heartbeat to keep sending "unavailable" state every 60 seconds.
    // This overrides WhatsApp's automatic presence tracking and guarantees push notifications on the phone.
    setInterval(async () => {
        try {
            if (connectionStatus === 'connected' && sock) {
                await sock.sendPresenceUpdate('unavailable');
            }
        } catch(e) {
            // Quietly catch temporary network drop errors
        }
    }, 60000);
}

// ---------------- Middleware & Routes ----------------

app.use((req, res, next) => {
    const token = req.headers['x-api-secret'];
    if (token !== API_SECRET) {
        return res.status(403).json({ status: 'error', message: 'Forbidden' });
    }
    next();
});

app.get('/status', (req, res) => {
    res.json({ 
        status: connectionStatus,
        hasQr: !!latestQRData,
        qr: latestQRData,
        user: (connectionStatus === 'connected' && sock?.user) ? {
            id: sock.user.id,
            name: sock.user.name,
            phone: sock.user.id.split(':')[0]
        } : null
    });
});

app.post('/logout', async (req, res) => {
    try {
        if (sock) {
            await sock.logout();
        }
        res.json({ status: 'success', message: 'Logged out' });
    } catch (e) {
        res.json({ status: 'error', message: e.message });
    }
});

// The logic function to sanitize the number
function formatNumber(number) {
    let formatted = number.toString().replace(/\D/g, '');
    if (!formatted.endsWith('@s.whatsapp.net')) {
        formatted += '@s.whatsapp.net';
    }
    return formatted;
}

app.post('/send-message', async (req, res) => {
    const { number, message, image, document, mimetype, fileName } = req.body;

    if (connectionStatus !== 'connected' || !sock) {
        return res.status(503).json({ status: 'error', message: 'WhatsApp not connected' });
    }

    if (!number || (!message && !document)) {
        return res.status(400).json({ status: 'error', message: 'Missing phone number or message/document content' });
    }

    try {
        const jid = formatNumber(number);
        let sentMsg;

        if (image) {
            let buffer;
            if (image.startsWith('data:')) {
                // Base64 data URL
                const base64Data = image.split(',')[1];
                buffer = Buffer.from(base64Data, 'base64');
            } else {
                // Regular URL or path
                buffer = { url: image };
            }

            sentMsg = await sock.sendMessage(jid, {
                image: buffer,
                caption: message || ''
            });
        } else if (document) {
            let buffer;
            if (document.startsWith('data:')) {
                const base64Data = document.split(',')[1];
                buffer = Buffer.from(base64Data, 'base64');
            } else {
                buffer = Buffer.from(document, 'base64');
            }

            sentMsg = await sock.sendMessage(jid, {
                document: buffer,
                mimetype: mimetype || 'application/octet-stream',
                fileName: fileName || 'file.vcf',
                caption: message || ''
            });
        } else {
            // Send simple text message
            sentMsg = await sock.sendMessage(jid, { text: message });
        }
        
        res.json({ 
            status: 'success', 
            messageId: sentMsg.key.id 
        });
    } catch (error) {
        console.error('Error sending message:', error);
        res.status(500).json({ status: 'error', message: error.message });
    }
});

// Start Everything
app.listen(PORT, () => {
    console.log(`🚀 WhatsApp Gateway Server running on port ${PORT}`);
    connectToWhatsApp();
});
