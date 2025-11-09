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
      tr.innerHTML = `<td>${r.request_id}</td><td>${username}</td><td>${equipment}</td><td>${r.borrow_date||''}</td><td>${r.status}</td><td><button class='btn approve' data-id='${r.request_id}'>Approve</button> <button class='btn deny' data-id='${r.request_id}'>Deny</button></td>`
      tableBody.appendChild(tr)
    })
    tableBody.querySelectorAll('.approve').forEach(b=>b.addEventListener('click', async ()=>{ await fetch(`/api/borrow/${b.dataset.id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'approved'})}); loadBorrowRequests(); loadInventory() }))
    tableBody.querySelectorAll('.deny').forEach(b=>b.addEventListener('click', async ()=>{ await fetch(`/api/borrow/${b.dataset.id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'denied'})}); loadBorrowRequests(); }))
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
    tableBody.querySelectorAll('.approveReturn').forEach(b=>b.addEventListener('click', async ()=>{ await fetch(`/api/return/${b.dataset.id}`,{method:'PUT'}); loadReturnRequests(); loadInventory() }))
  } else {
    const div = document.getElementById('returnRequests')
    div.innerHTML=''
    rows.forEach(r=>{
      const d = el('div','equip-item')
      d.textContent = `#${r.return_id} borrow ${r.borrow_id} - ${r.status}`
      const a = el('button','', 'Approve Return')
      a.onclick = async ()=>{ await fetch(`/api/return/${r.return_id}`,{method:'PUT'}); loadReturnRequests(); loadInventory() }
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
  document.getElementById('overdueReturns').textContent = 0
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
  loadInventory()
  loadBorrowRequests()
  loadReturnRequests()
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
      }else if(view === 'equipment'){
        loadInventory(); populateEquipmentTable()
      }else if(view === 'inventory'){
        loadInventory()
      }else if(view === 'borrow'){
        loadBorrowRequests()
      }else if(view === 'return'){
        loadReturnRequests()
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
    tr.innerHTML = `<td>${r.equipment_id}</td><td>${r.equipment_name}</td><td>${r.category}</td><td>${r.quantity_available}</td><td>${r.status}</td><td><button class='btn' data-id='${r.equipment_id}'>Delete</button></td>`
    tbody.appendChild(tr)
  })
  tbody.querySelectorAll('button').forEach(b=>b.addEventListener('click', async ()=>{ await fetch(`/api/equipment/${b.dataset.id}`, {method:'DELETE'}); populateEquipmentTable(); loadInventory() }))
}

function renderInventoryGrid(){
  // kept for backward compatibility; simply reload inventory into grid
  loadInventory()
}
