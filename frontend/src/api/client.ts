import type { ApiClient } from '../types'
import { mockApi } from './mock'
import { realApi } from './realApi'

// Mocks are on by default. Set VITE_USE_MOCKS=false in the root .env once api/agent are running.
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false'

export const api: ApiClient = USE_MOCKS ? mockApi : realApi
