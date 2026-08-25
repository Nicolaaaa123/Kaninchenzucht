import type {
  Animal,
  AnimalListItem,
  AnimalLookup,
  AnimalStatus,
  Breed,
  BreedGrowthCurveActual,
  BreedingCategory,
  BreedGrowthPoint,
  BreedScoringPosition,
  CageBox,
  ChatMessage,
  DashboardData,
  DescendantsGrowth,
  Evaluation,
  Feed,
  FeedingPlan,
  FeedPlanYear,
  GrowthCurve,
  GrowthStatus,
  LitterCreate,
  LitterResult,
  LitterStats,
  LitterSummary,
  LitterUpdate,
  User,
  MatingSuggestion,
  NameSuggestions,
  OffspringScores,
  PairingCheck,
  PedigreeNode,
  Relatedness,
  ScanResult,
  Sex,
  Stall,
  StallPage,
  StrengthsWeaknesses,
  WeightEntry,
  YearlyEvaluationStat,
  YearlyWeightStat,
} from "./types";

// Kein VITE_API_URL gesetzt (z.B. im Produktions-Docker-Build) -> relative
// Pfade, da Frontend und Backend dort von derselben Adresse ausgeliefert werden.
export const BASE_URL = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (res.status === 401) {
    window.dispatchEvent(new Event("auth:unauthorized"));
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  dashboard: () => request<DashboardData>("/api/dashboard"),

  auth: {
    login: (username: string, password: string) =>
      request<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
    logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
    me: () => request<User>("/api/auth/me"),
    merge: (code: string) => request<{ ok: boolean }>("/api/auth/merge", { method: "POST", body: JSON.stringify({ code }) }),
    listUsers: () => request<User[]>("/api/auth/users"),
    createUser: (data: { username: string; password: string; display_name?: string | null; is_admin?: boolean }) =>
      request<User>("/api/auth/users", { method: "POST", body: JSON.stringify(data) }),
  },

  breeds: {
    list: () => request<Breed[]>("/api/breeds"),
    create: (data: Record<string, unknown>) =>
      request<Breed>("/api/breeds", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Record<string, unknown>) =>
      request<Breed>(`/api/breeds/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: string) => request<void>(`/api/breeds/${id}`, { method: "DELETE" }),
    replaceScoringPositions: (id: string, positions: BreedScoringPosition[]) =>
      request<Breed>(`/api/breeds/${id}/scoring-positions`, {
        method: "PUT",
        body: JSON.stringify(positions),
      }),
    growthCurve: (id: string, sex?: Sex) =>
      request<GrowthCurve>(`/api/breeds/${id}/growth-curve${sex ? `?sex=${sex}` : ""}`),
    growthCurveActual: (id: string) => request<BreedGrowthCurveActual>(`/api/breeds/${id}/growth-curve-actual`),
    replaceGrowthCurve: (id: string, points: BreedGrowthPoint[]) =>
      request<GrowthCurve>(`/api/breeds/${id}/growth-curve`, { method: "PUT", body: JSON.stringify(points) }),
  },

  stats: {
    yearlyWeights: (breedId?: string) =>
      request<YearlyWeightStat[]>(`/api/stats/yearly-weights${breedId ? `?breed_id=${breedId}` : ""}`),
    yearlyEvaluations: (breedId?: string) =>
      request<YearlyEvaluationStat[]>(`/api/stats/yearly-evaluations${breedId ? `?breed_id=${breedId}` : ""}`),
  },

  feeds: {
    list: () => request<Feed[]>("/api/feeds"),
    create: (data: Record<string, unknown>) =>
      request<Feed>("/api/feeds", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Record<string, unknown>) =>
      request<Feed>(`/api/feeds/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: string) => request<void>(`/api/feeds/${id}`, { method: "DELETE" }),
  },

  stalls: {
    list: (pageId?: string) =>
      request<Stall[]>(`/api/stalls${pageId ? `?page_id=${pageId}` : ""}`),
    create: (data: { label: string; rows: number; columns: number; position?: number; page_id?: string | null }) =>
      request<Stall>("/api/stalls", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Record<string, unknown>) =>
      request<Stall>(`/api/stalls/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: string) => request<void>(`/api/stalls/${id}`, { method: "DELETE" }),
    addRow: (id: string) => request<Stall>(`/api/stalls/${id}/add-row`, { method: "POST" }),
    addColumn: (id: string) => request<Stall>(`/api/stalls/${id}/add-column`, { method: "POST" }),
    updateBox: (boxId: string, data: Record<string, unknown>) =>
      request<CageBox>(`/api/stalls/boxes/${boxId}`, { method: "PATCH", body: JSON.stringify(data) }),
    removeBox: (boxId: string) => request<void>(`/api/stalls/boxes/${boxId}`, { method: "DELETE" }),
  },

  stallPages: {
    list: () => request<StallPage[]>("/api/stall-pages"),
    create: (data: { label: string; position?: number }) =>
      request<StallPage>("/api/stall-pages", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Record<string, unknown>) =>
      request<StallPage>(`/api/stall-pages/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: string) => request<void>(`/api/stall-pages/${id}`, { method: "DELETE" }),
  },

  animals: {
    list: (params?: {
      search?: string;
      breed_id?: string;
      color_variant?: string;
      status?: AnimalStatus;
      category?: BreedingCategory;
    }) => {
      const qs = new URLSearchParams();
      if (params?.search) qs.set("search", params.search);
      if (params?.breed_id) qs.set("breed_id", params.breed_id);
      if (params?.color_variant) qs.set("color_variant", params.color_variant);
      if (params?.status) qs.set("status", params.status);
      if (params?.category) qs.set("category", params.category);
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      return request<AnimalListItem[]>(`/api/animals${suffix}`);
    },
    get: (id: string) => request<Animal>(`/api/animals/${id}`),
    create: (data: Record<string, unknown>) =>
      request<Animal>("/api/animals", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Record<string, unknown>) =>
      request<Animal>(`/api/animals/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: string) => request<void>(`/api/animals/${id}`, { method: "DELETE" }),
    children: (id: string) => request<AnimalListItem[]>(`/api/animals/${id}/children`),
    lookup: (identifier: string) =>
      request<AnimalLookup>(`/api/animals/lookup?identifier=${encodeURIComponent(identifier)}`),
    feedingPlan: (id: string) => request<FeedingPlan>(`/api/animals/${id}/feeding-plan`),
    pedigree: (id: string, generations = 4) =>
      request<PedigreeNode>(`/api/animals/${id}/pedigree?generations=${generations}`),
    pairingCheck: (motherId: string, fatherId: string) =>
      request<PairingCheck>(`/api/animals/pairing-check?mother_id=${motherId}&father_id=${fatherId}`),
    growthPlan: (id: string) => request<GrowthStatus>(`/api/animals/${id}/growth-plan`),
    descendantsGrowth: (id: string) => request<DescendantsGrowth>(`/api/animals/${id}/descendants-growth`),
    offspringScores: (id: string) => request<OffspringScores>(`/api/animals/${id}/offspring-scores`),
    strengthsWeaknesses: (id: string) => request<StrengthsWeaknesses>(`/api/animals/${id}/strengths-weaknesses`),
    feedPlanYear: (id: string) => request<FeedPlanYear>(`/api/animals/${id}/feed-plan-year`),
    relatedness: (a: string, b: string) =>
      request<Relatedness>(`/api/animals/relatedness?animal_a=${a}&animal_b=${b}`),
    matingSuggestions: (
      id: string,
      weights?: { total?: number; inbreeding?: number; complement?: number; focus?: number },
      focusCategories?: string[],
    ) => {
      const qs = new URLSearchParams();
      if (weights?.total != null) qs.set("weight_total", String(weights.total));
      if (weights?.inbreeding != null) qs.set("weight_inbreeding", String(weights.inbreeding));
      if (weights?.complement != null) qs.set("weight_complement", String(weights.complement));
      if (weights?.focus != null) qs.set("weight_focus", String(weights.focus));
      (focusCategories ?? []).forEach((c) => qs.append("focus_categories", c));
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      return request<MatingSuggestion[]>(`/api/animals/${id}/mating-suggestions${suffix}`);
    },
    createLitter: (data: LitterCreate) =>
      request<LitterResult>("/api/animals/litter", { method: "POST", body: JSON.stringify(data) }),
    nameSuggestions: (letter: string | null, count: number, sex?: Sex, exclude?: string[]) => {
      const qs = new URLSearchParams();
      if (letter) qs.set("letter", letter);
      qs.set("count", String(count));
      if (sex) qs.set("sex", sex);
      if (exclude && exclude.length > 0) qs.set("exclude", exclude.join(","));
      return request<NameSuggestions>(`/api/animals/name-suggestions?${qs.toString()}`);
    },
  },

  litters: {
    list: () => request<LitterSummary[]>("/api/litters"),
    animals: (litterName: string) =>
      request<AnimalListItem[]>(`/api/litters/${encodeURIComponent(litterName)}/animals`),
    stats: (litterName: string) =>
      request<LitterStats>(`/api/litters/${encodeURIComponent(litterName)}/stats`),
    update: (litterName: string, data: LitterUpdate) =>
      request<LitterSummary>(`/api/litters/${encodeURIComponent(litterName)}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },

  weights: {
    list: (animalId: string) => request<WeightEntry[]>(`/api/animals/${animalId}/weights`),
    create: (animalId: string, data: { measured_on: string; weight_grams: number; notes?: string | null }) =>
      request<WeightEntry>(`/api/animals/${animalId}/weights`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    remove: (animalId: string, entryId: string) =>
      request<void>(`/api/animals/${animalId}/weights/${entryId}`, { method: "DELETE" }),
  },

  evaluations: {
    list: (animalId: string) => request<Evaluation[]>(`/api/animals/${animalId}/evaluations`),
    create: (animalId: string, data: Record<string, unknown>) =>
      request<Evaluation>(`/api/animals/${animalId}/evaluations`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    remove: (animalId: string, evaluationId: string) =>
      request<void>(`/api/animals/${animalId}/evaluations/${evaluationId}`, { method: "DELETE" }),
  },

  chat: {
    send: (messages: ChatMessage[]) =>
      request<{ messages: ChatMessage[] }>("/api/chat", { method: "POST", body: JSON.stringify({ messages }) }),
  },

  scan: {
    evaluationCard: async (file: File): Promise<ScanResult> => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${BASE_URL}/api/scan/evaluation-card`, {
        method: "POST",
        body: form,
        credentials: "include",
      });
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const body = await res.json();
          detail = body.detail ?? detail;
        } catch {
          // ignore
        }
        throw new Error(detail);
      }
      return res.json() as Promise<ScanResult>;
    },
  },
};
