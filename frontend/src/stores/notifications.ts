import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getToken, onMessage } from 'firebase/messaging'
import { getFirebaseMessaging } from '@/services/firebase'
import { api } from '@/services/api'
import { useMessagesStore } from './messages'
import { getSafeLocalStorage } from './theme'

const DEVICE_ID_KEY = 'moatok_pwa_device_id'

function getOrCreateDeviceId(): string {
  const storage = getSafeLocalStorage()
  let id = storage.getItem(DEVICE_ID_KEY)
  if (!id) {
    id = `pwa_${Math.random().toString(36).substring(2, 12)}_${Date.now().toString(36)}`
    storage.setItem(DEVICE_ID_KEY, id)
  }
  return id
}

export const useNotificationsStore = defineStore('notifications', () => {
  const permission = ref<NotificationPermission>(
    typeof window !== 'undefined' && 'Notification' in window ? Notification.permission : 'default'
  )
  const token = ref<string | null>(null)
  const deviceId = ref<string>(getOrCreateDeviceId())
  const isSupported = ref<boolean>(typeof window !== 'undefined' && 'Notification' in window && 'serviceWorker' in navigator)
  const isRegistered = ref<boolean>(false)
  const latestNotification = ref<any | null>(null)

  async function requestPermissionAndRegister(): Promise<boolean> {
    if (!isSupported.value) {
      return false
    }

    try {
      const result = await Notification.requestPermission()
      permission.value = result

      if (result !== 'granted') {
        return false
      }

      const messaging = await getFirebaseMessaging()
      if (!messaging) {
        // Fallback for environments where Firebase VAPID key is not set
        token.value = `mock-fcm-token-${deviceId.value}`
        isRegistered.value = true
        return true
      }

      const vapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY
      const currentToken = await getToken(messaging, {
        vapidKey: vapidKey || undefined
      })

      if (currentToken) {
        token.value = currentToken
        await api.registerFcmDevice({
          fcm_token: currentToken,
          device_id: deviceId.value,
          platform: 'web_pwa'
        })
        isRegistered.value = true

        // Listen for foreground push messages
        onMessage(messaging, (payload) => {
          latestNotification.value = payload
          const messagesStore = useMessagesStore()
          messagesStore.fetchAll(true)
        })

        return true
      }
    } catch (err) {
      console.warn('FCM registration encountered an error:', err)
    }

    return false
  }

  return {
    permission,
    token,
    deviceId,
    isSupported,
    isRegistered,
    latestNotification,
    requestPermissionAndRegister
  }
})
