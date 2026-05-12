<template>
  <MainLayout>
    <div class="page-header">
      <h1 class="page-title">账号设置</h1>
    </div>

    <section class="panel">
      <div class="panel-header">
        <h3 class="panel-title">基本信息</h3>
      </div>

      <div class="form-grid" style="grid-template-columns: 1fr 1fr">
        <div class="field">
          <label>账号</label>
          <input v-model="profile.username" class="input" placeholder="账号" />
        </div>
        <div class="field">
          <label>显示名</label>
          <input v-model="profile.display_name" class="input" placeholder="显示名" />
        </div>
        <div class="field">
          <label>创建时间</label>
          <input class="input" :value="profile.created_at" disabled />
        </div>
        <div class="field">
          <label>更新时间</label>
          <input class="input" :value="profile.updated_at" disabled />
        </div>
        <div class="field" style="align-self: end">
          <button class="btn primary" type="button" @click="saveProfile" :disabled="loadingProfile">
            {{ loadingProfile ? "保存中..." : "保存信息" }}
          </button>
        </div>
      </div>
    </section>

    <section class="panel" style="margin-top: 24px">
      <div class="panel-header">
        <h3 class="panel-title">修改密码</h3>
      </div>

      <div class="form-grid" style="grid-template-columns: 1fr 1fr">
        <div class="field">
          <label>当前密码</label>
          <input v-model="passwordForm.current_password" class="input" type="password" />
        </div>
        <div class="field">
          <label>新密码</label>
          <input v-model="passwordForm.new_password" class="input" type="password" />
        </div>
        <div class="field" style="align-self: end">
          <button class="btn primary" type="button" @click="savePassword" :disabled="loadingPassword">
            {{ loadingPassword ? "保存中..." : "修改密码" }}
          </button>
        </div>
      </div>

      <div v-if="message" style="padding: 0 20px 20px; color: var(--green); font-size: 13px">
        {{ message }}
      </div>
      <div v-if="error" style="padding: 0 20px 20px; color: var(--red); font-size: 13px">
        {{ error }}
      </div>
    </section>
  </MainLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import MainLayout from "../layouts/MainLayout.vue";
import { getCurrentAdmin, updatePassword, updateProfile } from "../api/admin";

const profile = reactive({
  username: "",
  display_name: "",
  created_at: "",
  updated_at: "",
});

const passwordForm = reactive({
  current_password: "",
  new_password: "",
});

const loadingProfile = ref(false);
const loadingPassword = ref(false);
const message = ref("");
const error = ref("");

const loadProfile = async () => {
  error.value = "";
  try {
    const data = await getCurrentAdmin();
    profile.username = data.username;
    profile.display_name = data.display_name;
    profile.created_at = data.created_at;
    profile.updated_at = data.updated_at;
  } catch (err) {
    error.value = "获取管理员信息失败";
  }
};

const saveProfile = async () => {
  message.value = "";
  error.value = "";
  loadingProfile.value = true;
  try {
    const data = await updateProfile(profile.username, profile.display_name);
    profile.updated_at = data.updated_at;
    message.value = "账号信息已更新";
  } catch (err) {
    error.value = "更新失败";
  } finally {
    loadingProfile.value = false;
  }
};

const savePassword = async () => {
  message.value = "";
  error.value = "";
  loadingPassword.value = true;
  try {
    await updatePassword(passwordForm.current_password, passwordForm.new_password);
    passwordForm.current_password = "";
    passwordForm.new_password = "";
    message.value = "密码已更新";
  } catch (err) {
    error.value = "修改密码失败";
  } finally {
    loadingPassword.value = false;
  }
};

onMounted(loadProfile);
</script>