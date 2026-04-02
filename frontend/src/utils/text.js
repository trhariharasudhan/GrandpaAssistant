export function cleanPlannerItem(text) {
  return String(text || "").split(" - ")[0].trim();
}

export function normalizeMessageText(text) {
  return String(text || "").replace(/^Grandpa\s:\s*/, "").trim();
}

export function matchesCommand(command, query) {
  const normalizedCommand = String(command || "").toLowerCase();
  const normalizedQuery = String(query || "").trim().toLowerCase();
  if (!normalizedQuery) return true;
  return normalizedCommand.includes(normalizedQuery);
}
