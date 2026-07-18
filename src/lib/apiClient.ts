import { auth } from './firebase';

/**
 * Appels à /api/v2 avec le token Firebase attaché.
 *
 * Depuis que l'API vérifie les tokens, toute requête doit porter un
 * `Authorization: Bearer <idToken>` — sinon 401. getIdToken() rafraîchit
 * automatiquement le token quand il est expiré.
 */

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

/** true quand le compte Firebase existe mais n'a pas encore de ligne `users`. */
export const isNotProvisioned = (error: unknown): boolean =>
  error instanceof ApiError && error.code === 'user_not_provisioned';

const authHeaders = async (): Promise<Record<string, string>> => {
  const user = auth.currentUser;
  if (!user) return {};
  const token = await user.getIdToken();
  return { Authorization: `Bearer ${token}` };
};

export const apiFetch = async <T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(await authHeaders()),
    ...((options.headers as Record<string, string>) || {}),
  };

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  const isJson = response.headers.get('content-type')?.includes('application/json');
  const body = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    throw new ApiError(
      body?.error || `Request failed (${response.status})`,
      response.status,
      body?.code,
    );
  }

  return body as T;
};

export interface OrganizationSummary {
  id: string;
  name: string;
  role: string | null;
}

export interface UserContext {
  id: string;
  email: string;
  full_name: string | null;
  organizations: OrganizationSummary[];
  organization_id: string | null;
}

/**
 * Nom saisi au formulaire, en attente de provisionnement.
 *
 * createUserWithEmailAndPassword déclenche onAuthStateChanged aussitôt, donc
 * AuthProvider provisionne avant que updateProfile ait posé le displayName.
 * Sans ce relais, un compte créé par email/mot de passe arriverait avec
 * full_name NULL et une organisation nommée d'après l'email — alors que
 * l'étape 1 vient justement de demander prénom et nom.
 */
let pendingFullName: string | undefined;

export const setPendingFullName = (name?: string) => {
  pendingFullName = name?.trim() || undefined;
};

/**
 * Crée (ou retrouve) le User et son organisation par défaut.
 * Idempotent : sûr à rejouer à chaque connexion.
 */
export const provisionAccount = (fullName?: string) => {
  const name = fullName?.trim() || pendingFullName;
  pendingFullName = undefined;
  return apiFetch<UserContext>('/api/v2/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ full_name: name }),
  });
};

export const fetchMe = () => apiFetch<UserContext>('/api/v2/auth/me');
