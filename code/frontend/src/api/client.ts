import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api",
  timeout: 120000, // 2分钟，支持大文件上传
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === "ECONNABORTED") {
      error.message = "请求超时，请检查网络或稍后重试";
    } else if (!error.response) {
      error.message = "无法连接服务器，请确认后端服务已启动";
    }
    return Promise.reject(error);
  }
);

export default apiClient;

