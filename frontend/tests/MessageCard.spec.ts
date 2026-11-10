import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import MessageCard from '@/components/MessageCard.vue'
import type { ShareMessage } from '@/types'

describe('MessageCard Component', () => {
  beforeEach(() => setActivePinia(createPinia()))
  const sampleMessage: ShareMessage = {
    id: 'smsg_test_1',
    article_id: 'art_1',
    title: '테스트용 아키텍처 브리핑',
    body: '[모아톡 브리핑] 요약 내용입니다.\n\n🔗 https://news.example.com/post/1',
    target_url: 'https://news.example.com/post/1',
    source_name: '테크 브리핑',
    status: 'pending',
    kakao_shared: false,
    created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(), // 15 mins ago
    updated_at: new Date(Date.now() - 1000 * 60 * 15).toISOString()
  }

  it('renders title, source name, status, and creation time', () => {
    const wrapper = mount(MessageCard, {
      props: {
        message: sampleMessage
      }
    })

    // 1. Title
    expect(wrapper.find('.card-title').text()).toBe('테스트용 아키텍처 브리핑')

    // 2. Source
    expect(wrapper.find('.source-badge').text()).toContain('테크 브리핑')

    // 3. Status
    expect(wrapper.find('.status-badge').text()).toBe('공유 대기')
    expect(wrapper.find('.status-badge').classes()).toContain('badge-pending')

    // 4. Creation time
    const timeEl = wrapper.find('time.card-time')
    expect(timeEl.exists()).toBe(true)
    expect(timeEl.text()).toContain('15분 전')
  })

  it('falls back to domain name when source_name is omitted', () => {
    const noSourceNameMessage: ShareMessage = {
      ...sampleMessage,
      source_name: undefined,
      items: undefined,
      target_url: 'https://blog.techflow.io/item/99'
    }

    const wrapper = mount(MessageCard, {
      props: {
        message: noSourceNameMessage
      }
    })

    expect(wrapper.find('.source-badge').text()).toContain('blog.techflow.io')
  })

  it('emits select event when clicking the card', async () => {
    const wrapper = mount(MessageCard, {
      props: {
        message: sampleMessage
      }
    })

    await wrapper.find('.message-card').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0]).toEqual([sampleMessage])
  })

  it('emits select event when pressing Enter key on the card for accessibility', async () => {
    const wrapper = mount(MessageCard, {
      props: {
        message: sampleMessage
      }
    })

    await wrapper.find('.message-card').trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0]).toEqual([sampleMessage])
  })

  it('emits review event when clicking the quick share button without triggering card select', async () => {
    const wrapper = mount(MessageCard, {
      props: {
        message: sampleMessage
      }
    })

    await wrapper.find('.quick-share-btn').trigger('click')
    expect(wrapper.emitted('review')).toBeTruthy()
    expect(wrapper.emitted('review')![0]).toEqual([sampleMessage])
  })

  it('renders fetch button replacing retry button when message data fetch has failed', () => {
    const failedMessage: ShareMessage = {
      ...sampleMessage,
      status: 'failed',
      fetch_status: 'failed',
      failed_reason: '5회 재시도 초과'
    }

    const wrapper = mount(MessageCard, {
      props: {
        message: failedMessage
      }
    })

    // Status badge shows failed
    expect(wrapper.find('.status-badge').text()).toBe('수집 실패')
    expect(wrapper.find('.status-badge').classes()).toContain('badge-failed')

    // Fetch button is present instead of normal quick-share
    const fetchBtn = wrapper.find('.fetch-btn')
    expect(fetchBtn.exists()).toBe(true)
    expect(fetchBtn.text()).toContain('Fetch')
    expect(wrapper.find('.quick-share-btn').exists()).toBe(false)
  })

  it('emits fetch event when clicking the fetch button on a failed card', async () => {
    const failedMessage: ShareMessage = {
      ...sampleMessage,
      status: 'failed',
      fetch_status: 'failed'
    }

    const wrapper = mount(MessageCard, {
      props: {
        message: failedMessage
      }
    })

    await wrapper.find('.fetch-btn').trigger('click')
    expect(wrapper.emitted('fetch')).toBeTruthy()
    expect(wrapper.emitted('fetch')![0]).toEqual([failedMessage])
  })
})
