import type { NavigationGuardNext, RouteLocationNormalized } from "vue-router";

const publicRoutes = ["home", "login", "market"];

export const authGuard = (
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
) => {
  if (publicRoutes.includes(to.name as string)) {
    next();
    return;
  }
  const token = localStorage.getItem("access_token");
  if (!token) {
    next({ name: "login" });
    return;
  }
  next();
};

