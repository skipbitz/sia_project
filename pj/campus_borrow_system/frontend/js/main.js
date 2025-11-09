async function fetchJSON(url, opts={}){
  const res = await fetch(url, Object.assign({credentials:'include'}, opts))
  return res.json()
}

function el(tag, cls, txt){ const e=document.createElement(tag); if(cls) e.className=cls; if(txt) e.textContent=txt; return e }

async function loadPublicEquipment(){
  const cat = document.getElementById('categoryFilter')?.value || ''
  const q = cat?`?category=${encodeURIComponent(cat)}`:''
  const rows = await fetchJSON('/api/equipment'+q)
  const list = document.getElementById('equipmentList')
  list.innerHTML=''
  rows.forEach(r=>{
    const d = el('div','equip-item')
    d.innerHTML = `<strong>${r.equipment_name}</strong> <span class='small'>[${r.category}] - ${r.quantity_available} available</span>`
    list.appendChild(d)
  })
}

document.addEventListener('DOMContentLoaded', ()=>{
  const cat = document.getElementById('categoryFilter')
  if(cat) cat.addEventListener('change', loadPublicEquipment)
  loadPublicEquipment()

  const regLink = document.getElementById('registerLink')
  if(regLink) regLink.addEventListener('click', async ()=>{
    // fallback: go to register.html when clicked
    window.location.href = 'register.html'
  })

  const loginForm = document.getElementById('loginForm')
  if(loginForm){
    loginForm.addEventListener('submit', async (ev)=>{
      ev.preventDefault()
      const fd = new FormData(loginForm)
      const body = {username: fd.get('username'), password: fd.get('password')}
      const r = await fetchJSON('/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
      if(r.error) return alert(r.error)
      // redirect based on role
      const role = r.user && r.user.role
      if(role === 'admin') location.href = '/dashboard_admin.html'
      else location.href = '/dashboard_user.html'
    })
  }

  // register form handler (if present on register.html)
  const registerForm = document.getElementById('registerForm')
  if(registerForm){
    registerForm.addEventListener('submit', async (ev)=>{
      ev.preventDefault()
      const fd = new FormData(registerForm)
      const username = (fd.get('username')||'').toString().trim()
      const password = fd.get('password')
      const confirm = fd.get('confirm_password')
      if(!username || !password) return alert('Please provide email and password')
      if(password !== confirm) return alert('Passwords do not match')
      const payload = {username, password, role: 'user'}
      const res = await fetchJSON('/api/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      if(res && res.error) return alert(res.error)
      alert('Registration successful — please login')
      window.location.href = 'login.html'
    })
  }
})
