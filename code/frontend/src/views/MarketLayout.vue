<template>
  <div class="market-page">
    <header class="market-header">
      <h1 class="market-brand">电力市场平台</h1>
      <div class="header-actions">
        <button class="btn outline sm" @click="goBack">返回平台选择页面</button>
      </div>
    </header>
    <div class="market-layout">
      <!-- 左侧功能模块导航 -->
      <aside class="market-sidebar">
        <div class="sidebar-title">功能模块</div>
        <ul class="sidebar-nav">
          <li v-for="item in navItems" :key="item.key"
              :class="['nav-item', { active: isActive(item.path) || hasActiveChild(item) }]"
              @click="handleNavClick(item)">
            <span class="nav-icon">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
            <span v-if="item.children" class="nav-arrow" :class="{ rotated: openSubMenu === item.key }">▼</span>
          </li>
          <!-- 子菜单 -->
          <li v-if="openSubMenu === 'settlement'" class="sub-menu">
            <ul>
              <li v-for="child in getSubMenu('settlement')" :key="child.key"
                  :class="['sub-nav-item', { active: isActive(child.path) }]"
                  @click.stop="navigateTo(child.path)">
                <span>{{ child.label }}</span>
              </li>
            </ul>
          </li>
        </ul>
      </aside>

      <!-- 右侧内容区 -->
      <main class="market-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter, useRoute } from "vue-router";

const router = useRouter();
const route = useRoute();
const openSubMenu = ref<string | null>(null);

const goBack = () => router.push("/functions");

const navItems = [
  { key: "company", label: "企业信息", icon: "≡", path: "/market/company" },
  { key: "disclosure", label: "信息披露", icon: "📊", path: "/market/disclosure" },
  { key: "strategy", label: "策略报价", icon: "📈", path: "/market/strategy" },
  { key: "trading", label: "市场交易", icon: "⚙", path: "/market/trading" },
  {
    key: "settlement", 
    label: "结算报告", 
    icon: "💰", 
    path: "/market/settlement",
    children: [
      { key: "self-declare", label: "自主申报", path: "/market/settlement/self" },
      { key: "rational-declare", label: "基线申报", path: "/market/settlement/rational" },
      { key: "compare", label: "结果对比", path: "/market/settlement/compare" }
    ]
  },
];

const toggleSubMenu = (key: string) => {
  if (openSubMenu.value === key) {
    openSubMenu.value = null;
  } else {
    openSubMenu.value = key;
  }
};

const handleNavClick = (item: any) => {
  if (item.children) {
    toggleSubMenu(item.key);
  } else {
    navigateTo(item.path);
  }
};

const getSubMenu = (key: string) => {
  const item = navItems.find(item => item.key === key);
  return item?.children || [];
};

const navigateTo = (path: string) => {
  router.push(path);
};

const isActive = (path: string) => {
  return route.path === path;
};

const hasActiveChild = (item: any) => {
  if (!item.children) return false;
  return item.children.some((child: any) => isActive(child.path));
};
</script>

<style scoped>
/* 子菜单样式 */
.sub-menu {
  background: #f5f7fa;
  margin: 0 12px;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.sub-nav-item {
  padding: 8px 16px 8px 36px;
  cursor: pointer;
  font-size: 13px;
  color: #333;
  transition: all 0.2s;
}

.sub-nav-item:hover {
  background: rgba(24, 144, 255, 0.1);
}

.sub-nav-item.active {
  color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
  font-weight: 600;
}

/* 导航箭头样式 */
.nav-arrow {
  margin-left: auto;
  font-size: 10px;
  transition: transform 0.2s;
}

.nav-arrow.rotated {
  transform: rotate(180deg);
}
</style>

<style scoped>
.market-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.market-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 52px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}
.market-brand {
  font-size: 18px;
  font-weight: 700;
  color: #1890ff;
  margin: 0;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.market-layout {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 0;
  flex: 1;
}

/* 左侧导航 */
.market-sidebar {
  background: #fff;
  border-right: 1px solid #e8e8e8;
  padding: 20px 0;
}
.sidebar-title {
  padding: 0 20px 16px;
  font-size: 13px;
  color: #999;
}
.sidebar-nav {
  list-style: none;
  padding: 0;
  margin: 0;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}
.nav-item:hover {
  background: #f5f7fa;
}
.nav-item.active {
  color: #1890ff;
  border-left-color: #1890ff;
  background: #e6f7ff;
  font-weight: 600;
}
.nav-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
}

/* 右侧内容 */
.market-content {
  padding: 20px 24px;
  background: #f5f7fa;
  overflow-y: auto;
}

/* 按钮 */
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
</style>
