/**
 * Stock Journey Dashboard - Frontend Application Logic
 * Integrates live MetaTrader 5 APIs with the Figma dashboard interface.
 */

function getTodayDateString(d = new Date()) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const todayDate = new Date();
const todayDateStr = getTodayDateString(todayDate);

// Global State - Default to Today
let activeView = 'overview';
let pickerState = {
  currentYear: todayDate.getFullYear(),
  currentMonth: todayDate.getMonth(), // 0-indexed
  startDate: todayDateStr,
  endDate: todayDateStr,
  selecting: 'start'
};

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initTopActions();
  initDatePicker();
  checkMT5Health();
  refreshAllDashboardData();
});

/**
 * Check Health and MT5 Connection Status
 */
async function checkMT5Health() {
  try {
    const res = await fetch('/api/health');
    if (!res.ok) return;
    const data = await res.json();
    const indicator = document.getElementById('mt5Indicator');
    const statusText = document.getElementById('system-status-text');
    const sampleText = document.getElementById('sampleDataText');

    if (data.mt5_connected) {
      if (indicator) indicator.className = 'status-indicator online';
      if (statusText) statusText.innerText = 'Live MT5 Online';
    } else {
      if (indicator) indicator.className = 'status-indicator';
      if (statusText) statusText.innerText = 'MT5 Offline (Sample)';
    }

    if (sampleText && data.mode) {
      sampleText.innerText = data.mode;
    }
  } catch (e) {
    console.warn('Health check failed:', e);
  }
}

/**
 * Tab Navigation (Overview, Calendar, Analytics, Journal, Settings)
 */
function initNavigation() {
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const view = item.getAttribute('data-view');
      switchView(view);
    });
  });
}

function switchView(viewName) {
  activeView = viewName;

  document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
    if (item.getAttribute('data-view') === viewName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.remove('active');
  });

  const targetSection = document.getElementById(`view-${viewName}`);
  if (targetSection) {
    targetSection.classList.add('active');
  }

  const titleMap = {
    'overview': 'Pairs traded',
    'calendar': 'Calendar',
    'analytics': 'Analytics',
    'journal': 'Journal notes',
    'settings': 'Settings'
  };
  const pageTitleEl = document.getElementById('page-title');
  if (pageTitleEl && titleMap[viewName]) {
    pageTitleEl.innerText = titleMap[viewName];
  }
}

/**
 * Top Actions (Toggle Live MT5 / Sample Mode)
 */
function initTopActions() {
  const sampleBtn = document.getElementById('sampleDataBtn');
  if (sampleBtn) {
    sampleBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/toggle-mode', { method: 'POST' });
        const result = await res.json();
        const btnText = document.getElementById('sampleDataText');
        if (btnText && result.mode) {
          btnText.innerText = result.mode;
        }
        refreshAllDashboardData();
      } catch (err) {
        console.error('Mode toggle failed:', err);
      }
    });
  }
}

/**
 * Refresh Both Top Metrics and Pairs Table from Live API
 */
function refreshAllDashboardData() {
  const start = pickerState.startDate || todayDateStr;
  const end = pickerState.endDate || todayDateStr;
  fetchOverviewMetrics(start, end);
  fetchPairsData(start, end);
}

/**
 * 1. Fetch Top 4 Overview Cards via Single API
 */
async function fetchOverviewMetrics(startDate, endDate) {
  try {
    const url = `/api/overview-metrics?from_date=${encodeURIComponent(startDate)}&to_date=${encodeURIComponent(endDate)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('API response was not ok');
    const data = await res.json();

    const pnlEl = document.getElementById('val-net-pnl');
    const winRateEl = document.getElementById('val-win-rate');
    const pfEl = document.getElementById('val-profit-factor');
    const tradesEl = document.getElementById('val-total-trades');

    // Net PnL formatting & dynamic profit (green) vs loss (red) styling
    if (pnlEl) {
      const pnlCard = pnlEl.closest('.metric-card');
      const isProfit = (typeof data.net_profit === 'number')
        ? (data.net_profit >= 0)
        : !String(data.net_profit_formatted || '').trim().startsWith('-');

      if (data.net_profit_formatted) {
        pnlEl.innerText = data.net_profit_formatted;
      } else {
        const sign = data.net_profit >= 0 ? '+' : '-';
        pnlEl.innerText = `${sign}$${Math.abs(data.net_profit).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 2})}`;
      }

      if (isProfit) {
        if (pnlCard) pnlCard.classList.remove('loss-card');
        pnlEl.classList.remove('text-red');
      } else {
        if (pnlCard) pnlCard.classList.add('loss-card');
        pnlEl.classList.add('text-red');
      }

      pnlEl.classList.add('updated');
      setTimeout(() => pnlEl.classList.remove('updated'), 400);
    }

    // Win Rate
    if (winRateEl) {
      winRateEl.innerText = data.win_rate_formatted || `${data.win_rate}%`;
      winRateEl.classList.add('updated');
      setTimeout(() => winRateEl.classList.remove('updated'), 400);
    }

    // Profit Factor
    if (pfEl) {
      pfEl.innerText = data.profit_factor_formatted || `${data.profit_factor}`;
      pfEl.classList.add('updated');
      setTimeout(() => pfEl.classList.remove('updated'), 400);
    }

    // Total Trades
    if (tradesEl) {
      tradesEl.innerText = data.total_trades_formatted || `${data.total_trades}`;
      tradesEl.classList.add('updated');
      setTimeout(() => tradesEl.classList.remove('updated'), 400);
    }
  } catch (err) {
    console.warn('Overview metrics fetch failed:', err);
  }
}

/**
 * 2. Fetch Pairs Traded Table via Live MT5 API
 */
async function fetchPairsData(startDate, endDate) {
  try {
    const url = `/api/pairs?from_date=${encodeURIComponent(startDate)}&to_date=${encodeURIComponent(endDate)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch pairs data');
    const data = await res.json();

    if (data && data.pairs) {
      renderPairsTable(data.pairs);
    }
  } catch (err) {
    console.warn('Pairs fetch failed:', err);
  }
}

function renderPairsTable(pairs) {
  const tbody = document.getElementById('pairsTableBody');
  if (!tbody) return;

  if (!pairs || pairs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color: var(--text-muted);">No closed trades found for this period.</td></tr>`;
    return;
  }

  let html = '';
  pairs.forEach((p, idx) => {
    const isPositive = p.net_pnl >= 0;
    const pnlClass = isPositive ? 'text-green' : 'text-red';
    const actionClass = (p.action_primary || idx === 0) ? 'link-primary' : 'link-muted';
    const actionText = p.action_text || (idx === 0 ? 'Open calendar &rsaquo;' : 'View &rsaquo;');

    html += `
      <tr>
        <td class="col-pair font-semibold">${p.pair}</td>
        <td class="col-trades">${p.trades}</td>
        <td class="col-winrate">${p.win_rate}%</td>
        <td class="col-pf">${p.profit_factor || 1.9}</td>
        <td class="col-pnl ${pnlClass}">${p.net_pnl_formatted || (isPositive ? '+' : '-') + '$' + Math.abs(p.net_pnl).toLocaleString()}</td>
        <td class="col-action">
          <a href="javascript:void(0)" class="action-link ${actionClass}">
            ${actionText}
          </a>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

/**
 * Interactive Calendar Popover Picker
 */
function initDatePicker() {
  const triggerBtn = document.getElementById('dateFilterBtn');
  const popover = document.getElementById('datePickerPopover');
  const chevron = document.getElementById('chevronIcon');
  const prevBtn = document.getElementById('prevMonthBtn');
  const nextBtn = document.getElementById('nextMonthBtn');
  const startInput = document.getElementById('popoverStartDate');
  const endInput = document.getElementById('popoverEndDate');
  const applyBtn = document.getElementById('applyDatePickerBtn');
  const cancelBtn = document.getElementById('cancelDatePickerBtn');
  const presetBtns = document.querySelectorAll('.preset-btn');

  if (!triggerBtn || !popover) return;

  // Toggle Popover
  triggerBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = popover.classList.contains('open');
    if (isOpen) {
      popover.classList.remove('open');
      if (chevron) chevron.classList.remove('rotate');
    } else {
      popover.classList.add('open');
      if (chevron) chevron.classList.add('rotate');
      renderPickerCalendar();
    }
  });

  // Close when clicking outside
  document.addEventListener('click', (e) => {
    if (!popover.contains(e.target) && !triggerBtn.contains(e.target)) {
      popover.classList.remove('open');
      if (chevron) chevron.classList.remove('rotate');
    }
  });

  // Month Navigation
  if (prevBtn) {
    prevBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      pickerState.currentMonth--;
      if (pickerState.currentMonth < 0) {
        pickerState.currentMonth = 11;
        pickerState.currentYear--;
      }
      renderPickerCalendar();
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      pickerState.currentMonth++;
      if (pickerState.currentMonth > 11) {
        pickerState.currentMonth = 0;
        pickerState.currentYear++;
      }
      renderPickerCalendar();
    });
  }

  // Quick Presets
  presetBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      presetBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const preset = btn.getAttribute('data-preset');
      applyPresetDates(preset);
      renderPickerCalendar();
    });
  });

  // Manual Date Inputs
  if (startInput) {
    startInput.addEventListener('change', () => {
      if (startInput.value) {
        pickerState.startDate = startInput.value;
        updateRangeHint();
        renderPickerCalendar();
      }
    });
  }

  if (endInput) {
    endInput.addEventListener('change', () => {
      if (endInput.value) {
        pickerState.endDate = endInput.value;
        updateRangeHint();
        renderPickerCalendar();
      }
    });
  }

  // Cancel & Apply
  if (cancelBtn) {
    cancelBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      popover.classList.remove('open');
      if (chevron) chevron.classList.remove('rotate');
    });
  }

  if (applyBtn) {
    applyBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      popover.classList.remove('open');
      if (chevron) chevron.classList.remove('rotate');

      // Update date pill label
      const rangeText = document.getElementById('dateRangeText');
      if (rangeText) {
        rangeText.innerText = formatRangeLabel(pickerState.startDate, pickerState.endDate);
      }

      // Fetch live data
      refreshAllDashboardData();
    });
  }

  // Set default inputs and labels to Today
  if (startInput) startInput.value = pickerState.startDate;
  if (endInput) endInput.value = pickerState.endDate;
  updateRangeHint();
  const rangeText = document.getElementById('dateRangeText');
  if (rangeText) {
    rangeText.innerText = formatRangeLabel(pickerState.startDate, pickerState.endDate);
  }

  renderPickerCalendar();
}

function applyPresetDates(preset) {
  const now = new Date();
  const todayStr = getTodayDateString(now);

  if (preset === 'today') {
    pickerState.startDate = todayStr;
    pickerState.endDate = todayStr;
    pickerState.currentYear = now.getFullYear();
    pickerState.currentMonth = now.getMonth();
  } else if (preset === 'thisMonth') {
    pickerState.startDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    pickerState.endDate = todayStr;
    pickerState.currentYear = now.getFullYear();
    pickerState.currentMonth = now.getMonth();
  } else if (preset === 'last30') {
    const d30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    pickerState.startDate = getTodayDateString(d30);
    pickerState.endDate = todayStr;
    pickerState.currentYear = now.getFullYear();
    pickerState.currentMonth = now.getMonth();
  } else if (preset === 'lastMonth') {
    const lastMonthDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
    pickerState.startDate = getTodayDateString(lastMonthDate);
    pickerState.endDate = getTodayDateString(lastMonthEnd);
    pickerState.currentYear = lastMonthDate.getFullYear();
    pickerState.currentMonth = lastMonthDate.getMonth();
  } else if (preset === 'ytd') {
    pickerState.startDate = '2026-01-01';
    pickerState.endDate = '2026-11-23';
    pickerState.currentYear = 2026;
    pickerState.currentMonth = 10;
  } else if (preset === 'all2026') {
    pickerState.startDate = '2026-01-01';
    pickerState.endDate = '2026-12-31';
    pickerState.currentYear = 2026;
    pickerState.currentMonth = 11;
  }

  const startInput = document.getElementById('popoverStartDate');
  const endInput = document.getElementById('popoverEndDate');
  if (startInput) startInput.value = pickerState.startDate;
  if (endInput) endInput.value = pickerState.endDate;
  updateRangeHint();
}

function formatRangeLabel(start, end) {
  const todayStr = getTodayDateString();
  if (start === todayStr && end === todayStr) {
    return 'Today';
  }
  if (start === end) {
    return start;
  }
  if (start === '2026-01-01' && end.startsWith('2026-11')) {
    return 'Jan – Nov 2026';
  }
  return `${start} – ${end}`;
}

function updateRangeHint() {
  const hintEl = document.getElementById('rangeHintText');
  if (hintEl) {
    hintEl.innerText = `Period: ${pickerState.startDate} to ${pickerState.endDate || '...'}`;
  }
}

function renderPickerCalendar() {
  const monthLabel = document.getElementById('calendarCurrentMonth');
  const grid = document.getElementById('popoverCalendarDays');
  if (!monthLabel || !grid) return;

  monthLabel.innerText = `${MONTH_NAMES[pickerState.currentMonth]} ${pickerState.currentYear}`;
  grid.innerHTML = '';

  const firstDay = new Date(pickerState.currentYear, pickerState.currentMonth, 1).getDay();
  const daysInMonth = new Date(pickerState.currentYear, pickerState.currentMonth + 1, 0).getDate();

  for (let i = 0; i < firstDay; i++) {
    const emptyCell = document.createElement('div');
    emptyCell.className = 'popover-day-cell empty';
    grid.appendChild(emptyCell);
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const dayCell = document.createElement('div');
    dayCell.className = 'popover-day-cell';
    dayCell.innerText = day;

    const mStr = String(pickerState.currentMonth + 1).padStart(2, '0');
    const dStr = String(day).padStart(2, '0');
    const dateStr = `${pickerState.currentYear}-${mStr}-${dStr}`;

    if (pickerState.startDate && dateStr === pickerState.startDate) {
      dayCell.classList.add('selected-start');
    }
    if (pickerState.endDate && dateStr === pickerState.endDate) {
      dayCell.classList.add('selected-end');
    }
    if (pickerState.startDate && pickerState.endDate && dateStr > pickerState.startDate && dateStr < pickerState.endDate) {
      dayCell.classList.add('in-range');
    }

    dayCell.addEventListener('click', (e) => {
      e.stopPropagation();
      handleDayCellClick(dateStr);
    });

    grid.appendChild(dayCell);
  }
}

function handleDayCellClick(dateStr) {
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));

  if (pickerState.selecting === 'start' || (pickerState.startDate && pickerState.endDate)) {
    pickerState.startDate = dateStr;
    pickerState.endDate = null;
    pickerState.selecting = 'end';
  } else {
    if (dateStr >= pickerState.startDate) {
      pickerState.endDate = dateStr;
      pickerState.selecting = 'start';
    } else {
      pickerState.startDate = dateStr;
      pickerState.endDate = null;
      pickerState.selecting = 'end';
    }
  }

  const startInput = document.getElementById('popoverStartDate');
  const endInput = document.getElementById('popoverEndDate');
  if (startInput) startInput.value = pickerState.startDate;
  if (endInput) endInput.value = pickerState.endDate || '';

  updateRangeHint();
  renderPickerCalendar();
}
