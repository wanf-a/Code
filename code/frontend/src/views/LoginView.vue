<template>
  <div class="home">
    <div class="portal">
      <div class="portal-inner" style="max-width: 420px">
        <div class="panel" style="padding: 32px">
          <div class="portal-header" style="margin-bottom: 24px; text-align: left">
            <h1 class="portal-title" style="font-size: 24px">系统登录</h1>
            <p class="portal-subtitle">请输入账号密码登录系统</p>
          </div>

          <div class="form-grid" style="grid-template-columns: 1fr; padding: 0; gap: 16px">
            <div class="field">
              <label>账号</label>
              <input v-model="form.username" class="input" placeholder="请输入账号" />
            </div>
            <div class="field">
              <label>密码</label>
              <input v-model="form.password" class="input" type="password" placeholder="请输入密码" />
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; align-items: center; margin-top: 24px">
            <button class="btn primary" type="button" @click="handleLogin" :disabled="loading">
              {{ loading ? "登录中..." : "登录" }}
            </button>
          </div>

          <div v-if="error" style="margin-top: 16px; color: var(--red); font-size: 13px">
            {{ error }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "../api/auth";

const router = useRouter();
const loading = ref(false);
const error = ref("");

const form = reactive({
  username: "G13",
  password: "admin123",
});

const handleLogin = async () => {
  error.value = "";
  loading.value = true;
  try {
    const data = await login({ ...form });
    localStorage.setItem("access_token", data.access_token);
    await router.push("/functions");
  } catch (err) {
    error.value = "账号或密码错误";
  } finally {
    loading.value = false;
  }
};
</script>

