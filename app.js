/* ==========================================================================
   TrustGraph Web Application Logic
   Interactive state machine, auto-demo controller, Web Audio SFX, logs
   ========================================================================== */

(function () {
  'use strict';

  // State
  let currentStep = 0; // 0 to 7
  let isPlaying = false;
  let timerId = null;
  let soundEnabled = true;
  let rightTab = 'mdt'; // 'mdt' or 'audit'

  // Step config metadata
  const STEPS = [
    {
      id: 0,
      name: 'Awaiting Demo Start',
      navId: null,
      protocolActive: null,
      auditPassedCount: 0,
      scannerText: 'AWAITING CANDIDATES',
      scannerState: 'idle',
      showEvaluatedList: false,
      log: null
    },
    {
      id: 1,
      name: 'Prompt',
      navId: 'step-nav-1',
      protocolActive: 'proto-comm',
      auditPassedCount: 0,
      scannerText: 'AWAITING CANDIDATES',
      scannerState: 'idle',
      showEvaluatedList: false,
      log: {
        tag: 'A2A',
        class: 'log-comm',
        text: 'AGENT_INIT: Shopping Agent with TrustGraph activated...'
      }
    },
    {
      id: 2,
      name: 'Context',
      navId: 'step-nav-2',
      protocolActive: 'proto-ap2',
      auditPassedCount: 1,
      scannerText: 'AWAITING CANDIDATES',
      scannerState: 'idle',
      showEvaluatedList: false,
      log: {
        tag: 'AP2',
        class: 'log-ap2',
        text: 'CONTEXT_LOADED: 30 guests, elegant style, quality priority, $3,500 mandate bound.'
      }
    },
    {
      id: 3,
      name: 'Research',
      navId: 'step-nav-3',
      protocolActive: 'proto-ucp',
      auditPassedCount: 2,
      scannerText: 'SCANNING MERCHANTS...',
      scannerState: 'scanning',
      showEvaluatedList: false,
      log: {
        tag: 'UCP',
        class: 'log-ucp',
        text: 'UCP_RESEARCH: Agent scanning merchant digital twins across 4 candidate categories...'
      }
    },
    {
      id: 4,
      name: 'MDT Score',
      navId: 'step-nav-4',
      protocolActive: 'proto-risk',
      auditPassedCount: 3,
      scannerText: 'EVALUATION COMPLETE',
      scannerState: 'scored',
      showEvaluatedList: true,
      log: {
        tag: 'RISK',
        class: 'log-risk',
        text: 'MDT_EVAL: 4 merchants selected — BrightCap Events (0.93), Golden Tassel (0.89)...'
      }
    },
    {
      id: 5,
      name: 'Payment',
      navId: 'step-nav-5',
      protocolActive: 'proto-payment',
      auditPassedCount: 4,
      scannerText: 'PAYMENT AUDIT VERIFIED',
      scannerState: 'scored',
      showEvaluatedList: true,
      log: {
        tag: 'PAY',
        class: 'log-pay',
        text: 'AUDIT_PASS: 4 payments authorized — BrightCap $1,280.00, Harvest Table $1,050.00...'
      }
    },
    {
      id: 6,
      name: 'Escrow',
      navId: 'step-nav-6',
      protocolActive: 'proto-settlement',
      auditPassedCount: 5,
      scannerText: 'SMART ESCROW BOUND',
      scannerState: 'scored',
      showEvaluatedList: true,
      log: {
        tag: 'SETTLE',
        class: 'log-settle',
        text: 'ESCROW_BIND: 4 smart contracts active with milestone protection & tokenization.'
      }
    },
    {
      id: 7,
      name: 'Delivery',
      navId: 'step-nav-7',
      protocolActive: 'proto-lifecycle',
      auditPassedCount: 6,
      scannerText: 'TRUST LOOP CLOSED',
      scannerState: 'scored',
      showEvaluatedList: true,
      log: {
        tag: 'LIFE',
        class: 'log-life',
        text: 'MDT_RECORD: All deliveries confirmed before 2 PM, ratings fed back to data lake.'
      }
    }
  ];

  // Timing for auto-run per step in ms
  const STEP_DURATIONS = [
    2500, // 0 -> 1
    5500, // 1 -> 2
    5500, // 2 -> 3
    6500, // 3 -> 4
    6500, // 4 -> 5
    6500, // 5 -> 6
    6500, // 6 -> 7
    8000  // 7 -> loop or pause
  ];

  // Web Audio Synthesizer for high-tech UI sounds
  const AudioEngine = {
    ctx: null,
    init() {
      if (!this.ctx) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          this.ctx = new AudioCtx();
        }
      }
      if (this.ctx && this.ctx.state === 'suspended') {
        this.ctx.resume();
      }
    },
    playClick() {
      if (!soundEnabled) return;
      this.init();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(800, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(400, this.ctx.currentTime + 0.05);
      gain.gain.setValueAtTime(0.08, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.05);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.05);
    },
    playStepChime() {
      if (!soundEnabled) return;
      this.init();
      if (!this.ctx) return;
      const notes = [523.25, 659.25, 783.99]; // C5, E5, G5
      notes.forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime + idx * 0.06);
        gain.gain.setValueAtTime(0.05, this.ctx.currentTime + idx * 0.06);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + idx * 0.06 + 0.18);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(this.ctx.currentTime + idx * 0.06);
        osc.stop(this.ctx.currentTime + idx * 0.06 + 0.2);
      });
    },
    playSuccessChime() {
      if (!soundEnabled) return;
      this.init();
      if (!this.ctx) return;
      const notes = [523.25, 659.25, 783.99, 1046.5]; // C5, E5, G5, C6
      notes.forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime + idx * 0.08);
        gain.gain.setValueAtTime(0.07, this.ctx.currentTime + idx * 0.08);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + idx * 0.08 + 0.35);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(this.ctx.currentTime + idx * 0.08);
        osc.stop(this.ctx.currentTime + idx * 0.08 + 0.4);
      });
    }
  };

  // DOM Elements
  const btnPlayPause = document.getElementById('btn-play-pause');
  const btnPrev = document.getElementById('btn-prev');
  const btnNext = document.getElementById('btn-next');
  const btnReset = document.getElementById('btn-reset');
  const btnSound = document.getElementById('btn-sound');
  const playIcon = document.getElementById('play-icon');
  const playText = document.getElementById('play-text');
  const progressFill = document.getElementById('progress-fill');
  const footerStepText = document.getElementById('footer-step-text');
  const logStream = document.getElementById('log-stream');
  const logPlaceholder = document.getElementById('log-placeholder');
  const mdtScannerBox = document.getElementById('mdt-scanner-box');
  const mdtEvaluatedList = document.getElementById('mdt-evaluated-list');
  const scannerStateLabel = document.getElementById('scanner-state-label');
  const scannerStateText = document.getElementById('scanner-state-text');

  // Initialize
  function init() {
    setupEventListeners();
    updateClock();
    setInterval(updateClock, 30000);
    renderStep(0);
  }

  function updateClock() {
    const clockEl = document.getElementById('phone-clock');
    if (clockEl) {
      const now = new Date();
      let hours = now.getHours();
      let mins = now.getMinutes();
      mins = mins < 10 ? '0' + mins : mins;
      clockEl.textContent = `${hours % 12 || 12}:${mins}`;
    }
  }

  function setupEventListeners() {
    // Nav controls
    btnPlayPause.addEventListener('click', togglePlayPause);
    btnPrev.addEventListener('click', () => {
      AudioEngine.playClick();
      pauseDemo();
      goToStep(Math.max(0, currentStep - 1));
    });
    btnNext.addEventListener('click', () => {
      AudioEngine.playClick();
      pauseDemo();
      goToStep(Math.min(7, currentStep + 1));
    });
    btnReset.addEventListener('click', () => {
      AudioEngine.playClick();
      pauseDemo();
      clearLogs();
      goToStep(0);
    });

    btnSound.addEventListener('click', () => {
      soundEnabled = !soundEnabled;
      btnSound.style.opacity = soundEnabled ? '1' : '0.4';
      AudioEngine.playClick();
    });

    // Step navigation pills click
    for (let i = 1; i <= 7; i++) {
      const navPill = document.getElementById(`step-nav-${i}`);
      if (navPill) {
        navPill.addEventListener('click', () => {
          AudioEngine.playClick();
          pauseDemo();
          goToStep(i);
        });
      }
    }

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'Escape') {
        closeAllModals();
      } else if (e.key === ' ') {
        e.preventDefault();
        togglePlayPause();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        pauseDemo();
        goToStep(Math.min(7, currentStep + 1));
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        pauseDemo();
        goToStep(Math.max(0, currentStep - 1));
      } else if (e.key >= '0' && e.key <= '7') {
        pauseDemo();
        goToStep(parseInt(e.key, 10));
      }
    });

    // Close modal when clicking overlay outside content
    document.querySelectorAll('.modal-overlay').forEach((overlay) => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          closeModal(overlay.id);
        }
      });
    });
  }

  function togglePlayPause() {
    AudioEngine.playClick();
    if (isPlaying) {
      pauseDemo();
    } else {
      startDemo();
    }
  }

  function startDemo() {
    isPlaying = true;
    btnPlayPause.classList.add('running');
    playIcon.textContent = '❚❚';
    playText.textContent = 'Pause';

    if (currentStep >= 7) {
      goToStep(0);
    }

    scheduleNextStep();
  }

  function pauseDemo() {
    isPlaying = false;
    btnPlayPause.classList.remove('running');
    playIcon.textContent = '▶';
    playText.textContent = currentStep === 0 ? 'Run Demo' : 'Resume';
    if (timerId) {
      clearTimeout(timerId);
      timerId = null;
    }
  }

  function scheduleNextStep() {
    if (!isPlaying) return;
    const duration = STEP_DURATIONS[currentStep] || 5000;
    timerId = setTimeout(() => {
      if (!isPlaying) return;
      if (currentStep < 7) {
        goToStep(currentStep + 1);
        scheduleNextStep();
      } else {
        pauseDemo();
      }
    }, duration);
  }

  function goToStep(step) {
    if (step < 0 || step > 7) return;
    currentStep = step;
    renderStep(step);
    if (step === 7) {
      AudioEngine.playSuccessChime();
    } else if (step > 0) {
      AudioEngine.playStepChime();
    }
  }

  function renderStep(stepIndex) {
    const config = STEPS[stepIndex];

    // 1. Phone View switching
    for (let i = 0; i <= 7; i++) {
      const viewEl = document.getElementById(`view-step-${i}`);
      if (viewEl) {
        viewEl.classList.toggle('active', i === stepIndex);
      }
    }

    // 2. Top Progress Fill & Step Nav items
    if (progressFill) {
      const pct = stepIndex === 0 ? 0 : Math.round((stepIndex / 7) * 100);
      progressFill.style.width = `${pct}%`;
    }

    for (let i = 1; i <= 7; i++) {
      const navEl = document.getElementById(`step-nav-${i}`);
      if (navEl) {
        navEl.classList.remove('active', 'completed');
        if (i === stepIndex) {
          navEl.classList.add('active');
        } else if (i < stepIndex) {
          navEl.classList.add('completed');
        }
      }
    }

    // 3. Protocol Stack Glow & Active Dot
    const allProtos = [
      'proto-comm', 'proto-identity', 'proto-ap2', 'proto-ucp',
      'proto-risk', 'proto-payment', 'proto-settlement', 'proto-lifecycle'
    ];
    allProtos.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('active');
    });

    const allDots = [
      'dot-comm', 'dot-identity', 'dot-ap2', 'dot-ucp',
      'dot-risk', 'dot-payment', 'dot-settlement', 'dot-lifecycle'
    ];
    allDots.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('active');
    });

    if (config.protocolActive) {
      const activeEl = document.getElementById(config.protocolActive);
      if (activeEl) activeEl.classList.add('active');

      const dotMap = {
        'proto-comm': 'dot-comm',
        'proto-identity': 'dot-identity',
        'proto-ap2': 'dot-ap2',
        'proto-ucp': 'dot-ucp',
        'proto-risk': 'dot-risk',
        'proto-payment': 'dot-payment',
        'proto-settlement': 'dot-settlement',
        'proto-lifecycle': 'dot-lifecycle'
      };
      const dotEl = document.getElementById(dotMap[config.protocolActive]);
      if (dotEl) dotEl.classList.add('active');
    }

    // 4. MDT Engine Scanner vs Scored List
    if (scannerStateText) {
      scannerStateText.textContent = config.scannerText;
    }

    // Active dimensions nodes in step 3
    const allDimNodes = document.querySelectorAll('.dim-node');
    allDimNodes.forEach((node) => {
      if (config.scannerState === 'scanning' || config.scannerState === 'scored') {
        node.classList.add('active');
      } else {
        node.classList.remove('active');
      }
    });

    if (mdtEvaluatedList && mdtScannerBox) {
      if (config.showEvaluatedList) {
        mdtEvaluatedList.classList.remove('hidden');
        mdtScannerBox.style.display = 'none';
      } else {
        mdtEvaluatedList.classList.add('hidden');
        mdtScannerBox.style.display = 'block';
      }
    }

    // Auto-switch tabs to show the most relevant context
    const rightCol = document.querySelector('.right-panel-column');
    if (!rightCol || !rightCol.classList.contains('full-log-mode')) {
      if (stepIndex === 2 || stepIndex === 5) {
        switchRightTab('audit');
      } else if (stepIndex === 3 || stepIndex === 4 || stepIndex === 7) {
        switchRightTab('mdt');
      }
    }

    // 5. Audit Checklist Progress
    for (let i = 1; i <= 6; i++) {
      const auditItem = document.getElementById(`audit-item-${i}`);
      if (auditItem) {
        if (i <= config.auditPassedCount) {
          auditItem.classList.add('passed');
        } else {
          auditItem.classList.remove('passed');
        }
      }
    }

    // 6. Network Log Stream
    if (config.log) {
      appendLog(config.log);
    }

    // 7. Footer Step Indicator
    if (footerStepText) {
      if (stepIndex === 0) {
        footerStepText.textContent = 'Awaiting Demo Start Step 0 / 7';
      } else {
        footerStepText.textContent = `${config.name} Step ${stepIndex} / 7`;
      }
    }
  }

  function appendLog(logInfo) {
    if (!logStream) return;
    if (logPlaceholder) {
      logPlaceholder.style.display = 'none';
    }

    const now = new Date();
    const timeStr = `[${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}]`;

    const line = document.createElement('div');
    line.className = 'log-line';
    line.innerHTML = `<span class="log-time">${timeStr}</span> <span class="${logInfo.class}">${logInfo.tag}</span> <span class="log-text">${logInfo.text}</span>`;

    logStream.appendChild(line);

    // Auto-scroll log console
    const consoleBody = document.getElementById('log-console');
    if (consoleBody) {
      consoleBody.scrollTop = consoleBody.scrollHeight;
    }
  }

  function clearLogs() {
    if (logStream) logStream.innerHTML = '';
    if (logPlaceholder) logPlaceholder.style.display = 'block';
  }

  // Right Tabs Switcher
  window.switchRightTab = function (tabName) {
    rightTab = tabName;
    const tabMdt = document.getElementById('tab-mdt');
    const tabAudit = document.getElementById('tab-audit');
    const tabLog = document.getElementById('tab-log');
    const paneMdt = document.getElementById('pane-mdt');
    const paneAudit = document.getElementById('pane-audit');
    const rightCol = document.querySelector('.right-panel-column');

    if (tabName === 'mdt') {
      if (tabMdt) tabMdt.classList.add('active');
      if (tabAudit) tabAudit.classList.remove('active');
      if (tabLog) tabLog.classList.remove('active');
      if (paneMdt) paneMdt.classList.add('active');
      if (paneAudit) paneAudit.classList.remove('active');
      if (rightCol) rightCol.classList.remove('full-log-mode');
    } else if (tabName === 'audit') {
      if (tabAudit) tabAudit.classList.add('active');
      if (tabMdt) tabMdt.classList.remove('active');
      if (tabLog) tabLog.classList.remove('active');
      if (paneAudit) paneAudit.classList.add('active');
      if (paneMdt) paneMdt.classList.remove('active');
      if (rightCol) rightCol.classList.remove('full-log-mode');
    } else if (tabName === 'log') {
      if (tabLog) tabLog.classList.add('active');
      if (tabMdt) tabMdt.classList.remove('active');
      if (tabAudit) tabAudit.classList.remove('active');
      if (rightCol) rightCol.classList.add('full-log-mode');
    }
  };

  window.toggleLogExpand = function () {
    const rightCol = document.querySelector('.right-panel-column');
    if (rightCol) {
      const isFull = rightCol.classList.toggle('full-log-mode');
      const tabLog = document.getElementById('tab-log');
      const tabMdt = document.getElementById('tab-mdt');
      const tabAudit = document.getElementById('tab-audit');
      if (isFull) {
        if (tabLog) tabLog.classList.add('active');
        if (tabMdt) tabMdt.classList.remove('active');
        if (tabAudit) tabAudit.classList.remove('active');
      } else {
        switchRightTab('mdt');
      }
    }
  };

  // Modal Dialog Handlers
  window.openModal = function (modalId) {
    AudioEngine.playClick();
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
    }
  };

  window.closeModal = function (modalId) {
    AudioEngine.playClick();
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
    }
  };

  window.closeAllModals = function () {
    document.querySelectorAll('.modal-overlay').forEach((modal) => {
      modal.classList.remove('active');
    });
  };

  // Expose global methods for inline clicks if needed
  window.goToStep = goToStep;
  window.startDemo = startDemo;
  window.pauseDemo = pauseDemo;

  // Run on DOM loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
