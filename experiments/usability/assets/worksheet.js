"use strict";
const OUTCOMES = ["completed_without_moderator_help", "completed_with_help", "blocked", "not_assessed"];
const SEVERITIES = ["blocking", "misinterpretation", "recoverable_difficulty", "presentation"];
const SESSION_FIELDS = ["role", "domain_experience", "software_experience", "platform", "python_uv", "installation_scope", "started_at", "ended_at", "guide_use", "archive_paths", "remaining_limits", "fix_commit", "retest_notes"];
const TASK_FIELDS = ["first_action", "assistance", "explanation", "issue", "artifact_path"];
const TEXT = {
  nl: {glossary:"Engelse woorden in het experimentscherm", glossaryDetail:"Het experimentscherm is in het Engels. Start = beginscherm; Insulin secretion = insulinesecretie; Results = resultaten; Options = opties; Check setup = controleer de voorbereiding; Run experiment = voer het experiment uit; Check saved analysis = controleer de opgeslagen analyse; View operation = bekijk de lopende taak; Cancel operation = annuleer de taak; Added archives = toegevoegde archieven. Source ID is de korte naam van een model. Python model is de rekencode (.py); Model declaration is het bijbehorende JSON-bestand met identiteit, herkomst, eenheden en interface. Houd het meegeleverde paar bij elkaar. Deze woordenlijst is uitleg, geen verplichte klikroute; noteer wanneer je hem gebruikt.", welcome:"OpenT1D-testsessie", intro:"Eén experiment met verzonnen invoer, gevolgd door jullie observaties. Er is geen tijdslimiet om te slagen.", scope:"Gebruik de meegeleverde verzonnen voorbeelden. Deze sessie onderzoekt de bediening; ze bewijst geen nauwkeurigheid bij echte mensen.", open:"Open het experimentscherm", tasks:"Opdrachten voor de tester", form:"Observatieformulier", moderator:"Instructies voor de begeleider", home:"Begin van de sessie", first:"Voor je begint", firstDetail:"Spreek af of installeren ook wordt getest of de omgeving vooraf is klaargezet. Zeg wanneer je de handleiding gebruikt of hulp nodig hebt. Houd het startvenster open.", think:"Werk zoals je normaal zou doen en denk waar mogelijk hardop. Vraag om hulp als dat nodig is; de begeleider noteert die hulp.", private:"Dit formulier blijft in deze browser totdat je het exporteert. Het wordt niet automatisch op de server of in de cloud opgeslagen. Exporteer regelmatig en noteer geen namen of contactgegevens.", save:"Exporteer observaties", restore:"Herstel een geëxporteerd verslag", newRetest:"Maak een hertest vanuit een eerder verslag", moderate:"Plan 45–60 minuten; noteer langere installatie of berekening apart. Lees de doelen voor, geen klikroute. Noteer alle hulp en de eigen uitleg van de tester.", criteria:"Noteer per taak: zelf gelukt, met hulp gelukt, vastgelopen of niet getest. Een niet bekeken taak is geen succes. Noteer een blokkade voordat je een opgeslagen rapport aanbiedt.", references:"Voorbeeldrapporten", referenceDetail:"Het volledige en onderbroken M4-archief zijn geregistreerd bij Added archives met het label session-reference. Open het experimentscherm en controleer daar expliciet de opgeslagen analyse voordat je ze leest. Alle geplande gevallen en ontbrekende waarden blijven zichtbaar.", retest:"Na de sessie", retestDetail:"Exporteer het formulier naar een privémap buiten de wetenschappelijke archieven. Bewaar het oorspronkelijke verslag. Los blokkades en verkeerd begrepen resultaten eerst op en herhaal de betrokken taken met de tester op een vastgelegde versie. Een beginnerstest sluit de formele onderzoekers- of P1-acceptatie niet automatisch af.", blank:"Nog niet genoteerd", outcome:"Uitkomst", severity:"Ernst", role:"Rol, zonder naam", domain_experience:"Ervaring met diabetes of onderzoek", software_experience:"Ervaring met computers en software", platform:"Werkelijk gebruikte Windows/WSL-, macOS- of Linux-versie", python_uv:"Werkelijke Python- en uv-versies", installation_scope:"Is installeren getest, vooraf verzorgd of niet getest?", started_at:"Werkelijke start van de sessie", ended_at:"Werkelijk einde van de sessie", guide_use:"Gebruik van de handleiding", archive_paths:"Paden/identiteiten van werkelijk gebruikte archieven", remaining_limits:"Resterende problemen en niet geteste onderdelen", fix_commit:"Werkelijk geteste versie bij een hertest", retest_notes:"Welke eerdere problemen worden opnieuw getest?", first_action:"Eerste gekozen actie", assistance:"Werkelijk gegeven hulp", explanation:"Uitleg van de tester, in eigen woorden", issue:"Waargenomen probleem", artifact_path:"Bijbehorend archief of rapport", completed_without_moderator_help:"Zelf gelukt", completed_with_help:"Met hulp gelukt", blocked:"Vastgelopen", not_assessed:"Niet getest", blocking:"Blokkade", misinterpretation:"Verkeerde interpretatie", recoverable_difficulty:"Overkomelijke moeilijkheid", presentation:"Presentatie", download:"Download aangevraagd. Controleer of het bestand werkelijk is opgeslagen voordat je sluit.", unsaved:"Nog niet geëxporteerde wijzigingen. Exporteer om deze te bewaren.", restored:"Eerder geëxporteerde waarden hersteld; er zijn geen nieuwe observaties toegevoegd.", retestCreated:"Nieuw hertestverslag met lege uitkomsten. Het oude bestand blijft bewaard. Noteer de werkelijk geteste versie.", importError:"Kan dit verslag niet herstellen: ", unknown:"Onbekend"},
  en: {glossary:"Interface terms", glossaryDetail:"Start is the home view; Insulin secretion is the secretion experiment; Results contains your experiments and Added archives. Source ID is a short model name. Python model is the calculation code (.py); Model declaration is its matching JSON file with identity, ancestry, units and interface. Keep the supplied pair together. Check setup validates preparation; Run experiment starts execution; Check saved analysis reconstructs retained evidence; View operation opens the ongoing task; Cancel operation stops it. This glossary explains terms, not a required click sequence; record when you use it.", welcome:"OpenT1D test session", intro:"One synthetic experiment, followed by your observations. There is no speed target.", scope:"Use the supplied invented examples. This session assesses software use; it does not establish accuracy in people.", open:"Open the experiment interface", tasks:"Participant tasks", form:"Observation form", moderator:"Moderator instructions", home:"Session start", first:"Before starting", firstDetail:"Agree whether installation is assessed or was prepared beforehand. Say when you use the guide or need help. Keep the startup window open.", think:"Work as you normally would and explain your thinking where comfortable. Ask for help when needed; the moderator records it.", private:"This form stays in this browser until you export it. There is no automatic server or cloud save. Export periodically and do not enter names or contacts.", save:"Export observations", restore:"Restore an exported record", newRetest:"Create a retest from a previous record", moderate:"Plan 45–60 minutes; record longer setup or execution separately. Read goals, not a click sequence. Record every intervention and the tester's own explanation.", criteria:"Record completed without help, completed with help, blocked or not assessed. An unobserved task is not a success. Record a block before offering a saved report.", references:"Reference reports", referenceDetail:"The complete and interrupted M4 archives are registered in Added archives with session-reference tags. Explicitly check saved analysis in the experiment interface before reading them. Planned denominators and unavailable values remain visible.", retest:"After the session", retestDetail:"Export privately outside scientific archives. Preserve the original record. Resolve blocking and interpretation issues first, then repeat affected tasks on an identified fix. A novice session does not automatically close intended-researcher or P1 acceptance.", blank:"Not recorded", outcome:"Outcome", severity:"Severity", role:"Non-identifying role", domain_experience:"Domain/research experience", software_experience:"Software experience", platform:"Actual Windows/WSL, macOS or Linux version", python_uv:"Actual Python and uv versions", installation_scope:"Installation assessed, prepared beforehand or not assessed?", started_at:"Actual session start", ended_at:"Actual session end", guide_use:"Guide use", archive_paths:"Actually used archive/report identities", remaining_limits:"Remaining issues and unassessed tasks", fix_commit:"Actually tested revision for a retest", retest_notes:"Which earlier issues are being retested?", first_action:"First action", assistance:"Actual assistance", explanation:"Tester explanation in their own words", issue:"Observed issue", artifact_path:"Related archive or report", completed_without_moderator_help:"Completed without help", completed_with_help:"Completed with help", blocked:"Blocked", not_assessed:"Not assessed", blocking:"Blocking", misinterpretation:"Misinterpretation", recoverable_difficulty:"Recoverable difficulty", presentation:"Presentation", download:"Download requested. Verify that the file was saved before closing.", unsaved:"Unexported changes. Export to retain them.", restored:"Previously exported values restored; no new observations were added.", retestCreated:"New retest record with empty outcomes. Keep the original file and record the actual tested revision.", importError:"Cannot restore this record: ", unknown:"Unknown"}
};

function emptyRecord(packet) {
  return {schema:"opent1d.usability-observations/1", session_id:"session-" + crypto.randomUUID(), packet_id:packet.id, packet_commit:packet.commit, language:packet.language, retest_of:null, previous_packet:null, context:Object.fromEntries(SESSION_FIELDS.map(key => [key, null])), tasks:packet.goals.map(goal => ({id:goal.id, outcome:null, severity:null, ...Object.fromEntries(TASK_FIELDS.map(key => [key, null]))}))};
}
function validateRecord(value, packet, restore) {
  const fail = message => {throw new Error(message);};
  if (!value || typeof value !== "object" || Array.isArray(value) || value.schema !== "opent1d.usability-observations/1") fail("Unsupported schema");
  const keys = ["schema","session_id","packet_id","packet_commit","language","retest_of","previous_packet","context","tasks"];
  if (Object.keys(value).sort().join() !== keys.sort().join()) fail("Unexpected record fields");
  if (typeof value.session_id !== "string" || !/^session-[0-9a-f-]{36}$/.test(value.session_id) || !/^packet-[0-9a-f]{32}$/.test(value.packet_id) || !/^[0-9a-f]{40}$/.test(value.packet_commit) || !["en","nl"].includes(value.language)) fail("Invalid record identity");
  if (restore && (value.packet_id !== packet.id || value.packet_commit !== packet.commit)) fail("Different packet: use the separate retest action");
  if (value.retest_of !== null && (typeof value.retest_of !== "string" || !/^session-[0-9a-f-]{36}$/.test(value.retest_of))) fail("Invalid parent session");
  if (value.previous_packet !== null && (typeof value.previous_packet !== "object" || Object.keys(value.previous_packet).sort().join() !== "commit,id" || !/^packet-[0-9a-f]{32}$/.test(value.previous_packet.id) || !/^[0-9a-f]{40}$/.test(value.previous_packet.commit))) fail("Invalid previous packet");
  const text = entry => entry === null || typeof entry === "string" && entry.length <= 8192;
  if (!value.context || typeof value.context !== "object" || Object.keys(value.context).sort().join() !== [...SESSION_FIELDS].sort().join() || !Object.values(value.context).every(text)) fail("Invalid context");
  if (!Array.isArray(value.tasks) || value.tasks.length !== packet.goals.length || value.tasks.some((task,index) => !task || task.id !== packet.goals[index].id || Object.keys(task).sort().join() !== ["id","outcome","severity",...TASK_FIELDS].sort().join() || task.outcome !== null && !OUTCOMES.includes(task.outcome) || task.severity !== null && !SEVERITIES.includes(task.severity) || !TASK_FIELDS.every(key => text(task[key])))) fail("Invalid task outcomes");
  return value;
}
function retestRecord(previous, packet) {
  validateRecord(previous, packet, false);
  const result = emptyRecord(packet);
  result.retest_of = previous.session_id;
  result.previous_packet = {id:previous.packet_id, commit:previous.packet_commit};
  return result;
}

async function initialize() {
  const embedded = document.getElementById("packet-data");
  let packet;
  if (embedded) packet = JSON.parse(embedded.textContent);
  else {
    const response = await fetch("/test/packet.json", {cache:"no-store"});
    if (!response.ok) throw new Error("Cannot load packet identity");
    packet = await response.json();
  }
  const words = {...TEXT[packet.language]};
  const mmtt = packet.goals.some(goal => goal.id === "mmtt_assumptions");
  if (mmtt) Object.assign(words, packet.language === "nl" ? {
    intro:"Twee korte opdrachten met verzonnen maaltijdtesten. We testen de software, niet jou. Er is geen tijdslimiet om te slagen.",
    form:"Feedback — installeren en twee opdrachten",
    glossaryDetail:"MMTT = maaltijdtest met metingen na een gemengde maaltijd; paired = twee gekoppelde testen; assumptions = analyse-aannames; estimated secretion = geschatte hoeveelheid afgegeven insuline; measurement times = meetmomenten; Results = resultaten; Check saved analysis = controleer opgeslagen analyse; Download report = bewaar rapport. De interface is Engels. Deze woordenlijst geeft geen klikroute. Noteer gebruik ervan.",
    remaining_limits:"Overige opmerkingen, resterende problemen en niet geteste onderdelen",
    explanation:"Wat zag je? Wat betekent het resultaat volgens jou? Wat is nog onduidelijk?",
    moderate:"Plan ongeveer 45–60 minuten voor de twee opdrachten; noteer installatie en extra tijd apart. Toon alleen de deelnemerskaart. Noteer hulp en de eigen uitleg van de tester."
  } : {intro:"Two short tasks with invented meal tests. We are testing the software, not you. There is no speed target.", form:"Feedback — installation and two tasks", glossaryDetail:"MMTT means mixed-meal tolerance test; paired means linked visits; assumptions are the analysis settings; secretion is the estimated amount of insulin released. Results contains retained reports. Check saved analysis reconstructs evidence. This glossary gives no click sequence; record its use.", remaining_limits:"Other comments, remaining issues and unassessed tasks"});
  if (!words) throw new Error("Unsupported packet language");
  document.documentElement.lang = packet.language;
  for (const element of document.querySelectorAll("[data-text]")) element.textContent = words[element.dataset.text];
  const identity = document.getElementById("identity");
  if (identity) identity.textContent = packet.id + " · " + packet.commit;
  const list = document.getElementById("goals");
  if (list) for (const goal of packet.goals.filter(goal => !mmtt || goal.id.startsWith("mmtt_"))) {const item = document.createElement("li"); item.textContent = goal.goal; list.append(item);}
  const refs = document.getElementById("references");
  if (refs) refs.textContent = Object.entries(packet.references).map(([key, value]) => key + ": " + value.status + " · report SHA-256 " + value.report_sha256["report.json"]).join("; ");
  const form = document.getElementById("observation-form");
  if (!form) return;
  let record = emptyRecord(packet), dirty = false, importMode = "restore", selectingRetest = false;
  const status = document.getElementById("save-status");
  const statusText = message => {status.textContent = message;};
  function field(parent, key, object, options) {
    const label = document.createElement("label"), title = document.createElement("span");
    title.textContent = words[key]; label.append(title);
    const input = document.createElement(options ? "select" : "textarea");
    input.dataset.field = key;
    if (options) for (const value of ["", ...options]) {const option = document.createElement("option"); option.value = value; option.textContent = value ? words[value] : words.blank; input.append(option);}
    else input.maxLength = 8192;
    input.value = object[key] || "";
    input.addEventListener("input", () => {object[key] = input.value || null; dirty = true; statusText(words.unsaved);});
    label.append(input); parent.append(label);
  }
  function render() {
    const context = document.getElementById("session-fields"), tasks = document.getElementById("task-fields");
    context.replaceChildren(); tasks.replaceChildren();
    const optionalContext = document.createElement("details"), contextSummary = document.createElement("summary");
    contextSummary.textContent = packet.language === "nl" ? "Versies, tijden en verdere sessiegegevens" : "Versions, times and further session context";
    optionalContext.append(contextSummary);
    for (const key of SESSION_FIELDS) field(["role","domain_experience","software_experience","platform","installation_scope", "remaining_limits"].includes(key) ? context : optionalContext, key, record.context);
    context.append(optionalContext);
    packet.goals.forEach((goal,index) => {
      const section = document.createElement("fieldset"), legend = document.createElement("legend");
      legend.textContent = goal.goal; section.dataset.task = goal.id; section.append(legend);
      field(section,"outcome",record.tasks[index],OUTCOMES);
      field(section,"explanation",record.tasks[index]);
      const detail = document.createElement("details"), summary = document.createElement("summary");
      summary.textContent = packet.language === "nl" ? "Hulp, problemen en overige observaties" : "Assistance, issues and further observations";
      detail.append(summary); field(detail,"severity",record.tasks[index],SEVERITIES);
      for (const key of TASK_FIELDS.filter(key => key !== "explanation")) field(detail,key,record.tasks[index]);
      section.append(detail); tasks.append(section);
    });
  }
  document.getElementById("export").addEventListener("click", () => {
    validateRecord(record, packet, true);
    const blob = new Blob([JSON.stringify(record,null,2) + "\n"], {type:"application/json"});
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = "opent1d-" + record.session_id + "-" + Date.now() + ".json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000); dirty = false; statusText(words.download);
  });
  const uploader = document.getElementById("import");
  uploader.addEventListener("click", () => {if (!selectingRetest) importMode = "restore";});
  uploader.addEventListener("cancel", () => {importMode = "restore";});
  uploader.addEventListener("change", async () => {
    try {
      const file = uploader.files[0];
      if (!file) return;
      if (file.size > 1048576) throw new Error("Record exceeds 1 MiB");
      if (dirty && !window.confirm(words.unsaved)) return;
      const candidate = JSON.parse(await file.text());
      record = importMode === "retest" ? retestRecord(candidate, packet) : validateRecord(candidate, packet, true);
      dirty = importMode === "retest"; render(); statusText(dirty ? words.retestCreated : words.restored);
    } catch (error) {statusText(words.importError + error.message);}
    finally {importMode = "restore"; uploader.value = "";}
  });
  document.getElementById("new-retest").addEventListener("click", () => {importMode = "retest"; uploader.value = ""; selectingRetest = true; uploader.click(); selectingRetest = false;});
  window.addEventListener("beforeunload", event => {if (dirty) {event.preventDefault(); event.returnValue = "";}});
  form.addEventListener("submit", event => event.preventDefault());
  render(); statusText(words.blank);
}
if (typeof document !== "undefined") initialize().catch(error => {const element = document.createElement("p"); element.textContent = error.message; element.setAttribute("role","alert"); document.querySelector("main").append(element);});
if (typeof module !== "undefined") module.exports = {emptyRecord, validateRecord, retestRecord};
