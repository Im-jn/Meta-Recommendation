import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { Chat } from '../ui/Chat'

import {
  addMessage,
  getConversation,
  getTaskStatus,
  recommend,
  recommendStream,
} from '../utils/api'

vi.mock('../utils/api', () => ({
  recommend: vi.fn(),
  recommendStream: vi.fn(),
  getTaskStatus: vi.fn(),
  getConversation: vi.fn(),
  addMessage: vi.fn(),
}))

describe('frontend page: Chat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getConversation).mockResolvedValue({
      id: 'conv-1',
      user_id: 'u-1',
      title: 'Chat',
      model: 'RestRec',
      last_message: '',
      timestamp: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [],
    })
    vi.mocked(addMessage).mockResolvedValue({ success: true, message: 'ok' })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders welcome state and composer', () => {
    render(<Chat selectedTypes={[]} selectedFlavors={[]} />)

    expect(screen.getByText('Welcome to MetaRec.')).toBeInTheDocument()
    expect(
      screen.getByPlaceholderText(/Ask for recommendations/i)
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()
  })

  it('streams llm reply when backend returns llm_reply intent', async () => {
    vi.mocked(recommend).mockResolvedValue({
      restaurants: [],
      llm_reply: 'Sure, let me help.',
      intent: 'chat',
    })
    vi.mocked(recommendStream).mockImplementation(
      async (_q, _u, _h, onChunk, onComplete) => {
        onChunk?.('Hello')
        onChunk?.(' world')
        onComplete?.('Hello world')
        return 'Hello world'
      }
    )

    render(<Chat selectedTypes={[]} selectedFlavors={[]} />)
    fireEvent.change(screen.getByPlaceholderText(/Ask for recommendations/i), {
      target: { value: 'hi there' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(recommend).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(recommendStream).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Hello world')).toBeInTheDocument()
  })

  it('handles confirmation to task polling and renders recommendation result', async () => {
    vi.mocked(recommend)
      .mockResolvedValueOnce({
        restaurants: [],
        confirmation_request: {
          message: 'Please confirm your preferences.',
          preferences: {
            restaurant_types: ['casual'],
            flavor_profiles: ['spicy'],
            dining_purpose: 'friends',
            budget_range: { min: 20, max: 60, currency: 'SGD', per: 'person' },
            location: 'Chinatown',
          },
          needs_confirmation: true,
        },
      })
      .mockResolvedValueOnce({
        restaurants: [],
        thinking_steps: [
          {
            step: 'start_processing',
            description: 'Starting recommendation process...',
            status: 'thinking',
            details: 'Task ID: task-123',
          },
        ],
      })

    vi.mocked(getTaskStatus).mockResolvedValue({
      task_id: 'task-123',
      status: 'completed',
      progress: 100,
      message: 'Recommendations ready!',
      result: {
        restaurants: [
          {
            id: 'r-1',
            name: 'Mock Bistro',
            area: 'Chinatown',
            cuisine: 'Sichuan',
            price_per_person_sgd: '20-30',
            flavor_match: ['Spicy'],
            purpose_match: ['Friends'],
            why: 'Great fit for spicy group dining',
          },
        ],
        thinking_steps: [],
      },
    })

    render(<Chat selectedTypes={[]} selectedFlavors={[]} />)

    fireEvent.change(screen.getByPlaceholderText(/Ask for recommendations/i), {
      target: { value: 'Need spicy dinner for friends' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('Please confirm your preferences.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    await waitFor(() => expect(recommend).toHaveBeenCalledTimes(2))

    await new Promise((resolve) => setTimeout(resolve, 1200))

    await waitFor(() =>
      expect(getTaskStatus).toHaveBeenCalledWith('task-123', undefined, undefined)
    )
    expect(await screen.findByText('Mock Bistro')).toBeInTheDocument()
  }, 10000)
})
