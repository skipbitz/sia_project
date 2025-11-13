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
    btn.addEventListener('click', async ()=>{
      try{
        const resp = await fetchJSON('/api/borrow',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({equipment_id:r.equipment_id})})
        if(resp && resp.error) { alert(resp.error); return }
        alert('Borrow request submitted')
        loadMyRequests()
      }catch(err){ console.error(err); alert('Failed to submit request') }
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
    d.innerHTML = `<div><strong>Request #${r.request_id}</strong> — equipment ${r.equipment_id} — <em>${r.status}</em></div>`
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

document.addEventListener('DOMContentLoaded', ()=>{
  const cat = document.getElementById('categoryFilterUser')
  if(cat) cat.addEventListener('change', loadEquipment)
  document.getElementById('logoutBtn')?.addEventListener('click', async ()=>{ await fetch('/api/logout',{method:'POST'}); location.href='/' })
  // initial load for active view
  loadEquipment()
  loadMyRequests()
  loadReturnRequestsUser()

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
