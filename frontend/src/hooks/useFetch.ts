import { useEffect, useState } from "react";

export type FetchState<T> =
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "empty" }
  | { status: "ready"; data: T };

export function useFetch<T>(
  fn: () => Promise<T>,
  deps: unknown[],
): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    setState({ status: "loading" });
    fn()
      .then((data) => {
        if (!alive) return;
        const anyData = data as unknown;
        const points =
          typeof anyData === "object" && anyData !== null && "points" in anyData
            ? (anyData as { points: unknown[] }).points
            : null;
        const isEmpty =
          data == null || (Array.isArray(data) && data.length === 0) || (points !== null && points.length === 0);
        setState(isEmpty ? { status: "empty" } : { status: "ready", data });
      })
      .catch((e: Error) => {
        if (alive) setState({ status: "error", error: e.message });
      });
    return () => {
      alive = false;
    };
  }, [...deps, attempt]); // deps merged deliberately: callers pass all reactive inputs

  void setAttempt; // kept for manual refetch wiring if needed later
  return state;
}
