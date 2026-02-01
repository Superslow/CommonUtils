import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Timestamp from '../views/Timestamp.vue'
import JsonValidator from '../views/JsonValidator.vue'
import EncodeConverter from '../views/EncodeConverter.vue'
import FileMD5 from '../views/FileMD5.vue'
import IPChecker from '../views/IPChecker.vue'
import CronParser from '../views/CronParser.vue'
import DataConstruction from '../views/DataConstruction.vue'
import Login from '../views/Login.vue'
import UserManagement from '../views/UserManagement.vue'

function getToken() {
  try {
    return localStorage.getItem('token')
  } catch {
    return null
  }
}

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/timestamp',
    name: 'Timestamp',
    component: Timestamp
  },
  {
    path: '/json',
    name: 'JsonValidator',
    component: JsonValidator
  },
  {
    path: '/encode',
    name: 'EncodeConverter',
    component: EncodeConverter
  },
  {
    path: '/md5',
    name: 'FileMD5',
    component: FileMD5
  },
  {
    path: '/ip',
    name: 'IPChecker',
    component: IPChecker
  },
  {
    path: '/cron',
    name: 'CronParser',
    component: CronParser
  },
  {
    path: '/data-construction',
    name: 'DataConstruction',
    component: DataConstruction,
    meta: { requiresAuth: true }
  },
  {
    path: '/user-management',
    name: 'UserManagement',
    component: UserManagement,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫：需要登录的页面未带 token 时跳转登录
router.beforeEach((to, _from, next) => {
  if (to.meta.requiresAuth) {
    const token = getToken()
    if (!token || !token.trim()) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }
  next()
})

export default router