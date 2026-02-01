import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Timestamp from '../views/Timestamp.vue'
import JsonValidator from '../views/JsonValidator.vue'
import EncodeConverter from '../views/EncodeConverter.vue'
import FileMD5 from '../views/FileMD5.vue'
import IPChecker from '../views/IPChecker.vue'
import CronParser from '../views/CronParser.vue'
import DataConstruction from '../views/DataConstruction.vue'

const routes = [
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
    component: DataConstruction
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router