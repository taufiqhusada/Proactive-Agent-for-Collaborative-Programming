import axios from 'axios'
import { useAuth } from '@/stores/useAuth'

interface RunResponse {
  stdout: string
  stderr: string
}

export async function runCode(code: string): Promise<RunResponse> {
  const auth = useAuth()
  const url = `${import.meta.env.VITE_API_URL}/api/run`

  const { data } = await axios.post<RunResponse>(
    url,
    { lang: 'python', code },
    { headers: { Authorization: `Bearer ${auth.token}` } }
  )
  return data
}
