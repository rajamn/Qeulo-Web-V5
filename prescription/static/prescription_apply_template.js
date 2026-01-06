

// -------- Helpers to work with formset/table --------
function getFormsetCountInput() {
  return document.querySelector('input[name="details-TOTAL_FORMS"]');
}
function getTableBody() {
  return document.querySelector('#drug-table tbody');
}
function getHiddenTemplateRow() {
  return document.getElementById('empty-form');
}
function addOneRow() {
  const formCount = getFormsetCountInput();
  const tableBody = getTableBody();
  const emptyForm = getHiddenTemplateRow();
  if (!formCount || !tableBody || !emptyForm) return null;

  const idx = parseInt(formCount.value, 10);
  const clone = emptyForm.cloneNode(true);
  clone.removeAttribute('id');
  clone.style.display = '';

  // Enable inputs and replace __prefix__/index
  const re = /details-(?:__prefix__|\d+)-/g;
  clone.querySelectorAll('input, select, textarea, label').forEach(el => {
    if (el.tagName === 'LABEL') {
      const forAttr = el.getAttribute('for');
      if (forAttr) el.setAttribute('for', forAttr.replace(re, `details-${idx}-`));
      return;
    }
    el.disabled = false;
    if (el.name) el.name = el.name.replace(re, `details-${idx}-`);
    if (el.id)   el.id   = el.id.replace(re,   `details-${idx}-`);
    if (el.type === 'checkbox' || el.type === 'radio') el.checked = false;
    else el.value = '';
  });

  tableBody.appendChild(clone);
  formCount.value = idx + 1;
  return clone;
}
function lastRow() {
  const rows = getTableBody()?.querySelectorAll('tr.drug-row');
  return rows && rows.length ? rows[rows.length - 1] : null;
}
function rowIsEmpty(row) {
  const name = row?.querySelector('input[name$="-drug_name"]');
  return !name || !name.value.trim();
}
function setVal(row, selector, val) {
  const el = row?.querySelector(selector);
  if (!el) return;
  el.value = val || '';
  // Trigger change/input for any listeners
  el.dispatchEvent(new Event('input',  { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}
function fillRow(row, it) {
  setVal(row, 'input[name$="-drug_name"]',   it.drug_name);
  setVal(row, 'textarea[name$="-composition"], input[name$="-composition"]', it.composition);
  setVal(row, 'input[name$="-dosage"]',      it.dosage);
  setVal(row, 'input[name$="-frequency"]',   it.frequency);
  setVal(row, 'input[name$="-duration"]',    it.duration);
  setVal(row, 'select[name$="-food_order"]', it.food_order);
}

// -------- Populate templates dropdown --------
async function loadTemplates() {
  const sel = document.getElementById('rx-template-select');
  if (!sel) return;
  try {
    const r = await fetch(window.RX_TEMPLATES_LIST_URL, { credentials: 'same-origin' });
    const d = await r.json();
    if (!d.ok) return;
    (d.templates || []).forEach(t => {
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = t.name;
      sel.appendChild(opt);
    });
  } catch (_) { /* ignore */ }
}

// -------- Apply a selected template --------
async function applySelectedTemplate() {
  const sel = document.getElementById('rx-template-select');
  if (!sel || !sel.value) return;

  const btn = document.getElementById('btn-apply-template');
  btn && (btn.disabled = true);

  // Build a clean items URL from the list URL
  // RX_TEMPLATES_LIST_URL should be like: "/prescription/api/templates/"
  const listUrl = new URL(window.RX_TEMPLATES_LIST_URL, window.location.origin);
  const basePath = window.RX_TEMPLATES_LIST_URL.replace(/\/$/, '');  
  // Build final items URL safely by replacing the placeholder 0 only
  const itemsUrl = window.RX_TEMPLATE_ITEMS_URL.replace('0', String(sel.value));

    // or (even simpler if you don't care about the trailing slash pattern):
    // const itemsUrl = window.RX_TEMPLATE_ITEMS_URL.replace('0', sel.value);

  
  try {
    const r = await fetch(itemsUrl, { credentials: 'same-origin' });
    
    const d = await r.json();
    

    if (!r.ok || !d.ok) { alert(d.error || 'Could not load template'); return; }
    const items = d.items || [];
    if (!items.length) { alert('Template is empty'); return; }

    // --- your existing append/fill code follows ---
    let row = lastRow();
    let i = 0;
    if (row && rowIsEmpty(row)) {
      fillRow(row, items[0]);
      i = 1;
    }
    for (; i < items.length; i++) {
      const newRow = addOneRow();
      if (!newRow) { alert('Could not add a new row'); break; }
      fillRow(newRow, items[i]);
    }
    document.getElementById('drug-table')?.scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    console.error(e);
    alert('Network error while applying template');
  } finally {
    btn && (btn.disabled = false);
  }
}

// -------- Wire events --------
function wireApplyTemplate() {
  const sel = document.getElementById('rx-template-select');
  const btn = document.getElementById('btn-apply-template');

  if (sel) {
    sel.addEventListener('change', () => { btn && (btn.disabled = !sel.value); });
  }
  if (btn) {
    btn.addEventListener('click', (e) => {
      e.preventDefault(); e.stopPropagation();
      applySelectedTemplate();
    });
  }

  loadTemplates(); // populate on load
}

// Ensure DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', wireApplyTemplate);
} else {
  wireApplyTemplate();
}
