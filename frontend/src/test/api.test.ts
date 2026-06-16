import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { taskApi, authApi } from '../services/api'

vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  }
  return { default: mockAxios }
})

const mockedAxios = vi.mocked(axios.create())

describe('taskApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('creates a task', async () => {
    const mockResponse = { data: { task_id: 'abc123', status: 'pending', message: 'Created' } }
    mockedAxios.post.mockResolvedValueOnce(mockResponse)

    const result = await taskApi.create('Analyze AAPL stock')

    expect(mockedAxios.post).toHaveBeenCalledWith('/task/create', {
      query: 'Analyze AAPL stock',
      priority: 1,
    })
    expect(result).toEqual(mockResponse.data)
  })

  it('gets task status', async () => {
    const mockResponse = {
      data: {
        task_id: 'abc123',
        status: 'running',
        progress: 50,
        current_stage: 'executing',
        message: 'Running',
      },
    }
    mockedAxios.get.mockResolvedValueOnce(mockResponse)

    const result = await taskApi.getStatus('abc123')

    expect(mockedAxios.get).toHaveBeenCalledWith('/task/abc123/status')
    expect(result.status).toBe('running')
    expect(result.progress).toBe(50)
  })

  it('lists tasks', async () => {
    const mockResponse = {
      data: {
        tasks: [
          { task_id: '1', query: 'test', status: 'completed', created_at: '', updated_at: '' },
        ],
      },
    }
    mockedAxios.get.mockResolvedValueOnce(mockResponse)

    const result = await taskApi.list()

    expect(result.tasks).toHaveLength(1)
    expect(result.tasks[0].task_id).toBe('1')
  })
})

describe('authApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('registers a user', async () => {
    const mockResponse = {
      data: {
        access_token: 'jwt-token',
        token_type: 'bearer',
        expires_in: 86400,
        user: { id: 1, username: 'test', email: 'test@test.com', is_active: true, created_at: '' },
      },
    }
    mockedAxios.post.mockResolvedValueOnce(mockResponse)

    const result = await authApi.register({ username: 'test', email: 'test@test.com', password: 'pass1234' })

    expect(mockedAxios.post).toHaveBeenCalledWith('/auth/register', {
      username: 'test',
      email: 'test@test.com',
      password: 'pass1234',
    })
    expect(result.access_token).toBe('jwt-token')
  })

  it('logs in a user', async () => {
    const mockResponse = {
      data: {
        access_token: 'jwt-token',
        token_type: 'bearer',
        expires_in: 86400,
        user: { id: 1, username: 'test', email: 'test@test.com', is_active: true, created_at: '' },
      },
    }
    mockedAxios.post.mockResolvedValueOnce(mockResponse)

    const result = await authApi.login({ username: 'test', password: 'pass1234' })

    expect(result.access_token).toBe('jwt-token')
  })

  it('gets current user', async () => {
    const mockResponse = {
      data: { id: 1, username: 'test', email: 'test@test.com', is_active: true, created_at: '' },
    }
    mockedAxios.get.mockResolvedValueOnce(mockResponse)

    const result = await authApi.getMe()

    expect(result.username).toBe('test')
  })
})
