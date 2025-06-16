<template>
  <form @submit.prevent="submit" class="w-80 mx-auto mt-24 flex flex-col gap-4">
    <input v-model="username" placeholder="username" class="border p-2 rounded" />
    <input v-model="password" type="password" class="border p-2 rounded" />
    <button class="bg-indigo-600 text-white rounded p-2">Log in</button>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/stores/useAuth'
import { useSocket } from '@/lib/socket'

const username = ref('')
const password = ref('')

const auth       = useAuth()
const { connect } = useSocket()
const router      = useRouter()

async function submit() {
  await auth.login(username.value, password.value)  // fetch JWT
  connect()                                         // open socket
  router.push({ name: 'pair-room', params: { roomId: 'room123' } })
}
</script>
