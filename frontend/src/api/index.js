import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

let _router = null
export function setApiRouter(router) {
  _router = router
}

// 请求拦截器：携带 token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器：401 清除 token 并跳转登录
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401 && error.config?.url !== '/auth/login' && error.config?.url !== '/auth/register') {
      localStorage.removeItem('token')
      const redirect = encodeURIComponent(window.location.pathname + window.location.search || '/data-construction')
      if (_router) {
        _router.push('/login?redirect=' + redirect).catch(() => {})
      } else {
        window.location.href = '#/login?redirect=' + redirect
      }
    }
    return Promise.reject(error)
  }
)

export default api