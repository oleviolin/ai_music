const express = require('express');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');
const app = express();
const PORT = 3000;

app.use(express.json());

// --- PATHS ---
const PLAYER_DIR = __dirname;
const PUBLIC_DIR = path.join(PLAYER_DIR, 'public');
const MIDI_DIR = path.join(PLAYER_DIR, '../mid/cleaned');
const MP3_DIR = path.join(PLAYER_DIR, '../mp3');
const SETUP_DIR = path.join(PLAYER_DIR, '../setup');

app.use(express.static(PUBLIC_DIR));
app.use('/setup', express.static(SETUP_DIR));

// --- ROUTES ---

app.get('/', (req, res) => {
    if (fs.existsSync(path.join(PUBLIC_DIR, 'index.html'))) 
        res.sendFile(path.join(PUBLIC_DIR, 'index.html'));
    else res.status(404).send("index.html missing");
});

// --- SETTINGS (NEW) ---
const SETTINGS_FILE = path.join(SETUP_DIR, 'user_settings.json');

app.get('/api/settings', (req, res) => {
    if (fs.existsSync(SETTINGS_FILE)) res.sendFile(SETTINGS_FILE);
    else res.json({}); // Default empty
});

app.post('/api/settings', (req, res) => {
    // Saves whatever JSON body is sent (e.g. { alignMode: 'dtw' })
    fs.writeFileSync(SETTINGS_FILE, JSON.stringify(req.body, null, 2));
    res.json({ success: true });
});

// --- ALIGNMENT DATA ---
app.get('/api/alignment/manual/:category', (req, res) => {
    const p = path.join(SETUP_DIR, `alignment_manual_${req.params.category}.json`);
    if (fs.existsSync(p)) res.sendFile(p); else res.json({});
});

app.get('/api/alignment/dtw/:category', (req, res) => {
    const p = path.join(SETUP_DIR, `alignment_dtw_${req.params.category}.json`);
    if (fs.existsSync(p)) res.sendFile(p); else res.json({});
});

// --- SAVE MANUAL ---
app.post('/api/save_alignment', (req, res) => {
    const { category, key, offset, speed } = req.body;
    const p = path.join(SETUP_DIR, `alignment_manual_${category}.json`);
    let data = {};
    if (fs.existsSync(p)) {
        try { data = JSON.parse(fs.readFileSync(p, 'utf8')); } catch(e){}
    }
    data[key] = { offset, speed, timestamp: new Date().toISOString() };
    fs.writeFileSync(p, JSON.stringify(data, null, 2));
    console.log(`Saved ${key} (${Object.keys(data).length} total)`);
    res.json({ success: true });
});

// --- RE-ANALYZE ---
app.post('/api/reanalyze', (req, res) => {
    const { category, key } = req.body;
    const script = path.join(PLAYER_DIR, '../source/04_analyze_data.py');
    const python = path.join(PLAYER_DIR, '../venv/bin/python'); // Check this path!
    
    exec(`${python} "${script}" ${category} "${key}"`, (err, stdout, stderr) => {
        if(err) return res.status(500).json({error: stderr});
        console.log(stdout);
        res.json({success: true});
    });
});

// --- FILES ---
app.get('/api/melodies/:category', (req, res) => {
    const dir = path.join(MP3_DIR, req.params.category, 'wav');
    if (!fs.existsSync(dir)) return res.json([]);
    fs.readdir(dir, (err, files) => {
        if(err) return res.status(500).send('Error');
        res.json(files.filter(f=>f.endsWith('.wav')).map(f=>f.slice(0,-4)));
    });
});

app.get('/api/analysis/:category/:key', (req, res) => {
    const p = path.join(MP3_DIR, req.params.category, 'wav', `${req.params.key}.json`);
    if(fs.existsSync(p)) res.sendFile(p); else res.status(404).send('Not found');
});

app.use('/midi', express.static(MIDI_DIR));
app.use('/audio', express.static(MP3_DIR));
// ... existing code ...

// --- DEBUG / EXPERIMENTAL ROUTES ---
const DEBUG_DIR = path.join(SETUP_DIR, 'debug');

// 1. List all experimental files
app.get('/api/debug/list', (req, res) => {
    if (!fs.existsSync(DEBUG_DIR)) return res.json([]);
    
    fs.readdir(DEBUG_DIR, (err, files) => {
        if (err) return res.json([]);
        
        // Filter .json and parse "Category.Key.json"
        const debugFiles = files
            .filter(f => f.endsWith('.json'))
            .map(f => {
                const parts = f.replace('.json', '').split('.');
                if(parts.length < 2) return null;
                const category = parts[0];
                const key = parts.slice(1).join('.'); // Join back if key had dots
                return { 
                    filename: f, 
                    display: `${key} (${category})`, 
                    category: category, 
                    key: key 
                };
            })
            .filter(x => x !== null);
            
        res.json(debugFiles);
    });
});

// 2. Load a specific debug alignment
app.get('/api/debug/alignment/:filename', (req, res) => {
    const p = path.join(DEBUG_DIR, req.params.filename);
    if(fs.existsSync(p)) res.sendFile(p); else res.json({});
});

// ... existing app.listen ...

app.listen(PORT, () => console.log(`http://localhost:${PORT}`));