<template>
  <div class="home">
    <div class="portal">
      <div class="portal-inner function-page">
        <div class="title">功能</div>
        <div class="subtitle">请选择您要使用的平台</div>

        <div class="card-row">
          <button class="card" type="button" @click="goHome">
            <div class="card-icon">
              <svg viewBox="0 0 64 64" aria-hidden="true">
                <path
                  d="M16 14h12v12H16V14Zm0 24h12v12H16V38Zm24-12h12v12H40V26ZM28 20h12v24H28V20Zm-8 0h8v8h-8v-8Zm0 24h8v8h-8v-8Zm24-12h8v8h-8v-8Z"
                  fill="currentColor"
                />
              </svg>
            </div>
            <div class="card-label">电价预测</div>
          </button>

          <button class="card" type="button" @click="goMarket">
            <div class="card-icon">
              <svg viewBox="0 0 64 64" aria-hidden="true">
                <path d="M36 4 14 36h16l-2 24 22-32H34l2-24Z" fill="currentColor" />
              </svg>
            </div>
            <div class="card-label">电力市场</div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

const goHome = () => {
  router.push("/home");
};

const goMarket = () => {
  router.push("/market");
};
</script>

<style scoped>
.function-page {
  min-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding-top: 110px;
}

.title {
  font-size: 40px;
  font-weight: 700;
  color: var(--primary);
  line-height: 1.2;
}

.subtitle {
  margin-top: 12px;
  font-size: 16px;
  color: var(--text);
}

.card-row {
  width: min(920px, 100%);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 80px;
  margin-top: 60px;
  padding: 0 20px;
}

.card {
  height: 170px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid var(--border);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  cursor: pointer;
}

.card:focus {
  outline: none;
}

.card-icon {
  width: 54px;
  height: 54px;
  color: var(--primary);
}

.card-icon svg {
  width: 100%;
  height: 100%;
  display: block;
}

.card-label {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary);
}
</style>
