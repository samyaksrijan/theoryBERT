export async function api(path, options) {
  const response = await fetch(`/api${path}`, options);
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      data.error || "The local engine could not complete this request.",
    );
  return data;
}

export async function runTask(payload, onPhase) {
  onPhase?.(
    payload.kind === "render"
      ? "rendering"
      : payload.kind === "cfg"
        ? "parsing"
        : "predicting",
  );
  const { job_id } = await api("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const deadline = Date.now() + 240_000;
  while (Date.now() < deadline) {
    const task = await api(`/jobs/${job_id}`);
    onPhase?.(task.phase);
    if (task.status === "complete") return task.result;
    if (task.status === "error") {
      const error = new Error(task.error);
      error.kind = task.error_kind;
      error.candidateGrammar = task.candidate_grammar;
      throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error(
    "The local engine took too long. Try a shorter input or preview-quality video.",
  );
}

export function downloadJSON(value, name = "theorybert-evidence.json") {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function useStorageState(React, key, initial) {
  const [value, setValue] = React.useState(() => {
    try {
      return JSON.parse(localStorage.getItem(key)) ?? initial;
    } catch {
      return initial;
    }
  });
  React.useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* Inputs still work when browser storage is full. */
    }
  }, [key, value]);
  return [value, setValue];
}
