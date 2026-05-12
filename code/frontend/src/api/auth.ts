import apiClient from "./client";

export type LoginPayload = {
  username: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export const login = async (payload: LoginPayload) => {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", payload, {
    headers: {
      "Content-Type": "application/json",
    },
  });
  return data;
};

