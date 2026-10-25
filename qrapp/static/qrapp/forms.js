export const config = JSON.parse(document.querySelector('#app-config').textContent);
export const $ = s => document.querySelector(s);
export function element(tag, text, className) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (className) e.className = className; return e; }
export function options(select) { Object.entries(config.labels).forEach(([value, label]) => { const o = element('option', label); o.value = value; select.append(o); }); }
export class ContentForm {
  constructor(container, select) { this.container = container; this.select = select; this.cache = {}; options(select); this.render('vcard'); select.addEventListener('change', () => { this.cache[this.kind] = this.value(); this.render(select.value, this.cache[select.value]); }); }
  render(kind, values = {}) {
    this.kind = kind; this.select.value = kind; this.container.replaceChildren();
    for (const [key, title, type] of config.schema[kind]) {
      const label = element('label', title); const input = element(type === 'textarea' ? 'textarea' : type === 'select' ? 'select' : 'input');
      input.name = key;
      if (input.tagName === 'INPUT') input.type = type;
      if (type === 'select') { for (const [value, text] of [['WPA','WPA / WPA2 / WPA3'],['WEP','WEP'],['nopass','Open']]) { const option = element('option', text); option.value = value; input.append(option); } }
      if (type === 'checkbox') { input.checked = !!values[key]; label.prepend(input); } else { input.value = values[key] ?? (key === 'timezone' ? Intl.DateTimeFormat().resolvedOptions().timeZone : ''); label.append(input); }
      if (type === 'number') { input.step = 'any'; input.min = key === 'latitude' ? -90 : -180; input.max = key === 'latitude' ? 90 : 180; }
      if (type === 'text' || type === 'textarea' || type === 'password') input.maxLength = 4000;
      if (type === 'url') input.placeholder = 'https://example.com';
      if (type === 'textarea' || config.schema[kind].length === 1) label.classList.add('wide');
      this.container.append(label);
    }
    if (kind === 'vcard') {
      this.custom = element('div', undefined, 'custom-fields'); this.container.append(this.custom);
      for (const item of values.custom || []) this.addCustom(item);
      const add = element('button', '+ Add custom field', 'text-button wide'); add.type = 'button'; add.onclick = () => { if (this.custom.children.length < 20) this.addCustom(); }; this.container.append(add);
    }
  }
  addCustom(item = {}) { const row = element('div', undefined, 'custom-row'); for (const key of ['name','value']) { const label = element('label', key === 'name' ? 'Custom field name' : 'Value'); const input = element('input'); input.dataset.custom = key; input.value = item[key] || ''; input.maxLength = key === 'name' ? 60 : 1000; label.append(input); row.append(label); } const remove = element('button','×');remove.type='button';remove.setAttribute('aria-label','Remove custom field');remove.onclick=()=>{row.remove();this.container.dispatchEvent(new Event('input',{bubbles:true}));};row.append(remove);this.custom.append(row);row.querySelector('input').focus(); }
  value() { const data = {}; this.container.querySelectorAll('[name]').forEach(e => data[e.name] = e.type === 'checkbox' ? e.checked : e.value); if (this.kind === 'vcard') data.custom = [...this.custom.children].map(row=>Object.fromEntries([...row.querySelectorAll('input')].map(e=>[e.dataset.custom,e.value]))); return data; }
  reset(kind='vcard',data={}) { this.cache={};this.render(kind,data); }
}
export class Appearance {
  constructor(container) { this.container=container;container.classList.add('appearance-fields');for(const [key,title,type] of [['foreground','Foreground','color'],['background','Background','color'],['size','Image size','select'],['rounded','Rounded modules','checkbox'],['transparent','Transparent background','checkbox']]) { const label=element('label',title);const input=element(type==='select'?'select':'input');input.name=key;if(type!=='select')input.type=type;else for(const size of [256,512,768,1024,2048]){const o=element('option',`${size} × ${size} px`);o.value=size;input.append(o);}if(type==='checkbox')label.prepend(input);else label.append(input);container.append(label);}this.set({}); }
  set(data) { const values={foreground:'#1f3685',background:'#ffffff',size:512,rounded:false,transparent:false,...data};this.container.querySelectorAll('[name]').forEach(e=>{if(e.type==='checkbox')e.checked=values[e.name];else e.value=values[e.name];}); }
  value() { return Object.fromEntries([...this.container.querySelectorAll('[name]')].map(e=>[e.name,e.type==='checkbox'?e.checked:e.name==='size'?Number(e.value):e.value])); }
}
export async function api(url, {method='GET', data, binary=false}={}) {
  const headers={};const csrf=document.cookie.split('; ').find(c=>c.startsWith('csrftoken='))?.split('=').slice(1).join('=');if(csrf)headers['X-CSRFToken']=decodeURIComponent(csrf);
  let body;if(data instanceof FormData)body=data;else if(data!==undefined){headers['Content-Type']='application/json';body=JSON.stringify(data);}
  const response=await fetch(url,{method,headers,body,credentials:'same-origin'});
  if(!response.ok){let detail;try{detail=await response.json();}catch{detail={error:`Request failed (${response.status}). Please retry.`};}const error=new Error(detail.error||'Request failed.');error.field=detail.field;error.status=response.status;if(response.status===401)document.dispatchEvent(new Event('workspace-locked'));throw error;}
  if(response.status===204)return null;return binary?response.blob():response.json();
}
export function download(blob,name){const url=URL.createObjectURL(blob);const a=element('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
export function notice(message){$('#notice').textContent=message;$('#notice').hidden=!message;}
export async function busy(button, work) {button.disabled=true;try{return await work();}catch(e){notice(e.message);return null;}finally{button.disabled=false;}}
