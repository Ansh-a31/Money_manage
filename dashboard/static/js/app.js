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
let currentPair = null;
let calState = {
  year: todayDate.getFullYear(),
  month: todayDate.getMonth() + 1 // 1-12
};
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
  initCalendarView();
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

  if (viewName === 'calendar') {
    loadPairCalendar(currentPair, calState.year, calState.month);
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
      if (!currentPair && data.pairs.length > 0) {
        currentPair = data.pairs[0].pair;
      }
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
      <tr class="pair-row" data-pair="${p.pair}" style="cursor: pointer;" title="Click to view calendar for ${p.pair}">
        <td class="col-pair font-semibold">${p.pair}</td>
        <td class="col-trades">${p.trades}</td>
        <td class="col-winrate">${p.win_rate}%</td>
        <td class="col-pf">${p.profit_factor || 1.9}</td>
        <td class="col-pnl ${pnlClass}">${p.net_pnl_formatted || (isPositive ? '+' : '-') + '$' + Math.abs(p.net_pnl).toLocaleString()}</td>
        <td class="col-action">
          <a href="javascript:void(0)" class="action-link ${actionClass}" data-pair="${p.pair}">
            ${actionText}
          </a>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;

  // Add click listeners to rows and buttons to open pair calendar
  tbody.querySelectorAll('.pair-row').forEach(row => {
    row.addEventListener('click', (e) => {
      const pair = row.getAttribute('data-pair');
      if (pair) openPairCalendar(pair);
    });
  });
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
      if (activeView === 'calendar') {
        loadPairCalendar(currentPair, calState.year, calState.month, pickerState.startDate, pickerState.endDate);
      }
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

/**
 * ============================================================================
 * Pair Deep Dive Calendar Logic (Matches Figma)
 * ============================================================================
 */
function initCalendarView() {
  const backBtn = document.getElementById('calendarBackBtn');
  if (backBtn) {
    backBtn.addEventListener('click', (e) => {
      e.preventDefault();
      switchView('overview');
    });
  }

  const prevBtn = document.getElementById('calPrevMonthBtn');
  if (prevBtn) {
    prevBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      calState.month--;
      if (calState.month < 1) {
        calState.month = 12;
        calState.year--;
      }
      loadPairCalendar(currentPair, calState.year, calState.month);
    });
  }

  const nextBtn = document.getElementById('calNextMonthBtn');
  if (nextBtn) {
    nextBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      calState.month++;
      if (calState.month > 12) {
        calState.month = 1;
        calState.year++;
      }
      loadPairCalendar(currentPair, calState.year, calState.month);
    });
  }

  // Clicking on month button toggles the date picker for custom range selection
  const monthPickerBtn = document.getElementById('calMonthPickerBtn');
  if (monthPickerBtn) {
    monthPickerBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const popover = document.getElementById('datePickerPopover');
      const chevron = document.getElementById('chevronIcon');
      if (popover) {
        const isOpen = popover.classList.contains('open');
        if (isOpen) {
          popover.classList.remove('open');
          if (chevron) chevron.classList.remove('rotate');
        } else {
          popover.classList.add('open');
          if (chevron) chevron.classList.add('rotate');
          renderPickerCalendar();
        }
      }
    });
  }
}

function openPairCalendar(pairName) {
  if (pairName) currentPair = pairName;
  const now = new Date();
  calState.year = now.getFullYear();
  calState.month = now.getMonth() + 1; // Default to current month as requested
  switchView('calendar');
  loadPairCalendar(currentPair, calState.year, calState.month);
}

async function loadPairCalendar(symbol, year, month, fromDate = null, toDate = null) {
  try {
    let url = `/api/pair-calendar?year=${year}&month=${month}`;
    if (symbol) {
      url += `&symbol=${encodeURIComponent(symbol)}`;
    }
    if (fromDate && toDate) {
      url += `&from_date=${encodeURIComponent(fromDate)}&to_date=${encodeURIComponent(toDate)}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to load pair calendar data');
    const data = await res.json();
    if (data && data.symbol) {
      currentPair = data.symbol;
    }
    renderPairCalendar(data);
  } catch (err) {
    console.warn('Pair calendar load error:', err);
  }
}

function renderPairCalendar(data) {
  if (!data) return;

  // 1. Breadcrumb and Main Title
  const breadcrumbPair = document.getElementById('calendarBreadcrumbPair');
  if (breadcrumbPair) breadcrumbPair.innerText = data.symbol;

  const mainTitle = document.getElementById('calendarMainTitle');
  if (mainTitle) {
    mainTitle.innerHTML = `${data.symbol} &middot; ${data.month_name} ${data.year}`;
  }

  // 2. Month Nav Buttons
  const prevM = data.month === 1 ? 12 : data.month - 1;
  const prevMonthName = MONTH_NAMES[prevM - 1].slice(0, 3);
  const prevBtn = document.getElementById('calPrevMonthBtn');
  if (prevBtn) prevBtn.innerHTML = `&lsaquo; ${prevMonthName}`;

  const currentLabel = document.getElementById('calCurrentMonthLabel');
  if (currentLabel) {
    currentLabel.innerText = `${data.month_name.slice(0, 3)} ${data.year}`;
  }

  const nextM = data.month === 12 ? 1 : data.month + 1;
  const nextMonthName = MONTH_NAMES[nextM - 1].slice(0, 3);
  const nextBtn = document.getElementById('calNextMonthBtn');
  if (nextBtn) nextBtn.innerHTML = `${nextMonthName} &rsaquo;`;

  // 3. Render Month Calendar Grid
  const grid = document.getElementById('calendarDaysGrid');
  if (grid) {
    grid.innerHTML = '';

    // Empty offset slots for Sunday-start grid
    const offset = (typeof data.first_day_offset === 'number') ? data.first_day_offset : 0;
    for (let i = 0; i < offset; i++) {
      const emptySlot = document.createElement('div');
      emptySlot.className = 'cal-day-cell empty-slot';
      grid.appendChild(emptySlot);
    }

    // Days 1 through total_days_in_month
    const totalDays = data.total_days_in_month || 30;
    const daysMap = data.days || {};

    for (let day = 1; day <= totalDays; day++) {
      const dayCell = document.createElement('div');
      const dayInfo = daysMap[day] || daysMap[String(day)];

      if (dayInfo) {
        const isProfit = dayInfo.is_profit;
        dayCell.className = `cal-day-cell ${isProfit ? 'profit-day' : 'loss-day'}`;
        dayCell.setAttribute('data-day', day);
        dayCell.innerHTML = `
          <span class="cal-day-number">${day}</span>
          <span class="cal-day-pnl">${dayInfo.net_pnl_formatted}</span>
          <span class="cal-day-trades">${dayInfo.trades} ${dayInfo.trades === 1 ? 'trade' : 'trades'}</span>
        `;
      } else {
        dayCell.className = 'cal-day-cell inactive-day';
        dayCell.setAttribute('data-day', day);
        dayCell.innerHTML = `<span class="cal-day-number">${day}</span>`;
      }

      // Allow clicking day box to highlight it (matches Figma style)
      dayCell.addEventListener('click', () => {
        document.querySelectorAll('.cal-day-cell').forEach(c => c.classList.remove('selected-day'));
        dayCell.classList.add('selected-day');
      });

      grid.appendChild(dayCell);
    }
  }

  // 4. Right Side Stats Cards
  // Month Net P&L Card
  const pnlEl = document.getElementById('calMonthNetPnl');
  const pnlCard = document.getElementById('calMonthPnlCard');
  if (pnlEl) {
    pnlEl.innerText = data.month_net_pnl_formatted || (data.month_net_pnl >= 0 ? '+' : '-') + '$' + Math.abs(data.month_net_pnl).toLocaleString();
    if (data.month_net_pnl >= 0) {
      pnlEl.className = 'stats-value pnl-value text-green';
      if (pnlCard) pnlCard.classList.remove('loss-card');
    } else {
      pnlEl.className = 'stats-value pnl-value text-red';
      if (pnlCard) pnlCard.classList.add('loss-card');
    }
  }

  const daysSummaryEl = document.getElementById('calMonthDaysSummary');
  if (daysSummaryEl) {
    daysSummaryEl.innerHTML = `${data.winning_days || 0} winning days &middot; ${data.losing_days || 0} losing days`;
  }

  // Win Rate & Profit Factor
  const winRateEl = document.getElementById('calWinRate');
  if (winRateEl) {
    winRateEl.innerText = `${data.win_rate}%`;
  }

  const pfEl = document.getElementById('calProfitFactor');
  if (pfEl) {
    pfEl.innerText = `${data.profit_factor}`;
  }

  // Best Day & Worst Day
  const bestValEl = document.getElementById('calBestDayVal');
  const bestDateEl = document.getElementById('calBestDayDate');
  if (data.best_day) {
    if (bestValEl) bestValEl.innerText = data.best_day.net_pnl_formatted;
    if (bestDateEl) bestDateEl.innerText = data.best_day.date;
  } else {
    if (bestValEl) bestValEl.innerText = '$0';
    if (bestDateEl) bestDateEl.innerText = '-';
  }

  const worstValEl = document.getElementById('calWorstDayVal');
  const worstDateEl = document.getElementById('calWorstDayDate');
  if (data.worst_day) {
    if (worstValEl) worstValEl.innerText = data.worst_day.net_pnl_formatted;
    if (worstDateEl) worstDateEl.innerText = data.worst_day.date;
  } else {
    if (worstValEl) worstValEl.innerText = '$0';
    if (worstDateEl) worstDateEl.innerText = '-';
  }
}
