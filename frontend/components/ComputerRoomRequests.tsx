"use client";
import { useEffect, useState } from "react";

type Row = { id:number; entry_id?:number; time:string; subject:string; group:string; teacher:string; room:string; day:string; status:string; reason?:string; new_room?:string };
type Queue = {rows:Row[]; deadline:string|null; closed:boolean};
type Report = {id:number;date:string;mode:string;rows:Row[]};
const field="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";
const button="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50";
function localDay() { return new Intl.DateTimeFormat("sv-SE",{timeZone:"Asia/Yekaterinburg"}).format(new Date()); }
async function read<T>(url:string, init?:RequestInit):Promise<T> {
 const r=await fetch(url,{cache:"no-store",...init});
 if(!r.ok){const data=await r.json().catch(()=>({}));throw Error(typeof data.detail==="string"?data.detail:"Не удалось выполнить запрос");}
 return r.json();
}
export default function ComputerRoomRequests({api,teacher,onProcessed}:{api:string;teacher?:number;onProcessed:()=>void}){
 const base=api+"/room-requests";
 const [queue,setQueue]=useState<Queue|null>(null),[reports,setReports]=useState<Report[]>([]),[options,setOptions]=useState<Row[]>([]);
 const [day,setDay]=useState(localDay),[entry,setEntry]=useState(""),[deadline,setDeadline]=useState(""),[settings,setSettings]=useState(false);
 const [msg,setMsg]=useState(""),[busy,setBusy]=useState(false),[version,setVersion]=useState(0);
 useEffect(()=>{let live=true; async function load(){
 try{const [q,r]=await Promise.all([read<Queue>(base+(teacher?"?teacher_id="+teacher:"")),teacher?Promise.resolve([]):read<Report[]>(base+"/reports")]);
 if(live){setQueue(q);setReports(r);}}catch(e){if(live)setMsg((e as Error).message);}}
 void load();const timer=setInterval(load,60000);return()=>{live=false;clearInterval(timer);};},[base,teacher,version]);
 useEffect(()=>{let live=true;setOptions([]);setEntry("");
 if(teacher && day)read<Row[]>(base+"/options?teacher_id="+teacher+"&day="+day).then(r=>{if(live)setOptions(r);}).catch(e=>{if(live)setMsg(e.message);});return()=>{live=false};},[teacher,base,day,version]);
 async function action(path:string, method:string, body?:object){setBusy(true);setMsg("");
 try{const r=await read<{processed?:number}>(base+path,{method,headers:{"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
 setMsg(path==="/process"?"Обработано заявок: "+r.processed:path==="/hide"?"Обработанные заявки скрыты. Отчёты сохранены.":path==="/settings"?"Срок сбора сохранён.":"Заявка отправлена.");
 setVersion(v=>v+1);if(path==="/process")onProcessed();if(path==="/settings")setSettings(false);
 }catch(e){setMsg((e as Error).message);}finally{setBusy(false);}}
 const available=options.filter(o=>!queue?.rows.some(r=>r.day===day && r.entry_id===o.id));
 return <section className="my-4 w-full rounded-2xl border border-slate-200 bg-white p-5 text-slate-900">
 <h2 className="text-lg font-semibold">Заявки на компьютерную аудиторию</h2>
 <p className="my-2 text-sm text-slate-600">{teacher?"Выберите дату и занятие. Замена аудитории действует только на эту пару; время останется прежним.":"Заявки обрабатываются в порядке поступления. Для каждой пары система подбирает свободную аудиторию с компьютерами."}</p>
 {queue && <p className="mb-3 text-sm">{queue.closed?"Сбор закрыт":queue.deadline?"Сбор до "+new Date(queue.deadline).toLocaleString("ru-RU",{timeZone:"Asia/Yekaterinburg"})+" (Екатеринбург)":"Сбор открыт без срока"}</p>}
 {teacher?<div className="flex flex-wrap items-end gap-2"><label>Дата<br/><input className={field} type="date" value={day} min={localDay()} onChange={e=>setDay(e.target.value)}/></label>
 <label className="min-w-0 flex-1">Занятие<br/><select className={field+" w-full"} value={entry} onChange={e=>setEntry(e.target.value)}><option value="">{available.length?"Выберите пару":"Нет доступных занятий"}</option>{available.map(o=><option key={o.id} value={o.id}>{o.time} · {o.subject} · {o.group}</option>)}</select></label>
 <button className={button} disabled={busy||!entry||!queue||queue.closed} onClick={()=>action("","POST",{day,entry_id:Number(entry),teacher_id:teacher})}>Отправить заявку</button></div>:
 <div className="flex flex-wrap gap-2"><button className={button} disabled={busy||!queue?.rows.some(r=>r.status==="pending")} onClick={()=>action("/process","POST")}>Обработать все заявки</button>
 <button className={field} disabled={busy||!queue?.rows.some(r=>r.status!=="pending")} onClick={()=>action("/hide","POST")}>Очистить обработанные</button>
 <button className={field} aria-expanded={settings} onClick={()=>setSettings(!settings)}>Настройки сбора</button></div>}
 {settings && <form className="my-3 flex flex-wrap items-end gap-2 rounded-xl bg-slate-50 p-3" onSubmit={e=>{e.preventDefault();action("/settings","PUT",{deadline:new Date(deadline+":00+05:00").toISOString()});}}>
 <label>Срок сбора (Екатеринбург)<br/><input type="datetime-local" className={field} required value={deadline} onChange={e=>setDeadline(e.target.value)}/></label><button disabled={busy} className={button}>Открыть сбор до срока</button></form>}
 <p role="status" className="my-2 text-sm">{msg}</p>
 <ul className="max-h-64 divide-y overflow-auto">{queue?.rows.map(r=><li key={r.id} className="py-2 text-sm"><strong>{r.day} · {r.time} · {r.subject}</strong><br/>{r.teacher} · {r.group} · {r.status==="pending"?"Ожидает обработки":r.status==="assigned"?"Назначена: "+r.new_room:r.reason}</li>)}</ul>
 {queue && !queue.rows.length && <p className="text-sm text-slate-500">Заявок пока нет.</p>}
 {!teacher && <details className="mt-4"><summary className="cursor-pointer font-medium">Архив отчётов ({reports.length})</summary>{reports.map(r=><p key={r.id} className="mt-2 text-sm">{r.date} · {r.mode==="auto"?"По сроку":"Вручную"} · назначено {r.rows.filter(x=>x.status==="assigned").length} из {r.rows.length} · <a className="underline" href={base+"/reports/"+r.id+"/pdf"}>Скачать PDF</a></p>)}</details>}
 </section>;
}
