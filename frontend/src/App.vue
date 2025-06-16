<template>
  <!-- <TheHeader /> -->
  <router-view />
<!-- 
  <form @submit.prevent="submit" class="w-80 mx-auto mt-24 flex flex-col gap-4">
    <input v-model="username" placeholder="username" class="border p-2 rounded" />
    <input v-model="password" type="password" class="border p-2 rounded" />
    <button class="bg-indigo-600 text-white rounded p-2">Log in</button>
  </form> -->

  <!-- <TheFooter /> -->
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue'
import { useAuth } from '@/stores/useAuth'
import { useSocket } from '@/lib/socket'

export default defineComponent({

  setup() {
    // ①  All reactive/stateful logic goes *inside* setup()
    const username = ref('')
    const password = ref('')

    const auth = useAuth()
    const { connect } = useSocket()

    async function submit() {
      await auth.login(username.value, password.value)
      connect()
    }

    // ②  Return everything the template needs
    return { username, password, submit }
  },
})
</script>
