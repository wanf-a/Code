import { createRouter, createWebHistory } from "vue-router";
import { authGuard } from "./auth";
import AccountView from "../views/AccountView.vue";
import DatasetView from "../views/DatasetView.vue";
import FunctionSelectView from "../views/FunctionSelectView.vue";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import MarketLayout from "../views/MarketLayout.vue";
import CompanyInfoView from "../views/CompanyInfoView.vue";
import DisclosureView from "../views/DisclosureView.vue";
import TradingView from "../views/TradingView.vue";
import SelfDeclareView from "../views/SelfDeclareView.vue";
import RationalDeclareView from "../views/RationalDeclareView.vue";
import CompareView from "../views/CompareView.vue";
import StrategyView from "../views/StrategyView.vue";
import ModelsView from "../views/ModelsView.vue";
import PredictionsView from "../views/PredictionsView.vue";
import PredictionDetailView from "../views/PredictionDetailView.vue";
import RankingView from "../views/RankingView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/functions" },
    { path: "/login", name: "login", component: LoginView },
    { path: "/functions", name: "functions", component: FunctionSelectView },
    { path: "/home", name: "home", component: HomeView },
    { path: "/datasets", name: "datasets", component: DatasetView },
    { path: "/models", name: "models", component: ModelsView },
    { path: "/predictions", name: "predictions", component: PredictionsView },
    { path: "/predictions/:id", name: "prediction-detail", component: PredictionDetailView },
    { path: "/ranking", name: "ranking", component: RankingView },
    {
      path: "/market",
      component: MarketLayout,
      redirect: "/market/company",
      children: [
        { path: "company", name: "market-company", component: CompanyInfoView },
        { path: "disclosure", name: "market-disclosure", component: DisclosureView },
        { path: "trading", name: "market-trading", component: TradingView },
        {
          path: "settlement",
          name: "market-settlement",
          redirect: "/market/settlement/self",
          children: [
            { path: "self", name: "market-settlement-self", component: SelfDeclareView },
            { path: "rational", name: "market-settlement-rational", component: RationalDeclareView },
            { path: "compare", name: "market-settlement-compare", component: CompareView },
          ]
        },
        { path: "strategy", name: "market-strategy", component: StrategyView },
      ]
    },
    { path: "/account", name: "account", component: AccountView },
  ],
});

router.beforeEach(authGuard);
export default router;
