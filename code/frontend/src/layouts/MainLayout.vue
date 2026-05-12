<template>
  <div class="app">
    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-brand">
        <div class="header-brand-text">电价预测平台</div>
      </div>
      <div class="header-actions">
        <button class="btn outline sm" @click="goBack">返回平台选择页面</button>
      </div>
    </header>

    <div class="app-body">
      <!-- 左侧侧边栏 -->
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="sidebar-brand-text">电价预测平台</div>
        </div>

        <nav class="sidebar-menu">
          <div class="sidebar-section">功能模块</div>
          <RouterLink class="sidebar-item" to="/home" :class="{ active: $route.path === '/home' }">
            <span class="sidebar-item-icon">☰</span>
            <span>首页</span>
          </RouterLink>
          <RouterLink class="sidebar-item" to="/datasets" :class="{ active: $route.path === '/datasets' }">
            <span class="sidebar-item-icon">📊</span>
            <span>数据管理</span>
          </RouterLink>
          <RouterLink class="sidebar-item" to="/models" :class="{ active: $route.path === '/models' }">
            <span class="sidebar-item-icon">⚙</span>
            <span>模型管理</span>
          </RouterLink>
          <RouterLink class="sidebar-item" to="/predictions" :class="{ active: $route.path.startsWith('/predictions') }">
            <span class="sidebar-item-icon">📈</span>
            <span>预测</span>
          </RouterLink>
          <RouterLink class="sidebar-item" to="/ranking" :class="{ active: $route.path === '/ranking' }">
            <span class="sidebar-item-icon">👤</span>
            <span>评分管理</span>
          </RouterLink>

          <div class="sidebar-section">系统</div>
          <RouterLink class="sidebar-item" to="/account" :class="{ active: $route.path === '/account' }">
            <span class="sidebar-item-icon">⚙️</span>
            <span>账号设置</span>
          </RouterLink>
          <a class="sidebar-item" href="#" @click.prevent="handleLogout">
            <span class="sidebar-item-icon">🚪</span>
            <span>退出登录</span>
          </a>
        </nav>
      </aside>

      <!-- 右侧主内容区 -->
      <div class="main-wrapper">
        <main class="content">
          <slot />
        </main>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, useRouter } from "vue-router";

const router = useRouter();

const goBack = () => router.push("/functions");

const handleLogout = () => {
  localStorage.removeItem("access_token");
  router.push("/login");
};
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 52px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.header-brand {
  display: flex;
  align-items: center;
}

.header-brand-text {
  font-size: 18px;
  font-weight: 700;
  color: #1890ff;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.btn {
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.btn.outline {
  background: #fff;
  color: #333;
  border-color: #d9d9d9;
}

.btn.outline:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.btn.sm {
  padding: 4px 12px;
  font-size: 12px;
}

.sidebar {
  width: 180px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-brand {
  padding: 16px 20px;
  border-bottom: 1px solid #e8e8e8;
}

.sidebar-brand-text {
  font-size: 16px;
  font-weight: 600;
  color: #1890ff;
  margin: 0;
}

.sidebar-menu {
  padding: 8px 0;
}

.sidebar-section {
  padding: 12px 20px 4px;
  font-size: 12px;
  color: #999;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  color: #333;
  text-decoration: none;
  transition: all 0.2s;
  font-size: 14px;
  border-right: 3px solid transparent;
}

.sidebar-item:hover {
  background: #f5f7fa;
  color: #1890ff;
}

.sidebar-item.active {
  background: #e6f7ff;
  color: #1890ff;
  border-right-color: #1890ff;
  font-weight: 600;
}

.sidebar-item-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
}

.main-wrapper {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
  min-height: 0;
  position: relative;
}

.content {
  padding: 24px;
  box-sizing: border-box;
  overflow: visible;
  padding-bottom: 40px;
  min-height: 100%;
}
</style>
