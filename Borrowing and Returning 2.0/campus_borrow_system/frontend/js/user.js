import('./main.js')

async function fetchJSON(url, opts={}){
  const res = await fetch(url, Object.assign({credentials:'include'}, opts))
  return res.json()
}

function el(tag, cls, txt){ const e=document.createElement(tag); if(cls) e.className=cls; if(txt) e.textContent=txt; return e }

async function loadEquipment(){
  const cat = document.getElementById('categoryFilterUser')?.value || ''
  const q = cat?`?category=${encodeURIComponent(cat)}`:''
  const rows = await fetchJSON('/api/equipment'+q)
  const list = document.getElementById('equipmentListUser')
  list.innerHTML=''
  rows.forEach(r=>{
    const d = el('div','equip-item')
    const left = document.createElement('div')
    left.style.display = 'flex'
    left.style.alignItems = 'center'
    const name = document.createElement('div')
    name.className = 'name'
    name.textContent = r.equipment_name
    const meta = document.createElement('div')
    meta.className = 'meta'
    meta.innerHTML = `&nbsp;<span class='small'>[${r.category}] - ${r.quantity_available} available</span>`
    left.appendChild(name)
    left.appendChild(meta)

    const actions = document.createElement('div')
    actions.className = 'actions'
    const btn = el('button','btn','Request Borrow')
    btn.addEventListener('click', ()=>{
      // open modal and populate equipment id
      const modal = document.getElementById('borrowRequestModal')
      const form = document.getElementById('borrowRequestForm')
      document.getElementById('borrow_equipment_id').value = r.equipment_id
      // set default dates: borrow today, return tomorrow
      const now = new Date()
      const today = now.toISOString().slice(0,10)
      const tomorrow = new Date(Date.now()+24*3600*1000).toISOString().slice(0,10)
      // default time: current time (HH:MM)
      const hh = String(now.getHours()).padStart(2,'0')
      const mm = String(now.getMinutes()).padStart(2,'0')
      const timeNow = `${hh}:${mm}`
      document.getElementById('borrow_date').value = today
      document.getElementById('borrow_time').value = timeNow
      document.getElementById('return_date').value = tomorrow
      document.getElementById('return_time').value = timeNow
      modal.style.display = 'flex'
      modal.setAttribute('aria-hidden','false')
    })
    actions.appendChild(btn)
    d.appendChild(left)
    d.appendChild(actions)
    list.appendChild(d)
  })
}

async function loadMyRequests(){
  const rows = await fetchJSON('/api/borrow')
  const div = document.getElementById('myRequests')
  div.innerHTML=''
  rows.forEach(r=>{
    const d = el('div','equip-item')
    const equipName = r.equipment_name || r.equipment_id
    d.innerHTML = `<div><strong>Request #${r.request_id}</strong> — ${equipName} — <em>${r.status}</em></div>`
    // if approved, allow user to create a return request
    if(r.status === 'approved'){
      const ret = el('button','btn small','Return')
      ret.style.marginLeft='12px'
      ret.onclick = async ()=>{
        const resp = await fetchJSON('/api/return', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({borrow_id: r.request_id})})
        if(resp && resp.error) { alert(resp.error); return }
        alert('Return request submitted')
        loadReturnRequestsUser()
      }
      d.appendChild(ret)
    }
    div.appendChild(d)
  })
}

async function loadRecentBorrowsUser(){
  try{
    const resp = await fetch('/api/recent_borrows?limit=6', { credentials: 'include' })
    const tbody = document.querySelector('#recentBorrowsTableUser tbody')
    if(!tbody) return
    tbody.innerHTML = ''
    if(!resp.ok){
      tbody.innerHTML = `<tr><td colspan="4" class="small">Failed to load recent borrows (HTTP ${resp.status})</td></tr>`
      return
    }
    const rows = await resp.json()
    if(!rows || rows.length === 0){
      tbody.innerHTML = '<tr><td colspan="4" class="small">No recent borrows</td></tr>'
      return
    }
    rows.forEach(r=>{
      const tr = document.createElement('tr')
      tr.innerHTML = `<td>${r.request_id}</td><td>${r.equipment_name||r.equipment_id}</td><td>${r.borrow_date||''}</td><td>${r.status||''}</td>`
      tbody.appendChild(tr)
    })
    // update active borrow count tile based on current borrow list
    try{
      const my = await fetchJSON('/api/borrow')
      const active = (my||[]).filter(b=>b.status==='approved').length
      const el = document.getElementById('userActiveBorrow')
      if(el) el.textContent = active
    }catch(e){ /* ignore */ }
  }catch(err){
    console.error('loadRecentBorrowsUser failed', err)
    const tbody = document.querySelector('#recentBorrowsTableUser tbody')
    if(tbody) tbody.innerHTML = '<tr><td colspan="4" class="small">Failed to load recent borrows</td></tr>'
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  const cat = document.getElementById('categoryFilterUser')
  if(cat) cat.addEventListener('change', loadEquipment)
  document.getElementById('logoutBtn')?.addEventListener('click', async ()=>{ await fetch('/api/logout',{method:'POST'}); location.href='/' })
  // initial load for active view
  loadEquipment()
  loadMyRequests()
  loadReturnRequestsUser()
  loadRecentBorrowsUser()

  // simple view switching for sidebar
  document.querySelectorAll('.nav-item').forEach(a=>{
    a.addEventListener('click', (ev)=>{
      ev.preventDefault()
      document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active'))
      a.classList.add('active')
      const view = a.dataset.view
      document.querySelectorAll('.view').forEach(v=>v.style.display='none')
      const elView = document.getElementById(view)
      if(elView) elView.style.display = 'block'
      if(view === 'myrequest') loadEquipment()
      if(view === 'history') loadMyRequests()
      if(view === 'home') loadRecentBorrowsUser()
      if(view === 'return') loadReturnRequestsUser()
    })
  })

  // top action buttons
  document.getElementById('btnViewEquipment')?.addEventListener('click', ()=>{
    // open My Request view which contains equipment list
    document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active'))
    const el = document.querySelector('.nav-item[data-view="myrequest"]')
    if(el) el.classList.add('active')
    document.querySelectorAll('.view').forEach(v=>v.style.display='none')
    const view = document.getElementById('myrequest')
    if(view) view.style.display = 'block'
    loadEquipment()
  })
  document.getElementById('btnSubmitBorrow')?.addEventListener('click', ()=>{
    // same as ViewEquipment for now
    document.getElementById('btnViewEquipment')?.click()
  })
  document.getElementById('btnSubmitReturn')?.addEventListener('click', ()=>{
    document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active'))
    const el = document.querySelector('.nav-item[data-view="return"]')
    if(el) el.classList.add('active')
    document.querySelectorAll('.view').forEach(v=>v.style.display='none')
    const view = document.getElementById('return')
    if(view) view.style.display = 'block'
    loadReturnRequestsUser()
  })

  // borrow modal handlers
  const borrowModal = document.getElementById('borrowRequestModal')
  const borrowForm = document.getElementById('borrowRequestForm')
  if(borrowModal){
    document.getElementById('borrowCancel')?.addEventListener('click', ()=>{
      borrowModal.style.display='none'
      borrowModal.setAttribute('aria-hidden','true')
    })
    borrowForm?.addEventListener('submit', async (ev)=>{
      ev.preventDefault()
      const equipment_id = parseInt(document.getElementById('borrow_equipment_id').value)
      const quantity = parseInt(document.getElementById('borrow_quantity').value)
      const borrow_date = document.getElementById('borrow_date').value
      const borrow_time = document.getElementById('borrow_time')?.value || '00:00'
      const return_date = document.getElementById('return_date').value
      const return_time = document.getElementById('return_time')?.value || '00:00'
      // combine date + time into ISO-like string (YYYY-MM-DDTHH:MM)
      const borrow_datetime = borrow_date ? `${borrow_date}T${borrow_time}` : null
      const return_datetime = return_date ? `${return_date}T${return_time}` : null
      try{
        const resp = await fetchJSON('/api/borrow', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({equipment_id, quantity, borrow_date: borrow_datetime, return_date: return_datetime})})
        if(resp && resp.error){ alert(resp.error); return }
        alert('Borrow request submitted')
        borrowModal.style.display='none'
        borrowModal.setAttribute('aria-hidden','true')
        loadMyRequests()
        loadEquipment()
      }catch(err){ console.error(err); alert('Failed to submit request') }
    })
  }
})

async function loadReturnRequestsUser(){
  const rows = await fetchJSON('/api/return')
  const div = document.getElementById('returnRequestsUser')
  if(!div) return
  div.innerHTML = ''
  rows.forEach(r=>{
    const d = el('div','equip-item')
    d.textContent = `Return #${r.return_id} - borrow ${r.borrow_id} - ${r.status}`
    div.appendChild(d)
  })
}
