import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Meta } from "../api/types";

/** Loads /api/meta once and shares it across pages. */
export function useMeta(): { meta: Meta | null; error: string | null } {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api
      .meta()
      .then(setMeta)
      .catch((e: Error) => setError(e.message));
  }, []);
  return { meta, error };
}
