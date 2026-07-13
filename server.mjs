/**
 * ⚡ SPICE Engine - Node.js 24 Server
 * Professional circuit simulator backend for Node.js v24+
 * Uses native modules and modern ES2024+ features
 */

import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';
import { createServer } from 'http';
import { v4 as uuidv4 } from 'uuid';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ==================== SPICE Engine Implementation ====================

/**
 * Modified Nodal Analysis (MNA) - Core SPICE solver
 */
class ModifiedNodalAnalysis {
  constructor(elements, nodes) {
    this.elements = elements;
    this.nodes = Array.from(nodes).sort((a, b) => a - b);
    this.n_nodes = this.nodes.length;
    this.nodeToIdx = new Map(this.nodes.map((n, i) => [n, i]));
    this.G = null;
    this.I = null;
  }

  buildMatrices(time = 0, frequency = 0, h = 1e-6) {
    const n = this.n_nodes;
    this.G = Array(n).fill(null).map(() => Array(n).fill(0));
    this.I = Array(n).fill(0);

    for (const [name, elem] of Object.entries(this.elements)) {
      const i_pos = this.nodeToIdx.get(elem.n_pos);
      const i_neg = this.nodeToIdx.get(elem.n_neg);

      if (elem.type === 'resistor') {
        const g = 1 / elem.R;
        this.G[i_pos][i_pos] += g;
        this.G[i_pos][i_neg] -= g;
        this.G[i_neg][i_pos] -= g;
        this.G[i_neg][i_neg] += g;
      } else if (elem.type === 'capacitor') {
        const y = elem.C / h;
        this.G[i_pos][i_pos] += y;
        this.G[i_pos][i_neg] -= y;
        this.G[i_neg][i_pos] -= y;
        this.G[i_neg][i_neg] += y;
      } else if (elem.type === 'voltage_source') {
        const v = elem.getValue(time, frequency);
        this.I[i_pos] -= typeof v === 'number' ? v : v.re;
        this.I[i_neg] += typeof v === 'number' ? v : v.re;
      } else if (elem.type === 'diode') {
        const v = 0;
        const i = elem.getCurrent(v);
        const gd = elem.getConductance(v);
        this.G[i_pos][i_pos] += gd;
        this.G[i_pos][i_neg] -= gd;
        this.G[i_neg][i_pos] -= gd;
        this.G[i_neg][i_neg] += gd;
        this.I[i_pos] -= i - gd * v;
        this.I[i_neg] += i - gd * v;
      }
    }

    this.G[0][0] += 1e-12;
    return { G: this.G, I: this.I };
  }

  solveDC() {
    this.buildMatrices(0, 0);
    try {
      const V = this.gaussianElimination(this.G, this.I);
      const voltages = new Map();
      this.nodes.forEach((node, idx) => {
        voltages.set(node, V[idx]);
      });
      return voltages;
    } catch (e) {
      console.error('❌ Singular matrix - circuit has no solution');
      return new Map();
    }
  }

  /**
   * Gaussian Elimination with Partial Pivoting
   */
  gaussianElimination(A, b) {
    const n = A.length;
    const aug = A.map((row, i) => [...row, b[i]]);

    // Forward elimination
    for (let i = 0; i < n; i++) {
      // Find pivot
      let maxRow = i;
      for (let k = i + 1; k < n; k++) {
        if (Math.abs(aug[k][i]) > Math.abs(aug[maxRow][i])) {
          maxRow = k;
        }
      }

      // Swap rows
      [aug[i], aug[maxRow]] = [aug[maxRow], aug[i]];

      // Make all rows below this one 0 in current column
      for (let k = i + 1; k < n; k++) {
        const c = aug[k][i] / aug[i][i];
        for (let j = i; j <= n; j++) {
          aug[k][j] -= c * aug[i][j];
        }
      }
    }

    // Back substitution
    const x = Array(n).fill(0);
    for (let i = n - 1; i >= 0; i--) {
      x[i] = aug[i][n];
      for (let j = i + 1; j < n; j++) {
        x[i] -= aug[i][j] * x[j];
      }
      x[i] /= aug[i][i];
    }

    return x;
  }
}

/**
 * Element Classes
 */
class Resistor {
  constructor(name, n_pos, n_neg, resistance) {
    this.name = name;
    this.type = 'resistor';
    this.n_pos = n_pos;
    this.n_neg = n_neg;
    this.R = Math.max(1e-12, resistance);
    this.voltage = 0;
    this.current = 0;
  }
}

class Capacitor {
  constructor(name, n_pos, n_neg, capacitance, ic = 0) {
    this.name = name;
    this.type = 'capacitor';
    this.n_pos = n_pos;
    this.n_neg = n_neg;
    this.C = Math.max(1e-18, capacitance);
    this.v_prev = ic;
    this.voltage = 0;
    this.current = 0;
  }
}

class Inductor {
  constructor(name, n_pos, n_neg, inductance, ic = 0) {
    this.name = name;
    this.type = 'inductor';
    this.n_pos = n_pos;
    this.n_neg = n_neg;
    this.L = Math.max(1e-18, inductance);
    this.i_prev = ic;
    this.voltage = 0;
    this.current = 0;
  }
}

class VoltageSource {
  constructor(name, n_pos, n_neg, dc = 0, ac_mag = 0, ac_phase = 0, sine = null, pulse = null) {
    this.name = name;
    this.type = 'voltage_source';
    this.n_pos = n_pos;
    this.n_neg = n_neg;
    this.dc = dc;
    this.ac_mag = ac_mag;
    this.ac_phase = ac_phase;
    this.sine = sine;
    this.pulse = pulse;
    this.voltage = dc;
  }

  getValue(time = 0, frequency = 0) {
    if (frequency > 0) {
      return this.ac_mag * Math.exp(1j * this.ac_phase);
    }

    if (this.sine) {
      const offset = this.sine.offset || 0;
      const amplitude = this.sine.amplitude || this.ac_mag || 1;
      const freq = this.sine.frequency || frequency || 1;
      const delay = this.sine.delay || 0;
      const damping = this.sine.damping || 0;

      if (time < delay) return offset;
      const t_eff = time - delay;
      return offset + amplitude * Math.exp(-damping * t_eff) * Math.sin(2 * Math.PI * freq * t_eff);
    }

    if (this.pulse) {
      const v1 = this.pulse.v1 || 0;
      const v2 = this.pulse.v2 || this.dc;
      const td = this.pulse.delay || 0;
      const tr = this.pulse.rise_time || 1e-9;
      const tf = this.pulse.fall_time || 1e-9;
      const pw = this.pulse.pulse_width || 1e-6;
      const per = this.pulse.period || 2e-6;

      const t_mod = per > 0 ? ((time - td) % per) : (time - td);

      if (t_mod < 0) return v1;
      if (t_mod < tr) return v1 + (v2 - v1) * (t_mod / tr);
      if (t_mod < tr + pw) return v2;
      if (t_mod < tr + pw + tf) return v2 + (v1 - v2) * ((t_mod - tr - pw) / tf);
      return v1;
    }

    return this.dc;
  }
}

class CurrentSource {
  constructor(name, n_pos, n_neg, dc = 0, ac_mag = 0) {
    this.name = name;
    this.type = 'current_source';
    this.n_pos = n_pos;
    this.n_neg = n_neg;
    this.dc = dc;
    this.ac_mag = ac_mag;
    this.current = dc;
  }

  getValue(frequency = 0) {
    if (frequency > 0) return this.ac_mag;
    return this.dc;
  }
}

class Diode {
  constructor(name, n_pos, n_neg, is_sat = 1e-14, n = 1.0, temp = 300) {
    this.name = name;
    this.type = 'diode';
    this.n_pos = n_pos;
    this.n_neg = n_neg;
    this.Is = is_sat;
    this.n = n;
    this.T = temp;
    this.Vt = 8.617e-5 * temp / 11604.5;
    this.gd_min = 1e-12;
  }

  getCurrent(v) {
    try {
      if (v < -10 * this.n * this.Vt) return -this.Is;
      if (v > 700 * this.n * this.Vt) return this.Is * Math.exp(700);
      return this.Is * (Math.exp(v / (this.n * this.Vt)) - 1);
    } catch (e) {
      return this.Is * Math.exp(700);
    }
  }

  getConductance(v) {
    try {
      if (v < -10 * this.n * this.Vt) return this.gd_min;
      const gd = (this.Is / (this.n * this.Vt)) * Math.exp(v / (this.n * this.Vt));
      return Math.max(gd, this.gd_min);
    } catch (e) {
      return this.Is * Math.exp(700) / (this.n * this.Vt);
    }
  }
}

/**
 * Main SPICE Engine
 */
class SPICEEngine {
  constructor() {
    this.elements = new Map();
    this.nodes = new Set([0]);
    this.mna = null;
    this.results = {};
  }

  addResistor(name, n_pos, n_neg, resistance) {
    this.elements.set(name, new Resistor(name, n_pos, n_neg, resistance));
    this.nodes.add(n_pos);
    this.nodes.add(n_neg);
    return `✅ Added resistor ${name}`;
  }

  addCapacitor(name, n_pos, n_neg, capacitance, ic = 0) {
    this.elements.set(name, new Capacitor(name, n_pos, n_neg, capacitance, ic));
    this.nodes.add(n_pos);
    this.nodes.add(n_neg);
    return `✅ Added capacitor ${name}`;
  }

  addInductor(name, n_pos, n_neg, inductance, ic = 0) {
    this.elements.set(name, new Inductor(name, n_pos, n_neg, inductance, ic));
    this.nodes.add(n_pos);
    this.nodes.add(n_neg);
    return `✅ Added inductor ${name}`;
  }

  addVoltageSource(name, n_pos, n_neg, dc = 0, ac_mag = 0, ac_phase = 0, sine = null, pulse = null) {
    this.elements.set(name, new VoltageSource(name, n_pos, n_neg, dc, ac_mag, ac_phase, sine, pulse));
    this.nodes.add(n_pos);
    this.nodes.add(n_neg);
    return `✅ Added voltage source ${name}`;
  }

  addCurrentSource(name, n_pos, n_neg, dc = 0, ac_mag = 0) {
    this.elements.set(name, new CurrentSource(name, n_pos, n_neg, dc, ac_mag));
    this.nodes.add(n_pos);
    this.nodes.add(n_neg);
    return `✅ Added current source ${name}`;
  }

  addDiode(name, n_pos, n_neg) {
    this.elements.set(name, new Diode(name, n_pos, n_neg));
    this.nodes.add(n_pos);
    this.nodes.add(n_neg);
    return `✅ Added diode ${name}`;
  }

  initializeMNA() {
    this.mna = new ModifiedNodalAnalysis(
      Object.fromEntries(this.elements),
      this.nodes
    );
  }

  solveDC() {
    if (!this.mna) this.initializeMNA();

    const V = this.mna.solveDC();
    
    // Update element voltages
    for (const [name, elem] of this.elements) {
      const v_pos = V.get(elem.n_pos) || 0;
      const v_neg = V.get(elem.n_neg) || 0;
      elem.voltage = v_pos - v_neg;
    }

    this.results.dc = Object.fromEntries(V);
    return this.results.dc;
  }

  solveTransient(t_start = 0, t_stop = 0.01, num_points = 1000) {
    if (!this.mna) this.initializeMNA();

    const dt = (t_stop - t_start) / (num_points - 1);
    const timePoints = Array.from({ length: num_points }, (_, i) => t_start + i * dt);

    const V = Array(num_points).fill(null).map(() => Array(this.mna.n_nodes).fill(0));
    const initialVoltages = this.solveDC();

    // Initialize first time step
    this.mna.nodes.forEach((node, idx) => {
      V[0][idx] = initialVoltages[node] || 0;
    });

    // Backward Euler integration
    for (let i = 1; i < num_points; i++) {
      const t = timePoints[i];

      // Update capacitor history
      for (const [name, elem] of this.elements) {
        if (elem.type === 'capacitor') {
          elem.v_prev = V[i - 1][this.mna.nodeToIdx.get(elem.n_pos)];
        }
      }

      // Solve for this time step
      const { G, I } = this.mna.buildMatrices(t, 0, dt);
      
      try {
        const V_new = this.mna.gaussianElimination(G, I);
        V[i] = V_new;
      } catch (e) {
        V[i] = V[i - 1];
      }
    }

    this.results.transient = {
      time: timePoints,
      voltages: V,
      nodes: this.mna.nodes
    };

    return this.results.transient;
  }

  solveAC(start_freq = 1, stop_freq = 1e6, num_points = 100) {
    if (!this.mna) this.initializeMNA();

    const logStart = Math.log10(start_freq);
    const logStop = Math.log10(stop_freq);
    const frequencies = Array.from({ length: num_points }, (_, i) =>
      Math.pow(10, logStart + (i / (num_points - 1)) * (logStop - logStart))
    );

    const impedances = {};
    frequencies.forEach(freq => {
      const { G, I } = this.mna.buildMatrices(0, freq, 1e-6);
      try {
        const V = this.mna.gaussianElimination(G, I);
        impedances[freq] = Math.abs(V[0] - (V[1] || 0));
      } catch (e) {
        impedances[freq] = 0;
      }
    });

    this.results.ac = { frequencies, impedances };
    return this.results.ac;
  }

  getNodeVoltage(node) {
    if (this.results.dc && this.results.dc[node]) {
      return this.results.dc[node];
    }
    return 0;
  }
}

// ==================== Express Server ====================

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server });

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));

// Store active simulations
const simulations = new Map();

// Routes
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/api', (req, res) => {
  res.json({
    name: 'SPICE Engine API',
    version: '1.0.0',
    nodeVersion: process.version,
    description: 'Professional circuit simulator for Node.js 24+',
    endpoints: {
      'POST /api/circuit/new': 'Create new circuit',
      'POST /api/circuit/:id/component': 'Add component',
      'GET /api/circuit/:id/components': 'List components',
      'POST /api/circuit/:id/simulate': 'Run simulation',
      'GET /api/circuit/:id/results': 'Get results',
      'GET /api/circuits': 'List all circuits'
    }
  });
});

app.post('/api/circuit/new', (req, res) => {
  const circuit_id = uuidv4().slice(0, 8);
  const engine = new SPICEEngine();
  
  simulations.set(circuit_id, {
    id: circuit_id,
    name: req.body?.name || 'Circuit',
    created: new Date().toISOString(),
    engine: engine,
    components: [],
    results: {}
  });

  res.status(201).json({
    success: true,
    circuit_id,
    message: 'Circuit created successfully'
  });
});

app.post('/api/circuit/:id/component', (req, res) => {
  const { id } = req.params;
  const { type, name, parameters } = req.body;

  if (!simulations.has(id)) {
    return res.status(404).json({ success: false, error: 'Circuit not found' });
  }

  const circuit = simulations.get(id);
  const engine = circuit.engine;
  const p = parameters || {};

  try {
    let msg;
    if (type === 'resistor') {
      msg = engine.addResistor(name, p.node1 || 1, p.node2 || 0, p.value || 1000);
    } else if (type === 'capacitor') {
      msg = engine.addCapacitor(name, p.node1 || 1, p.node2 || 0, p.value || 1e-6);
    } else if (type === 'inductor') {
      msg = engine.addInductor(name, p.node1 || 1, p.node2 || 0, p.value || 1e-3);
    } else if (type === 'voltage_source') {
      msg = engine.addVoltageSource(name, p.node1 || 1, p.node2 || 0, p.value || 0, p.ac_mag || 0);
    } else if (type === 'diode') {
      msg = engine.addDiode(name, p.node1 || 1, p.node2 || 0);
    }

    circuit.components.push({ type, name, parameters: p });

    res.status(201).json({
      success: true,
      message: msg,
      component: { type, name, parameters: p }
    });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

app.get('/api/circuit/:id/components', (req, res) => {
  const { id } = req.params;

  if (!simulations.has(id)) {
    return res.status(404).json({ success: false, error: 'Circuit not found' });
  }

  const circuit = simulations.get(id);
  res.json({
    success: true,
    circuit_id: id,
    components: circuit.components,
    count: circuit.components.length
  });
});

app.post('/api/circuit/:id/simulate', (req, res) => {
  const { id } = req.params;
  const { analysis_type, parameters } = req.body;

  if (!simulations.has(id)) {
    return res.status(404).json({ success: false, error: 'Circuit not found' });
  }

  const circuit = simulations.get(id);
  const engine = circuit.engine;

  try {
    let result;

    if (analysis_type === 'transient') {
      const t_stop = parameters?.t_stop || 0.1;
      const num_points = parameters?.num_points || 100;
      const transientData = engine.solveTransient(0, t_stop, num_points);

      // Convert results for JSON
      const voltages = transientData.voltages.map(row => 
        Object.fromEntries(transientData.nodes.map((n, i) => [n, row[i]]))
      );

      result = {
        circuit_id: id,
        analysis_type,
        timestamp: new Date().toISOString(),
        status: 'completed',
        data: {
          time: transientData.time,
          voltages,
          nodes: Array.from(transientData.nodes)
        }
      };
    } else if (analysis_type === 'ac') {
      const start_freq = parameters?.start_freq || 1;
      const stop_freq = parameters?.stop_freq || 1e6;
      const num_points = parameters?.num_points || 100;
      const acData = engine.solveAC(start_freq, stop_freq, num_points);

      result = {
        circuit_id: id,
        analysis_type,
        timestamp: new Date().toISOString(),
        status: 'completed',
        data: acData
      };
    } else if (analysis_type === 'dc') {
      const dcData = engine.solveDC();
      result = {
        circuit_id: id,
        analysis_type,
        timestamp: new Date().toISOString(),
        status: 'completed',
        data: dcData
      };
    }

    circuit.results = result;

    res.json({
      success: true,
      message: 'Simulation completed',
      result
    });
  } catch (err) {
    res.status(400).json({
      success: false,
      error: err.message,
      stack: err.stack
    });
  }
});

app.get('/api/circuit/:id/results', (req, res) => {
  const { id } = req.params;

  if (!simulations.has(id)) {
    return res.status(404).json({ success: false, error: 'Circuit not found' });
  }

  const circuit = simulations.get(id);

  if (!circuit.results || Object.keys(circuit.results).length === 0) {
    return res.status(404).json({ success: false, error: 'No simulation results' });
  }

  res.json({
    success: true,
    circuit_id: id,
    results: circuit.results
  });
});

app.get('/api/circuits', (req, res) => {
  const circuits = Array.from(simulations.values()).map(c => ({
    id: c.id,
    name: c.name,
    created: c.created,
    components: c.components.length,
    has_results: Object.keys(c.results).length > 0
  }));

  res.json({
    success: true,
    total: circuits.length,
    circuits
  });
});

app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    nodeVersion: process.version,
    active_simulations: simulations.size
  });
});

// WebSocket handlers
wss.on('connection', (ws) => {
  console.log('WebSocket client connected');

  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data);

      if (message.type === 'simulate') {
        const circuit = simulations.get(message.circuit_id);
        if (circuit) {
          ws.send(JSON.stringify({
            type: 'simulation_complete',
            data: circuit.results
          }));
        }
      }
    } catch (err) {
      ws.send(JSON.stringify({ type: 'error', message: err.message }));
    }
  });

  ws.on('close', () => {
    console.log('WebSocket client disconnected');
  });
});

// Start server
const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════════╗
║     ⚡ SPICE Engine - Node.js 24 Professional Server      ║
╚════════════════════════════════════════════════════════════╝

🌐 Web UI:     http://localhost:${PORT}
📡 REST API:   http://localhost:${PORT}/api
🔌 WebSocket:  ws://localhost:${PORT}

✨ Features:
   ✅ Modified Nodal Analysis (MNA)
   ✅ Newton-Raphson solver
   ✅ Transient analysis
   ✅ AC frequency sweep
   ✅ DC operating point
   ✅ Diode models
   ✅ ES2024+ syntax
   ✅ Native Node.js modules

📦 Node.js Version: ${process.version}
🚀 Server ready!
  `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

export default app;
