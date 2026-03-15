async function toggle(qid, field, checkbox) {
    const val = checkbox.checked ? 1 : 0;
    try {
        const res = await fetch('/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qid, field, value: val })
        });
        if (!res.ok) throw new Error();
        const card = document.getElementById('qcard-' + qid);
        if (card) {
            card.dataset[field] = val;
            if (field === 'solved')
                card.classList.toggle('is-solved', val === 1);
            if (field === 'revision')
                card.classList.toggle('is-revision', val === 1);
        }
        showToast(
            val === 1
                ? (field === 'solved' ? '✓ Marked solved' : '⚑ Added to revision')
                : (field === 'solved' ? '✗ Unmarked'      : '⚑ Removed from revision')
        );
    } catch {
        checkbox.checked = !checkbox.checked;
        showToast('❌ Error — try again');
    }
}

let _toast;
function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(_toast);
    _toast = setTimeout(() => t.classList.remove('show'), 2000);
}

function restoreBackup(input) {
    if (!input.files[0]) return;
    if (!confirm('Overwrite current progress with this backup?')) return;
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/backup/restore';
    form.enctype = 'multipart/form-data';
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.name = 'backup_file';
    const dt = new DataTransfer();
    dt.items.add(input.files[0]);
    fileInput.files = dt.files;
    form.appendChild(fileInput);
    document.body.appendChild(form);
    form.submit();
}
