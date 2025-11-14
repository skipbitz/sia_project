import('./main.js')

async function fetchJSON(url, opts={}){
  const res = await fetch(url, Object.assign({credentials:'include'}, opts))
  return res.json()
}

function el(tag, cls, txt){ const e=document.createElement(tag); if(cls) e.className=cls; if(txt) e.textContent=txt; return e }

async function loadInventory(){
  const rows = await fetchJSON('/api/equipment')
  const div = document.getElementById('inventoryGridView') || document.getElementById('inventory')
  div.innerHTML=''
  if(!rows || rows.length===0){
    div.innerHTML = '<p class="small">No equipment found</p>'
    return
  }
  rows.forEach(r=>{
    const card = el('div','card')
    const img = el('div','img')
    const name = el('div','name', r.equipment_name)
    const meta = el('div','meta')
    meta.innerHTML = `<div class="meta-row">${r.category}</div><div class="meta-row">${r.quantity_available} available</div>`
    card.appendChild(img)
    card.appendChild(name)
    card.appendChild(meta)
    const actions = el('div','actions')
    const del = el('button','btn','Delete')
    del.style.marginTop='8px'
  del.onclick = async ()=>{ await fetch(`/api/equipment/${r.equipment_id}`,{method:'DELETE'}); loadInventory() }
    actions.appendChild(del)
    card.appendChild(actions)
    div.appendChild(card)
  })
  updateTiles().catch(()=>{})
}

async function loadBorrowRequests(){
  const rows = await fetchJSON('/api/borrow')
  const tableBody = document.querySelector('#borrowTable tbody')
  if(tableBody){
    tableBody.innerHTML = ''
    rows.forEach(r=>{
      const tr = document.createElement('tr')
      const username = r.username || r.user_id
      const equipment = r.equipment_name || r.equipment_id
      const returnDate = r.expected_return_date || r.return_date || ''
      // Build action buttons; include Delete only for denied items
        let actionsHtml = `<button class='btn approve' data-id='${r.request_id}'>Approve</button> <button class='btn deny' data-id='${r.request_id}'>Deny</button> <button class='btn' data-id='${r.request_id}' data-action='edit'>Edit</button>`
        if((r.status||'').toLowerCase() === 'denied'){
          actionsHtml += ` <button class='btn danger deleteBorrow' data-id='${r.request_id}'>Delete</button>`
        }
      tr.innerHTML = `<td>${r.request_id}</td><td>${username}</td><td>${equipment}</td><td>${r.borrow_date||''}</td><td>${returnDate}</td><td>${r.status}</td><td>${actionsHtml}</td>`
      tableBody.appendChild(tr)
    })
    tableBody.querySelectorAll('.approve').forEach(b=>b.addEventListener('click', async ()=>{ await fetch(`/api/borrow/${b.dataset.id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'approved'})}); loadBorrowRequests(); loadInventory() }))
    tableBody.querySelectorAll('.deny').forEach(b=>b.addEventListener('click', async ()=>{ await fetch(`/api/borrow/${b.dataset.id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'denied'})}); loadBorrowRequests(); }))
    tableBody.querySelectorAll('.deleteBorrow').forEach(b=>b.addEventListener('click', async ()=>{
      if(!confirm('Delete this denied borrow request? This cannot be undone.')) return
      try{
        const res = await fetch(`/api/borrow/${b.dataset.id}`, { method: 'DELETE', credentials: 'include' })
        if(!res.ok){
          const txt = await res.text().catch(()=>res.statusText)
          alert('Failed to delete: ' + (txt || ('HTTP ' + res.status)))
        }
      }catch(err){
        console.error('deleteBorrow failed', err)
        alert('Network error while deleting')
      }
      await loadBorrowRequests()
    }))

    // Edit button handling (open modal)
    tableBody.querySelectorAll('button[data-action="edit"]').forEach(b=>b.addEventListener('click', async ()=>{
      const id = b.dataset.id
      // fetch single borrow detail from /api/borrow list
      try{
        const rows = await fetchJSON('/api/borrow')
        const row = (rows||[]).find(x=>String(x.request_id) === String(id))
        if(!row){ alert('Borrow request not found'); return }
        // populate modal
        document.getElementById('edit_request_id').value = row.request_id
        document.getElementById('edit_quantity').value = row.quantity_requested || row.quantity || 1
        const bd = row.borrow_date || ''
        if(bd){ const parts = bd.split(' '); document.getElementById('edit_borrow_date').value = parts[0]; document.getElementById('edit_borrow_time').value = (parts[1]||'').slice(0,5) }
        const rd = row.expected_return_date || row.return_date || ''
        if(rd){ const parts = rd.split(' '); document.getElementById('edit_return_date').value = parts[0]; document.getElementById('edit_return_time').value = (parts[1]||'').slice(0,5) }
        const modal = document.getElementById('editBorrowModal')
        modal.style.display = 'flex'
        modal.setAttribute('aria-hidden','false')
      }catch(err){ console.error('open edit modal failed', err); alert('Failed to open edit form') }
    }))

    // edit modal handlers
    const editModal = document.getElementById('editBorrowModal')
    const editForm = document.getElementById('editBorrowForm')
    document.getElementById('editBorrowCancel')?.addEventListener('click', ()=>{ if(editModal){ editModal.style.display='none'; editModal.setAttribute('aria-hidden','true') } })
    editForm?.addEventListener('submit', async (ev)=>{
      ev.preventDefault()
      const id = document.getElementById('edit_request_id').value
      const quantity = parseInt(document.getElementById('edit_quantity').value || '1')
      const bd = document.getElementById('edit_borrow_date').value
      const bt = document.getElementById('edit_borrow_time').value || '00:00'
      const rd = document.getElementById('edit_return_date').value
      const rt = document.getElementById('edit_return_time').value || '00:00'
      const borrow_datetime = bd ? `${bd}T${bt}` : null
      const return_datetime = rd ? `${rd}T${rt}` : null
      try{
        const res = await fetch(`/api/borrow/${id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({quantity: quantity, borrow_date: borrow_datetime, return_date: return_datetime}), credentials: 'include'})
        if(!res.ok){ const txt = await res.text().catch(()=>res.statusText); alert('Failed to save: ' + (txt || ('HTTP ' + res.status))); return }
        editModal.style.display='none'; editModal.setAttribute('aria-hidden','true')
        await loadBorrowRequests()
      }catch(err){ console.error('save edit failed', err); alert('Network error while saving') }
    })
  } else {
    const div = document.getElementById('borrowRequests')
    div.innerHTML=''
    rows.forEach(r=>{
      const d = el('div','equip-item')
      d.innerHTML = `#${r.request_id} user ${r.user_id} equipment ${r.equipment_id} - ${r.status}`
      const a = el('button','', 'Approve')
      const dn = el('button','', 'Deny')
      a.onclick = async ()=>{ await fetch(`/api/borrow/${r.request_id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'approved'})}); loadBorrowRequests(); loadInventory() }
      dn.onclick = async ()=>{ await fetch(`/api/borrow/${r.request_id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'denied'})}); loadBorrowRequests(); }
      d.appendChild(a); d.appendChild(dn)
      div.appendChild(d)
    })
  }
}

async function loadReturnRequests(){
  const rows = await fetchJSON('/api/return')
  const tableBody = document.querySelector('#returnTable tbody')
  if(tableBody){
    tableBody.innerHTML = ''
    rows.forEach(r=>{
      const tr = document.createElement('tr')
      const username = r.username || r.user_id
      const equipment = r.equipment_name || r.equipment_id
      tr.innerHTML = `<td>${r.return_id}</td><td>${r.borrow_id}</td><td>${username}</td><td>${equipment}</td><td>${r.return_date||''}</td><td>${r.status}</td><td><button class='btn approveReturn' data-id='${r.return_id}'>Approve</button></td>`
      tableBody.appendChild(tr)
    })
    tableBody.querySelectorAll('.approveReturn').forEach(b=>b.addEventListener('click', async ()=>{
      try{
        const res = await fetch(`/api/return/${b.dataset.id}`,{method:'PUT'});
        if(!res.ok){
          const text = await res.text().catch(()=>res.statusText)
          alert('Failed to approve return: ' + (text || ('HTTP ' + res.status)))
        }
        await loadReturnRequests();
        await loadInventory();
      }catch(err){
        console.error('approveReturn fetch failed', err)
        alert('Network error while approving return')
      }
    }))
  } else {
    const div = document.getElementById('returnRequests')
    div.innerHTML=''
    rows.forEach(r=>{
      const d = el('div','equip-item')
      d.textContent = `#${r.return_id} borrow ${r.borrow_id} - ${r.status}`
      const a = el('button','', 'Approve Return')
      a.onclick = async ()=>{
        try{
          const res = await fetch(`/api/return/${r.return_id}`,{method:'PUT'})
          if(!res.ok){
            const text = await res.text().catch(()=>res.statusText)
            alert('Failed to approve return: ' + (text || ('HTTP ' + res.status)))
          }
          await loadReturnRequests();
          await loadInventory();
        }catch(err){
          console.error('approveReturn fetch failed', err)
          alert('Network error while approving return')
        }
      }
      d.appendChild(a)
      div.appendChild(d)
    })
  }
}

// update dashboard tiles
async function updateTiles(){
  const eq = await fetchJSON('/api/equipment')
  const br = await fetchJSON('/api/borrow')
  const total = eq.reduce((s,i)=>s + (i.quantity_available||0), 0)
  document.getElementById('totalEquip').textContent = total
  const active = br.filter(b=>b.status==='approved').length
  document.getElementById('activeBorrow').textContent = active
  // compute overdue count from current borrows endpoint (preferred) or fallback to borrow list
  try{
    const resp = await fetch('/api/current_borrows', { credentials: 'include' })
    if(resp.ok){
      const rows = await resp.json()
      const overdueCount = rows.reduce((cnt, r)=>{
        let returnDate = r.expected_return_date || r.return_date || ''
        let isOverdue = false
        if(returnDate){
          try{ const rd = (typeof returnDate === 'string') ? returnDate.replace(' ', 'T') : returnDate; const d = new Date(rd); if(!isNaN(d.getTime()) && d < new Date()) isOverdue = true }catch(e){}
        } else if(r.borrow_date){
          // fallback: treat borrow_date + 1 day as expected return
          try{ const bd = (typeof r.borrow_date === 'string') ? r.borrow_date.replace(' ', 'T') : r.borrow_date; const d = new Date(bd); if(!isNaN(d.getTime())){ d.setDate(d.getDate()+1); if(d < new Date()) isOverdue = true } }catch(e){}
        }
        return cnt + (isOverdue?1:0)
      }, 0)
      document.getElementById('overdueReturns').textContent = overdueCount
    }
  }catch(e){
    // fallback: no change
  }

  // load most-borrowed item
  try{
    const mb = await fetchJSON('/api/most_borrowed')
    const el = document.getElementById('mostBorrowed')
    if(el){
      if(mb && mb.length>0){
        const top = mb[0]
        el.textContent = `${top.equipment_name} (${top.borrow_count || 0})`
      } else {
        el.textContent = '--'
      }
    }
  }catch(e){
    // ignore
  }
}


async function loadRecentBorrows(){
  try{
    const resp = await fetch('/api/recent_borrows?limit=6', { credentials: 'include' })
    const tbody = document.querySelector('#recentBorrowsTable tbody')
    if(!tbody) return
    tbody.innerHTML = ''
    if(!resp.ok){
      tbody.innerHTML = `<tr><td colspan="5" class="small">Failed to load recent borrows (HTTP ${resp.status})</td></tr>`
      return
    }
    const rows = await resp.json()
    if(!rows || rows.length === 0){
      tbody.innerHTML = '<tr><td colspan="5" class="small">No recent borrows</td></tr>'
      return
    }
    rows.forEach(r=>{
      const tr = document.createElement('tr')
      tr.innerHTML = `<td>${r.request_id}</td><td>${r.username||r.user_id}</td><td>${r.equipment_name||r.equipment_id}</td><td>${r.borrow_date||''}</td><td>${r.status||''}</td>`
      tbody.appendChild(tr)
    })
  }catch(err){
    console.error('loadRecentBorrows failed', err)
    const tbody = document.querySelector('#recentBorrowsTable tbody')
    if(tbody) tbody.innerHTML = '<tr><td colspan="5" class="small">Failed to load recent borrows</td></tr>'
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  document.getElementById('logoutBtn')?.addEventListener('click', async ()=>{ await fetch('/api/logout',{method:'POST'}); location.href='/' })
  // wire Add Equipment button to open modal form
  const addEquipBtn = document.getElementById('addEquipBtn')
  const modal = document.getElementById('addEquipmentModal')
  const modalForm = document.getElementById('addEquipmentForm')
  const modalCancel = document.getElementById('addEquipCancel')

  addEquipBtn?.addEventListener('click', ()=>{
    if(!modal) return
    modal.style.display = 'flex'
    modal.setAttribute('aria-hidden','false')
    const nameInput = modal.querySelector('input[name="equipment_name"]')
    if(nameInput) nameInput.focus()
  })

  modalCancel?.addEventListener('click', ()=>{
    if(!modal) return
    modal.style.display = 'none'
    modal.setAttribute('aria-hidden','true')
    modalForm?.reset()
  })

  // click outside to close
  modal?.addEventListener('click', (ev)=>{ if(ev.target === modal){ modal.style.display='none'; modal.setAttribute('aria-hidden','true'); modalForm?.reset() } })

  // ESC to close
  document.addEventListener('keydown', (ev)=>{ if(ev.key === 'Escape'){ if(modal && modal.style.display !== 'none'){ modal.style.display='none'; modal.setAttribute('aria-hidden','true'); modalForm?.reset() } } })

  modalForm?.addEventListener('submit', async (ev)=>{
    ev.preventDefault()
    const fd = new FormData(modalForm)
    const body = {
      equipment_name: (fd.get('equipment_name')||'').toString().trim(),
      category: (fd.get('category')||'').toString().trim(),
      quantity_available: Number(fd.get('quantity_available')||0),
      status: (fd.get('status')||'available').toString()
    }
    if(!body.equipment_name){ alert('Name required'); return }
    try{
      const res = await fetchJSON('/api/equipment', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
      if(res && res.error){ alert(res.error); return }
      // success: close and refresh
      modal.style.display='none'
      modal.setAttribute('aria-hidden','true')
      modalForm.reset()
      await loadInventory()
      populateEquipmentTable()
    }catch(err){ console.error(err); alert('Failed to add equipment') }
  })
  // Edit Equipment modal handlers
  const editModal = document.getElementById('editEquipmentModal')
  const editForm = document.getElementById('editEquipmentForm')
  document.getElementById('editEquipCancel')?.addEventListener('click', ()=>{
    if(editModal){ editModal.style.display='none'; editModal.setAttribute('aria-hidden','true'); editForm?.reset() }
  })
  editModal?.addEventListener('click', (ev)=>{ if(ev.target === editModal){ editModal.style.display='none'; editModal.setAttribute('aria-hidden','true'); editForm?.reset() } })
  editForm?.addEventListener('submit', async (ev)=>{
    ev.preventDefault()
    const id = document.getElementById('edit_equipment_id').value
    const body = {
      equipment_name: document.getElementById('edit_equipment_name').value.trim(),
      category: document.getElementById('edit_category').value.trim(),
      quantity_available: Number(document.getElementById('edit_quantity_available').value || 0),
      status: document.getElementById('edit_status').value
    }
    try{
      const res = await fetch(`/api/equipment/${id}`, { method: 'PUT', credentials: 'include', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) })
      if(!res.ok){ const txt = await res.text().catch(()=>res.statusText); alert('Failed to save: ' + (txt || ('HTTP ' + res.status))); return }
      editModal.style.display='none'; editModal.setAttribute('aria-hidden','true'); editForm.reset()
      populateEquipmentTable(); loadInventory()
    }catch(err){ console.error('save equipment edit failed', err); alert('Network error while saving') }
  })
  loadInventory()
  loadBorrowRequests()
  loadReturnRequests()
  loadRecentBorrows()
  updateTiles()

  // nav handling: switch views
  document.querySelectorAll('.nav-item').forEach(a=>{
    a.addEventListener('click', (ev)=>{
      ev.preventDefault()
      document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active'))
      a.classList.add('active')
      const view = a.dataset.view
      document.querySelectorAll('.view').forEach(v=>v.style.display='none')
      const elView = document.getElementById(view)
      if(elView) elView.style.display = 'block'
      // refresh view data
      if(view === 'dashboard'){
        loadInventory()
        loadRecentBorrows()
      }else if(view === 'equipment'){
        loadInventory(); populateEquipmentTable()
      }else if(view === 'inventory'){
        loadInventory()
      }else if(view === 'borrow'){
        loadBorrowRequests()
      }else if(view === 'return'){
        loadReturnRequests()
      }else if(view === 'current_borrows'){
        loadCurrentBorrows()
      }else if(view === 'borrow_history'){
        loadBorrowHistory()
      }else if(view === 'users'){
        // load users table when the Users view is activated
        loadUsers()
      }
    })
  })
})

// populate equipment table
async function populateEquipmentTable(){
  const rows = await fetchJSON('/api/equipment')
  const tbody = document.querySelector('#equipmentTable tbody')
  tbody.innerHTML = ''
  rows.forEach(r=>{
    const tr = document.createElement('tr')
    tr.innerHTML = `<td>${r.equipment_id}</td><td>${r.equipment_name}</td><td>${r.category}</td><td>${r.quantity_available}</td><td>${r.status}</td><td><button class='btn editEquip' data-id='${r.equipment_id}'>Edit</button> <button class='btn deleteEquip' data-id='${r.equipment_id}'>Delete</button></td>`
    tbody.appendChild(tr)
  })
  // wire delete buttons
  tbody.querySelectorAll('.deleteEquip').forEach(b=>b.addEventListener('click', async ()=>{
    if(!confirm('Delete this equipment item?')) return
    try{
      const res = await fetch(`/api/equipment/${b.dataset.id}`, { method: 'DELETE', credentials: 'include' })
      if(!res.ok){ const txt = await res.text().catch(()=>res.statusText); alert('Failed to delete: ' + (txt || ('HTTP ' + res.status))); return }
      populateEquipmentTable(); loadInventory()
    }catch(err){ console.error('delete equipment failed', err); alert('Network error while deleting') }
  }))
  // wire edit buttons
  tbody.querySelectorAll('.editEquip').forEach(b=>b.addEventListener('click', async ()=>{
    const id = b.dataset.id
    try{
      const rows = await fetchJSON('/api/equipment')
      const item = (rows||[]).find(x=>String(x.equipment_id) === String(id))
      if(!item){ alert('Equipment not found'); return }
      document.getElementById('edit_equipment_id').value = item.equipment_id
      document.getElementById('edit_equipment_name').value = item.equipment_name || ''
      document.getElementById('edit_category').value = item.category || ''
      document.getElementById('edit_quantity_available').value = item.quantity_available || 0
      document.getElementById('edit_status').value = item.status || 'available'
      const modal = document.getElementById('editEquipmentModal')
      modal.style.display = 'flex'
      modal.setAttribute('aria-hidden','false')
    }catch(err){ console.error('open edit equipment failed', err); alert('Failed to open edit form') }
  }))
}

// load current borrows (approved borrow_request rows)
async function loadCurrentBorrows(){
  try{
    const resp = await fetch('/api/current_borrows', { credentials: 'include' })
    const tbody = document.querySelector('#currentBorrowsTable tbody')
    if(!tbody) return
    tbody.innerHTML = ''
    if(!resp.ok){
      tbody.innerHTML = `<tr><td colspan="4" class="small">Failed to load current borrows (HTTP ${resp.status})</td></tr>`
      return
    }
    const rows = await resp.json()
    if(!rows || rows.length === 0){
      tbody.innerHTML = '<tr><td colspan="4" class="small">No current borrows</td></tr>'
      return
    }
    rows.forEach(r=>{
      const tr = document.createElement('tr')
      const returnDate = r.expected_return_date || r.return_date || ''
      tr.innerHTML = `<td>${r.request_id}</td><td>${r.username||r.user_id}</td><td>${r.equipment_name||r.equipment_id}</td><td>${r.borrow_date||''}</td><td>${returnDate}</td>`
      // highlight overdue rows and add an Overdue badge. If expected_return_date missing,
      // fall back to borrow_date + 1 day as the estimated return deadline.
      let isOverdue = false
      if(returnDate){
        try{
          const rd = (typeof returnDate === 'string') ? returnDate.replace(' ', 'T') : returnDate
          const d = new Date(rd)
          if(!isNaN(d.getTime()) && d < new Date()){
            isOverdue = true
          }
        }catch(e){ /* ignore parse errors */ }
      } else if(r.borrow_date){
        try{
          const bd = (typeof r.borrow_date === 'string') ? r.borrow_date.replace(' ', 'T') : r.borrow_date
          const d = new Date(bd)
          if(!isNaN(d.getTime())){
            d.setDate(d.getDate() + 1) // default 1 day loan when no return date stored
            if(d < new Date()) isOverdue = true
          }
        }catch(e){ /* ignore parse errors */ }
      }
      if(isOverdue){
        tr.classList.add('overdue')
        try{
          const cells = tr.querySelectorAll('td')
          const returnCell = cells[cells.length - 1]
          if(returnCell){
            const badge = el('span','badge overdue','Overdue')
            returnCell.appendChild(badge)
            if(!returnCell.textContent.trim()){
              // show placeholder text if no explicit return date
              returnCell.insertBefore(document.createTextNode('(est)'), returnCell.firstChild)
            }
          }
        }catch(e){ /* ignore DOM append errors */ }
      }
      tbody.appendChild(tr)
    })
  }catch(err){
    console.error('loadCurrentBorrows failed', err)
    const tbody = document.querySelector('#currentBorrowsTable tbody')
    if(tbody) tbody.innerHTML = '<tr><td colspan="4" class="small">Failed to load current borrows</td></tr>'
  }
}

// load borrow history
async function loadBorrowHistory(){
  try{
    const resp = await fetch('/api/borrow_history', { credentials: 'include' })
    const tbody = document.querySelector('#borrowHistoryTable tbody')
    if(!tbody) return
    tbody.innerHTML = ''
    if(!resp.ok){
      tbody.innerHTML = `<tr><td colspan="6" class="small">Failed to load history (HTTP ${resp.status})</td></tr>`
      return
    }
    const rows = await resp.json()
    if(!rows || rows.length === 0){
      tbody.innerHTML = '<tr><td colspan="6" class="small">No history records</td></tr>'
      return
    }
    rows.forEach(r=>{
      const tr = document.createElement('tr')
      tr.innerHTML = `<td>${r.history_id}</td><td>${r.request_id||''}</td><td>${r.username||r.user_id||''}</td><td>${r.equipment_name||r.equipment_id||''}</td><td>${r.borrow_date||''}</td><td>${r.return_date||''}</td>`
      tbody.appendChild(tr)
    })
  }catch(err){
    console.error('loadBorrowHistory failed', err)
    const tbody = document.querySelector('#borrowHistoryTable tbody')
    if(tbody) tbody.innerHTML = '<tr><td colspan="6" class="small">Failed to load history</td></tr>'
  }
}

function renderInventoryGrid(){
  // kept for backward compatibility; simply reload inventory into grid
  loadInventory()
}

// load and render users for admin
async function loadUsers(){
  try{
    // First check session so we can show a clear message if not logged in or not admin
    const sessResp = await fetch('/api/session', { credentials: 'include' })
    let sess = null
    try{ sess = await sessResp.json() }catch(e){ /* ignore */ }
    if(!sess || !sess.session){
      const tbody = document.querySelector('#usersTable tbody')
      if(tbody) tbody.innerHTML = '<tr><td colspan="3" class="small">Not authenticated. Please log in.</td></tr>'
      return
    }
    if(sess.session.role !== 'admin'){
      const tbody = document.querySelector('#usersTable tbody')
      if(tbody) tbody.innerHTML = '<tr><td colspan="3" class="small">Access denied. Admins only.</td></tr>'
      return
    }

    const resp = await fetch('/api/users', { credentials: 'include' })
    const tbody = document.querySelector('#usersTable tbody')
    if(!tbody) return
    tbody.innerHTML = ''
    if(resp.status === 401){
      tbody.innerHTML = '<tr><td colspan="3" class="small">Not authenticated. Please log in.</td></tr>'
      return
    }
    if(resp.status === 403){
      tbody.innerHTML = '<tr><td colspan="3" class="small">Access denied. Admins only.</td></tr>'
      return
    }
    let data = null
    try{ data = await resp.json() }catch(e){ /* ignore parse errors */ }
    if(!resp.ok){
      const msg = data && data.error ? data.error : `HTTP ${resp.status}`
      tbody.innerHTML = `<tr><td colspan="3" class="small">Failed to load users: ${msg}</td></tr>`
      console.error('Failed to load users:', resp.status, data)
      return
    }
    const rows = data || []
    if(rows.length === 0){
      tbody.innerHTML = '<tr><td colspan="3" class="small">No users found</td></tr>'
      return
    }
    rows.forEach(u=>{
      const tr = document.createElement('tr')
      tr.innerHTML = `<td>${u.user_id}</td><td>${u.username}</td><td>${u.role||''}</td><td><button class='btn editUser' data-id='${u.user_id}'>Edit</button> <button class='btn deleteUser' data-id='${u.user_id}'>Delete</button></td>`
      tbody.appendChild(tr)
    })
    // wire delete buttons
    tbody.querySelectorAll('.deleteUser').forEach(b=>b.addEventListener('click', async ()=>{
      if(!confirm('Delete this user account? This cannot be undone.')) return
      try{
        const res = await fetch(`/api/users/${b.dataset.id}`, { method: 'DELETE', credentials: 'include' })
        if(!res.ok){ const txt = await res.text().catch(()=>res.statusText); alert('Failed to delete user: ' + (txt || ('HTTP ' + res.status))); return }
        await loadUsers()
      }catch(err){ console.error('delete user failed', err); alert('Network error while deleting user') }
    }))
    // wire edit buttons
    tbody.querySelectorAll('.editUser').forEach(b=>b.addEventListener('click', async ()=>{
      const id = b.dataset.id
      try{
        const resp = await fetch('/api/users', { credentials: 'include' })
        const users = await resp.json()
        const user = (users||[]).find(x=>String(x.user_id) === String(id))
        if(!user){ alert('User not found'); return }
        document.getElementById('edit_user_id').value = user.user_id
        document.getElementById('edit_user_username').value = user.username || ''
        document.getElementById('edit_user_role').value = user.role || 'user'
        document.getElementById('edit_user_password').value = ''
        const modal = document.getElementById('editUserModal')
        modal.style.display = 'flex'
        modal.setAttribute('aria-hidden','false')
      }catch(err){ console.error('open edit user failed', err); alert('Failed to open edit form') }
    }))
    // edit user modal handlers
    const editUserModal = document.getElementById('editUserModal')
    const editUserForm = document.getElementById('editUserForm')
    document.getElementById('editUserCancel')?.addEventListener('click', ()=>{ if(editUserModal){ editUserModal.style.display='none'; editUserModal.setAttribute('aria-hidden','true'); editUserForm?.reset() } })
    editUserModal?.addEventListener('click', (ev)=>{ if(ev.target === editUserModal){ editUserModal.style.display='none'; editUserModal.setAttribute('aria-hidden','true'); editUserForm?.reset() } })
    editUserForm?.addEventListener('submit', async (ev)=>{
      ev.preventDefault()
      const id = document.getElementById('edit_user_id').value
      const username = document.getElementById('edit_user_username').value.trim()
      const role = document.getElementById('edit_user_role').value
      const password = document.getElementById('edit_user_password').value
      const body = { username, role }
      if(password && password.length>0) body.password = password
      try{
        const res = await fetch(`/api/users/${id}`, { method: 'PUT', credentials: 'include', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) })
        if(!res.ok){ const txt = await res.text().catch(()=>res.statusText); alert('Failed to save user: ' + (txt || ('HTTP ' + res.status))); return }
        editUserModal.style.display='none'; editUserModal.setAttribute('aria-hidden','true'); editUserForm.reset()
        await loadUsers()
      }catch(err){ console.error('save user edit failed', err); alert('Network error while saving user') }
    })
  }catch(err){
    console.error('Failed to load users', err)
    const tbody = document.querySelector('#usersTable tbody')
    if(tbody) tbody.innerHTML = '<tr><td colspan="3" class="small">Failed to load users (network error)</td></tr>'
  }
}
