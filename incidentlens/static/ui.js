"use strict";
let currentReport = null;
let requestVersion = 0;
const $ = id => document.getElementById(id);
function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}
function showTab(name) {
  document.querySelectorAll("[data-tab]").forEach(el => {
    const selected = el.dataset.tab === name;
    el.setAttribute("aria-selected", String(selected));
    el.tabIndex = selected ? 0 : -1;
  });
  ["analysis","timeline","evidence","audit"].forEach(id => $("panel-"+id).hidden = id !== name);
}
function refs(ids) {
  const container = node("div",undefined,"refs");
  ids.forEach(id => {
    const button = node("button",id,"ref");
    button.title = "Inspect source evidence " + id;
    button.addEventListener("click", () => {
      showTab("evidence");
      const target = $("source-"+id);
      if (target) { target.scrollIntoView({behavior:"smooth",block:"center"}); target.focus({preventScroll:true}); }
    });
    container.append(button);
  });
  return container;
}
function list(id, values) {
  $(id).replaceChildren(...values.map(value => node("li", value)));
}
function render(report) {
  currentReport = report;
  $("error").hidden=true;
  $("runbook-query").value="";
  document.querySelectorAll(".queue-item").forEach(el=>el.setAttribute("aria-pressed",String(el.dataset.incident===report.incident_id)));
  showRunbooks(report.runbooks || []);
  const decisions=report.planner_decisions || [];
  $("planner-status").textContent = report.planner_strategy === "structured"
    ? (report.planner_notes.length ? "Safe fallback: " + report.planner_notes.join(" ")
       : "Local AI completed: " + decisions.length + " model-selected read-only tools.")
    : "Evidence view: no model inference.";
  $("audit-mode").textContent = report.mode + ". Evidence analysis remains deterministic.";
  $("planner-trace").replaceChildren(...decisions.map((name,index)=>
    node("div","Model decision "+(index+1)+" · "+name,"row")));
  $("report-title").textContent = report.title;
  $("report-id").textContent = report.incident_id + " · " + (report.incident_id.startsWith("CUSTOM-") ? "Imported sanitized logs" : "Synthetic sample") + " · Original project by Alisha";
  $("priority").textContent = report.triage.priority;
  $("tool-count").textContent = report.audit.length + " / " + report.budget.max_tool_calls;
  $("mechanism").textContent = report.likely_failure_mechanism.title;
  $("mechanism-reason").textContent = report.likely_failure_mechanism.reason;
  $("mechanism-confidence").textContent = report.likely_failure_mechanism.confidence + " confidence · Heuristic assessment";
  $("summary").textContent = report.summary.text;
  $("facts").replaceChildren(...report.facts.map(fact => {
    const row = node("div",undefined,"row"); row.append(node("p",fact.text), refs(fact.evidence_ids)); return row;
  }));
  $("hypotheses").replaceChildren(...report.hypotheses.map(h => {
    const section = node("section",undefined,"hypothesis");
    section.append(node("h4",h.rank + ". " + h.title), node("p",h.confidence + " confidence","confidence-label"), node("p",h.reason), refs(h.supporting_evidence));
    if (h.contradicting_evidence.length) section.append(node("div","Contradicting evidence — review required","counter"),refs(h.contradicting_evidence));
    return section;
  }));
  list("missing",report.missing_evidence); list("next-checks",report.next_checks);
  $("dependencies").replaceChildren(...report.dependencies.map(d => node("div",d.from + " → " + d.to,"row")));
  $("correlations").replaceChildren(...Object.entries(report.correlations).map(([id,evidence]) => {
    const row=node("div",undefined,"row");row.append(node("strong",id),refs(evidence));return row;
  }));
  $("timeline").replaceChildren(...report.timeline.map(e => {
    const row = node("div",undefined,"timeline-item"); const detail=node("div");
    detail.append(node("span",e.service,"timeline-service"),node("span",e.kind || e.level,"kind"),node("div",e.message,"timeline-message"),refs([e.id]));
    row.append(node("div",new Date(e.timestamp).toISOString().replace("T", " ").replace(".000Z", " UTC"),"timeline-time"),detail); return row;
  }));
  $("evidence").replaceChildren(...Object.entries(report.evidence).map(([id,e])=>{
    const section = node("section",undefined,"evidence-item");section.id="source-"+id;section.tabIndex=-1;
    section.append(node("h4",id + (e.title ? " · " + e.title : "")),node("div",e.source + (e.line ? " · incident event line " + e.line : " · " + id) + (e.timestamp ? " · " + e.timestamp : ""),"location"),node("p",e.message));return section;
  }));
  $("hashes").replaceChildren(...Object.entries(report.source_hashes).map(([file,hash])=>{
    const row=node("div",undefined,"row");row.append(node("strong",file),node("p",hash,"hash"));return row;
  }));
  $("audit").replaceChildren(...report.audit.map(a=>{
    const row=node("div",undefined,"row");row.append(node("strong","Step "+a.step+" · "+a.tool),node("p","Read-only · "+a.duration_ms+" ms"),node("p",JSON.stringify(a.arguments),"hash"));return row;
  }));
  $("policy").textContent=report.remediation.policy;
  $("report").hidden=false;
  showTab("analysis");
}
async function loadIncident(id) {
  const version=++requestVersion;
  $("loading").hidden=false; $("report").hidden=true; $("error").hidden=true;
  document.querySelectorAll(".queue-item").forEach(el=>el.setAttribute("aria-pressed",String(el.dataset.incident===id)));
  try {
    const response=await fetch("/api/report?incident_id="+encodeURIComponent(id));
    if (!response.ok) throw new Error("Report request failed.");
    const report=await response.json();
    if(version===requestVersion) render(report);
  } catch(error) {
    if(version===requestVersion){$("error").textContent="The local report could not be loaded. Check that IncidentLens is still running."; $("error").hidden=false;}
  } finally {if(version===requestVersion) $("loading").hidden=true;}
}
function download(content, extension, mime) {
  if(!currentReport) return;
  const url=URL.createObjectURL(new Blob([content],{type:mime}));
  const a=node("a");a.href=url;a.download="IncidentLens-"+currentReport.incident_id+"."+extension;
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$("export-json").addEventListener("click",()=>download(JSON.stringify(currentReport,null,2),"json","application/json"));
$("export-md").addEventListener("click",()=>{
  if(currentReport && currentReport.markdown)
    download(currentReport.markdown,"md","text/markdown");
});
$("run-ai").addEventListener("click",async()=>{
  if(!currentReport || $("run-ai").disabled)return;
  const id=currentReport.incident_id;
  const version=++requestVersion;
  $("run-ai").disabled=true;
  document.querySelectorAll(".queue-item").forEach(el=>el.disabled=true);
  $("planner-status").textContent="Local AI investigation running… Evidence tools remain read-only.";
  $("error").hidden=true;
  try{
    const response=await fetch("/api/ai-report?incident_id="+encodeURIComponent(id),
      {headers:{"X-IncidentLens-AI":"1"}});
    if(!response.ok)throw new Error("Request failed");
    const report=await response.json();
    if(version===requestVersion)render(report);
  }catch(error){
    $("planner-status").textContent="AI request failed; the existing evidence report is retained.";
    $("error").textContent="Local AI could not complete. Check that the existing Ollama service is running.";
    $("error").hidden=false;
  }finally{
    $("run-ai").disabled=false;
    document.querySelectorAll(".queue-item").forEach(el=>el.disabled=false);
  }
});
document.querySelectorAll("[data-tab]").forEach(el=>{
  el.addEventListener("click",()=>showTab(el.dataset.tab));
  el.addEventListener("keydown",event=>{
    const tabs=[...document.querySelectorAll("[data-tab]")];
    const i=tabs.indexOf(el);let target;
    if(event.key==="ArrowRight")target=tabs[(i+1)%tabs.length];
    if(event.key==="ArrowLeft")target=tabs[(i+tabs.length-1)%tabs.length];
    if(event.key==="Home")target=tabs[0];
    if(event.key==="End")target=tabs[tabs.length-1];
    if(target){event.preventDefault();showTab(target.dataset.tab);target.focus();}
  });
});
async function refreshQueue(){
  try {
    const response=await fetch("/api/incidents");if(!response.ok)throw new Error();
    const catalog=await response.json();
    $("queue").replaceChildren(...catalog.map(incident=>{
      const button=node("button",undefined,"queue-item");button.dataset.incident=incident.id;button.setAttribute("aria-pressed","false");
      button.append(node("span",incident.id,"queue-id"),node("span",incident.title,"queue-title"),node("span",incident.scenario,"queue-scenario"));
      button.addEventListener("click",()=>loadIncident(incident.id));return button;
    }));
    if(catalog.length && !currentReport)await loadIncident(catalog[0].id);
  } catch(error) {$("loading").hidden=true;$("error").textContent="Sample incidents could not be loaded.";$("error").hidden=false;}
}
refreshQueue();
refreshHistory();

function workspaceStatus(text){ $("workspace-status").textContent=text; }
async function api(url,data){
  const response=await fetch(url,data===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json","X-IncidentLens-Action":"1"},body:JSON.stringify(data)});
  const body=await response.json();
  if(!response.ok)throw new Error(body.error || "Local request failed.");
  return body;
}
function showRunbooks(sections){
  $("runbook-results").replaceChildren(...sections.map(r=>{
    const item=node("section",undefined,"row");
    item.append(node("h4",r.id+" · "+r.title),node("p",r.text),
      node("p","Relevance score: "+r.score+" · matched: "+(r.matched_terms||[]).join(", ")+" · service match: "+Boolean(r.service_match),"muted"));
    return item;
  }));
  if(!sections.length)$("runbook-results").textContent="No matching runbooks.";
}
$("search-runbooks").addEventListener("click",async()=>{
  if(!currentReport)return;
  const version=requestVersion;
  try{const result=await api("/api/runbooks?incident_id="+encodeURIComponent(currentReport.incident_id)+"&q="+encodeURIComponent($("runbook-query").value));
    if(version===requestVersion)showRunbooks(result.sections);
  }catch(e){workspaceStatus(e.message);}
});
$("import-file").addEventListener("change",async()=>{
  const file=$("import-file").files[0];if(!file)return;
  if(file.size>512000){$("import-content").value="";$("import-file").value="";workspaceStatus("File exceeds 512 KB.");return;}
  try{$("import-content").value=new TextDecoder("utf-8",{fatal:true}).decode(await file.arrayBuffer());workspaceStatus("File read in this browser. Review it, then import explicitly.");}
  catch(e){$("import-content").value="";$("import-file").value="";workspaceStatus("The selected file must contain valid UTF-8 text.");}
});
$("import-logs").addEventListener("click",async()=>{
  if($("run-ai").disabled){workspaceStatus("Wait for the current AI investigation.");return;}
  $("import-logs").disabled=true;
  try{
    const result=await api("/api/import",{title:$("import-title").value,content:$("import-content").value});
    $("import-content").value="";$("import-file").value="";
    await refreshQueue();await loadIncident(result.incident_id);
    workspaceStatus(result.events+" events validated, sanitized and stored locally. Original text was not saved.");
  }catch(e){workspaceStatus(e.message);}
  finally{$("import-logs").disabled=false;}
});
$("save-report").addEventListener("click",async()=>{
  if(!currentReport)return;
  try{await api("/api/history/save",{snapshot_id:currentReport.snapshot_id});await refreshHistory();workspaceStatus("Investigation snapshot saved locally.");}
  catch(e){workspaceStatus(e.message);}
});
async function refreshHistory(){
  try{
    const rows=await api("/api/history");
    $("history").replaceChildren(...rows.map(r=>{
      const row=node("div",undefined,"row");const label=node("label");const check=node("input");check.type="checkbox";check.value=r.id;check.className="history-check";
      label.append(check,document.createTextNode(r.incident_id+" · "+r.saved_at+" · "+r.planner));
      const open=node("button","Open saved report","secondary");
      open.addEventListener("click",async()=>{
        if($("run-ai").disabled){workspaceStatus("Wait for the current AI investigation.");return;}
        const version=++requestVersion;
        try{const report=await api("/api/history/report?id="+encodeURIComponent(r.id));if(version===requestVersion){render(report);$("loading").hidden=true;workspaceStatus("Opened immutable saved snapshot; no new inference.");}}
        catch(e){workspaceStatus(e.message);}
      });row.append(label,open);return row;
    }));
    if(!rows.length)$("history").textContent="No saved investigations yet.";
  }catch(e){workspaceStatus(e.message);}
}
$("refresh-history").addEventListener("click",refreshHistory);
$("compare-history").addEventListener("click",async()=>{
  const ids=[...document.querySelectorAll(".history-check:checked")].map(el=>el.value);
  if(ids.length!==2){workspaceStatus("Select exactly two saved snapshots.");return;}
  try{
    const [a,b]=await Promise.all(ids.map(id=>api("/api/history/report?id="+encodeURIComponent(id))));
    const ea=new Set(Object.keys(a.evidence)),eb=new Set(Object.keys(b.evidence));
    const lines=[a.incident_id===b.incident_id ? "Same incident; snapshot comparison, not proof of recovery." : "Different incidents; differences do not establish incident progression.",
      "A: "+a.incident_id+" · "+a.generated_at,"B: "+b.incident_id+" · "+b.generated_at,
      "Priority A / B: "+a.triage.priority+" / "+b.triage.priority,
      "Confidence A / B: "+a.likely_failure_mechanism.confidence+" / "+b.likely_failure_mechanism.confidence,
      "Mechanism A: "+a.likely_failure_mechanism.title,"Mechanism B: "+b.likely_failure_mechanism.title,
      "Evidence A / B: "+ea.size+" / "+eb.size,
      "Only in B: "+([...eb].filter(id=>!ea.has(id)).join(", ")||"None"),
      "Only in A: "+([...ea].filter(id=>!eb.has(id)).join(", ")||"None")];
    $("comparison").replaceChildren(...lines.map(t=>node("p",t)));
  }catch(e){workspaceStatus(e.message);}
});
