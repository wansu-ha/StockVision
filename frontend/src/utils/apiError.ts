/** Axios 에러에서 서버 detail 메시지를 추출한다. */
import { isAxiosError } from 'axios'

export function getApiError(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    return err.response?.data?.detail ?? fallback
  }
  return fallback
}
