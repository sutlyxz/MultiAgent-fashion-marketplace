import type { MockUser, RegisterInput, UserRole } from "../types/marketplace";
import { apiUrl } from "./apiClient";

export const TOKEN_STORAGE_KEY = "clothify_access_token";
export const USER_STORAGE_KEY = "clothify_active_user";

export interface BackendUserResponse {
  id: string;
  email: string;
  role: string;
  name: string | null;
  store_name: string | null;
  created_at: string;
}

export interface BackendTokenResponse {
  access_token: string;
  token_type: string;
  user: BackendUserResponse;
}

function mapBackendUserToMockUser(backendUser: BackendUserResponse): MockUser {
  return {
    id: backendUser.id,
    name: backendUser.name || (backendUser.email.split("@")[0] ?? "Member"),
    email: backendUser.email,
    role: (backendUser.role as UserRole) || "buyer",
    storeName: backendUser.store_name || undefined,
  };
}

export const authService = {
  getToken(): string | null {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        return window.localStorage.getItem(TOKEN_STORAGE_KEY);
      }
    } catch {
      // Ignore storage errors
    }
    return null;
  },

  setToken(token: string | null) {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        if (token) {
          window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
        } else {
          window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
      }
    } catch {
      // Ignore storage errors
    }
  },

  clearSession() {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        window.localStorage.removeItem(USER_STORAGE_KEY);
      }
    } catch {
      // Ignore storage errors
    }
  },

  async login(email: string, password?: string): Promise<{ token: string; user: MockUser }> {
    const cleanEmail = email.trim();
    if (!cleanEmail) {
      throw new Error("Email is required.");
    }

    const payload = {
      email: cleanEmail,
      password: password || "",
    };

    const response = await fetch(apiUrl("/api/auth/login"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let detail = "Unable to sign in. Please check your credentials.";
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          detail = Array.isArray(errorData.detail)
            ? errorData.detail.map((d: { msg?: string }) => d.msg || "").join(", ")
            : errorData.detail;
        }
      } catch {
        // Fallback to status text
      }
      throw new Error(detail);
    }

    const data: BackendTokenResponse = await response.json();
    const token = data.access_token;
    const user = mapBackendUserToMockUser(data.user);

    this.setToken(token);
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
      }
    } catch {
      // Ignore storage errors
    }

    return { token, user };
  },

  async register(input: RegisterInput): Promise<{ token: string; user: MockUser }> {
    const { name, email, password, role, storeName } = input;

    if (!name?.trim()) {
      throw new Error("Full name is required.");
    }
    const cleanEmail = email.trim();
    if (!cleanEmail) {
      throw new Error("Email is required.");
    }
    if (!password) {
      throw new Error("Password is required.");
    }

    const userRole = role || "buyer";
    const registerPayload = {
      name: name.trim(),
      email: cleanEmail,
      password,
      role: userRole,
      store_name: userRole === "seller" && storeName?.trim() ? storeName.trim() : null,
    };

    const registerResponse = await fetch(apiUrl("/api/auth/register"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(registerPayload),
    });

    if (!registerResponse.ok) {
      let detail = "Registration could not be completed.";
      try {
        const errorData = await registerResponse.json();
        if (errorData?.detail) {
          detail = Array.isArray(errorData.detail)
            ? errorData.detail.map((d: { msg?: string }) => d.msg || "").join(", ")
            : errorData.detail;
        }
      } catch {
        // Fallback
      }
      throw new Error(detail);
    }

    // After successful registration, sign in to acquire JWT token and active session
    return await this.login(cleanEmail, password);
  },

  async getMe(token: string): Promise<MockUser | null> {
    const response = await fetch(apiUrl("/api/auth/me"), {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        this.clearSession();
        return null;
      }
      // For temporary server errors (5xx, etc.), throw to let caller catch network glitch
      throw new Error(`Server returned ${response.status}`);
    }

    const backendUser: BackendUserResponse = await response.json();
    const user = mapBackendUserToMockUser(backendUser);
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
      }
    } catch {
      // Ignore storage errors
    }
    return user;
  },

  async updateProfile(updates: Partial<MockUser>): Promise<MockUser> {
    const token = this.getToken();
    if (!token) {
      throw new Error("You must be signed in to update your profile.");
    }

    const payload: { name?: string; store_name?: string } = {};
    if (updates.name !== undefined) {
      payload.name = updates.name.trim();
    }
    if (updates.storeName !== undefined) {
      payload.store_name = updates.storeName.trim();
    }

    const response = await fetch(apiUrl("/api/auth/me"), {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let detail = "Unable to update profile details.";
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          detail = Array.isArray(errorData.detail)
            ? errorData.detail.map((d: { msg?: string }) => d.msg || "").join(", ")
            : errorData.detail;
        }
      } catch {
        // Fallback
      }
      throw new Error(detail);
    }

    const updatedBackendUser: BackendUserResponse = await response.json();
    const updatedUser = mapBackendUserToMockUser(updatedBackendUser);

    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(updatedUser));
      }
    } catch {
      // Ignore storage errors
    }

    return updatedUser;
  },

  async becomeSeller(storeName: string): Promise<MockUser> {
    const token = this.getToken();
    if (!token) {
      throw new Error("You must be signed in to open a boutique.");
    }
    const cleanStoreName = storeName.trim();
    if (!cleanStoreName || cleanStoreName.length < 2) {
      throw new Error("Store name must be at least 2 characters.");
    }

    const response = await fetch(apiUrl("/api/seller/become-seller"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ store_name: cleanStoreName }),
    });

    if (!response.ok) {
      let detail = "Unable to register boutique store.";
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          detail = Array.isArray(errorData.detail)
            ? errorData.detail.map((d: { msg?: string }) => d.msg || "").join(", ")
            : errorData.detail;
        }
      } catch {
        // Fallback
      }
      throw new Error(detail);
    }

    const backendUser: BackendUserResponse = await response.json();
    const updatedUser = mapBackendUserToMockUser(backendUser);

    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(updatedUser));
      }
    } catch {
      // Ignore storage errors
    }

    return updatedUser;
  },
};
