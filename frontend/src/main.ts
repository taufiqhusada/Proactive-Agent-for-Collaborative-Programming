import './assets/base.css'


// Import Bootstrap and BootstrapVue CSS files (order is important)
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'


import { createApp } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuth } from './stores/useAuth'

// Import localStorage cleanup
import { useRoomPersistence } from './composables/useLocalStorage'

// Initialize cleanup of expired room states
const { cleanupExpiredStates } = useRoomPersistence('')
cleanupExpiredStates()

// import { loader } from '@guolao/vue-monaco-editor'
// loader.config({
//   paths: {
//     vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs',
//   },
// })


const app   = createApp(App)
const pinia = createPinia()

// Make this Pinia instance the global/default one
setActivePinia(pinia)

app.use(pinia)
// now you can install router, i18n, etc., all of which may use stores
app.use(router)

// Initialize auth store
const auth = useAuth()
auth.initialize()

app.mount('#app')
