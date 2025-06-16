// const routes = [
//   {
//     path: '/example',
//     name: 'Example',
//     component: Example,
//   },
//   {
//     path: '/feedback',
//     name: 'Feedback',
//     component: Feedback,
//   },
//   {
//     path: '/guidedSimulation',
//     name: 'GranularSimulation',
//     component: GranularSimulation,
//   },
//   {
//     path: '/',
//     name: 'Main',
//     component: Main,
//   },
// ];


import { createRouter, createWebHistory,  } from 'vue-router'
import LoginView     from '@/views/LoginView.vue'
import PairRoomView  from '@/views/PairRoomView.vue'

const routes = [
  { path: '/',           name: 'login',    component: LoginView },
  { path: '/room/:roomId', name: 'pair-room', component: PairRoomView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
