<template>
  <!-- full‑height column -->
  <div class="flex flex-col h-full">
    <!-- editor takes all available space -->
    <vue-monaco-editor
      v-model:value="code"
      theme="vs-dark"
      class="flex-grow w-full"
      :options="{ automaticLayout: true }"
      @keydown="broadcast"
    />

    <!-- optional output / controls -->
    <div class="p-2 border-t">
      <button @click="execute" class="bg-green-600 text-white px-3 py-1 rounded">
        Run ▶︎
      </button>
      <pre class="mt-2 max-h-40 overflow-auto">{{ output }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { useSocket } from '@/lib/socket'
import { runCode } from '@/lib/runCode'

const route = useRoute()
const roomId = String(route.params.roomId)      // "room123" from the router push
const code   = ref<string>('print("Hello")')
const output = ref<string>('')

const { socket } = useSocket()

socket.on('update', ({ delta }) => {
  code.value = delta as string
})

function broadcast() {
  socket.emit('update', { room: roomId, delta: code.value })
}

async function execute() {
  const res = await runCode(code.value)
  output.value = res.stderr || res.stdout || 'no output'
}

onMounted(() => {
  socket.emit('join', { room: roomId })
})
</script>
