// static/js/prescription_save_template.js
console.log('[rx-template] script loaded');

function getCookie(name) {
  const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return m ? m.pop() : '';
}

function collectCurrentDetails() {
  const rows = [...document.querySelectorAll('#drug-table tbody tr.drug-row')];
  return rows.map(r => ({
    drug_name:  (r.querySelector('input[name$="-drug_name"]')?.value || '').trim(),
    composition:(r.querySelector('textarea[name$="-composition"],input[name$="-composition"]')?.value || '').trim(),
    dosage:     (r.querySelector('input[name$="-dosage"]')?.value || '').trim(),
    frequency:  (r.querySelector('input[name$="-frequency"]')?.value || '').trim(),
    duration:   (r.querySelector('input[name$="-duration"]')?.value || '').trim(),
    food_order: (r.querySelector('select[name$="-food_order"]')?.value || '').trim(),
  })).filter(it => it.drug_name);
}

async function rxDoSaveTemplate() {
  const nameInput = document.getElementById('tmplName');
  const saveBtn   = document.getElementById('confirmSaveTemplate');
  const modalEl   = document.getElementById('saveAsTemplateModal');

  if (!nameInput || !saveBtn || !modalEl) {
    alert('Template UI elements not found'); 
    return;
  }

  const name = (nameInput.value || '').trim();
  if (!name) { alert('Please enter a template name'); return; }

  const details = collectCurrentDetails();
  if (!details.length) { alert('No items to save'); return; }

  saveBtn.disabled = true; const orig = saveBtn.innerHTML; saveBtn.innerHTML = 'Saving...';

  try {
    const res = await fetch(window.SAVE_RX_TEMPLATE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ name, details })
    });
    const data = await res.json();

    console.log('[rx-template] save status:', res.status, data);

    if (!res.ok || !data.ok) {
      alert(data.error || 'Failed to save template');
      return;
    }

    (bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl)).hide();

    const sel = document.getElementById('rx-template-select');
    if (sel) {
      const opt = document.createElement('option');
      opt.value = data.template_id;
      opt.textContent = data.name;
      sel.appendChild(opt);
      sel.value = data.template_id;
      document.getElementById('btn-apply-template')?.removeAttribute('disabled');
    }

    nameInput.value = '';
    alert('Template saved successfully');
  } catch (e) {
    console.error(e);
    alert('Network error while saving template');
  } finally {
    saveBtn.disabled = false; saveBtn.innerHTML = orig;
  }
}

// Event delegation: clicks anywhere, only acts if your button (or its icon) was clicked
document.addEventListener('click', function(e) {
  const btn = e.target.closest('#confirmSaveTemplate');
  if (!btn) return;
  e.preventDefault(); e.stopPropagation();
  rxDoSaveTemplate();
});

// Also allow Enter key in the name field
document.addEventListener('keydown', function(e) {
  if (e.key !== 'Enter') return;
  const modalOpen = document.getElementById('saveAsTemplateModal')?.classList.contains('show');
  if (!modalOpen) return;
  if (document.activeElement?.id === 'tmplName') {
    e.preventDefault(); e.stopPropagation();
    rxDoSaveTemplate();
  }
});

// When modal opens, clear & focus the input
document.addEventListener('shown.bs.modal', function(e) {
  if (e.target.id !== 'saveAsTemplateModal') return;
  const nameInput = document.getElementById('tmplName');
  if (nameInput) { nameInput.value = ''; nameInput.focus(); }
});
