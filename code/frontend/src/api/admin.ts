import apiClient from "./client";

export type AdminInfo = {
  id: number;
  username: string;
  display_name: string;
  email: string | null;
  created_at: string;
  updated_at: string;
};

export const getCurrentAdmin = async () => {
  const { data } = await apiClient.get<AdminInfo>("/admin/me");
  return data;
};

export const updatePassword = async (currentPassword: string, newPassword: string) => {
  const { data } = await apiClient.put("/admin/me/password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return data;
};

export const updateProfile = async (username: string, displayName: string) => {
  const { data } = await apiClient.put("/admin/me", {
    username,
    display_name: displayName,
  });
  return data;
};