"use strict";

// Editable inputs only. A browser draft never restores readiness or frozen authority.
let studyDraftEnabled = false, studyDraftRestoring = false, studyDraftUnsaved = false;
function studyDraftKey() { return "opent1d.m4-draft/1:" + session.draft_scope; }
function validateStudyDraft(raw) {
  if (typeof raw !== "string" || raw.length > 65536) throw new Error("Draft exceeds its bound");
  const value = JSON.parse(raw), config = value?.configuration;
  const exact = (object, keys) => object && typeof object === "object" && !Array.isArray(object) && Object.keys(object).sort().join() === keys.sort().join();
  const text = (value, maximum) => typeof value === "string" && value.length <= maximum && !value.includes("\0");
  if (!exact(value, ["schema", "configuration"]) || value.schema !== "opent1d.m4-draft/1" || !exact(config, ["schema", "sources", "scenarios", "timeout_seconds", "source_timeout_seconds"]) || config.schema !== session.defaults.schema || !Array.isArray(config.sources) || config.sources.length < 2 || config.sources.length > 8 || config.sources.some(item => !exact(item, ["id", "model", "declaration"]) || !text(item.id, 64) || !text(item.model, 4096) || !text(item.declaration, 4096)) || !Array.isArray(config.scenarios) || config.scenarios.length > 3 || new Set(config.scenarios).size !== config.scenarios.length || config.scenarios.some(item => !["fasting", "gastric_load_15g", "gastric_load_30g"].includes(item)) || [config.timeout_seconds, config.source_timeout_seconds].some(item => typeof item !== "number" || !Number.isFinite(item) || Math.abs(item) > 1e12)) throw new Error("Incompatible draft inputs");
  return config;
}
function studyDraftMessage(message) {
  $("study-draft-note").textContent = message;
  $("study-draft").hidden = !message;
}
function applyStudyDraft(config) {
  studyDraftRestoring = true;
  try {
    $("sources").replaceChildren(); config.sources.forEach(sourceCard);
    document.querySelectorAll('input[name="scenario"]').forEach(input => { input.checked = config.scenarios.includes(input.value); });
    $("stage-budget").value = config.timeout_seconds;
    $("source-budget").value = config.source_timeout_seconds;
    numberSources(); invalidate();
  } finally { studyDraftRestoring = false; }
}
function persistStudyDraft() {
  if (!studyDraftEnabled || studyDraftRestoring) return;
  studyDraftUnsaved = true;
  try {
    const raw = JSON.stringify({schema: "opent1d.m4-draft/1", configuration: formConfig()});
    validateStudyDraft(raw);
    sessionStorage.setItem(studyDraftKey(), raw);
    studyDraftUnsaved = false;
    studyDraftMessage("Draft saved in this browser tab. Reload restores inputs; setup must be checked again. Closing the tab may discard this draft.");
  } catch (_) { studyDraftMessage("Draft could not be saved in this tab. Reloading may discard changes; keep this page open until you have recorded the configuration."); }
}
function initializeStudyDraft() {
  if (!/^[0-9a-f]{64}$/.test(session.draft_scope || "")) return;
  studyDraftEnabled = true;
  try {
    const raw = sessionStorage.getItem(studyDraftKey());
    if (raw !== null) {
      applyStudyDraft(validateStudyDraft(raw));
      studyDraftMessage("Draft inputs restored in this browser tab. Check setup again before running.");
    }
  } catch (_) { studyDraftMessage("Saved draft could not be restored. Supplied examples are shown; review the inputs and check setup."); }
  $("reset-study-draft").addEventListener("click", () => {
    applyStudyDraft(session.defaults);
    try { sessionStorage.removeItem(studyDraftKey()); studyDraftUnsaved = false; }
    catch (_) { studyDraftUnsaved = true; }
    studyDraftMessage(studyDraftUnsaved ? "Draft storage could not be cleared. A previous draft may return on reload." : "Supplied examples restored. Check setup again before running.");
  });
  window.addEventListener("beforeunload", event => { if (studyDraftUnsaved) { event.preventDefault(); event.returnValue = ""; } });
}
