# Browser Push Notifications Feature

**Feature:** Notify Users When Story Generation Completes  
**Created:** 2026-03-22  
**Status:** 🔵 PLANNING  
**Estimated Time:** 6-10 hours (varies by approach)

---

## Overview

Send browser push notifications to users when their story completes, allowing them to navigate away or use other tabs while waiting for the 2-3 minute generation process.

**Use Case:**
- User starts story generation (2-3 min with illustrations)
- User switches tabs or minimizes browser
- Story completes → Browser notification appears
- User clicks notification → Returns to completed story

---

## Current Behavior

**User Experience:**
- Must stay on generation page and watch progress orb
- If user navigates away, they don't know when story is ready
- Have to manually check back or refresh
- No indication story is complete if in another tab

**Pain Points:**
- 2-3 minute wait feels longer without ability to multitask
- Users might forget they started generation
- No way to know when to come back
- Frustrating UX for impatient kids/parents

---

## Research Findings

### Browser Support (2026)

**Desktop:**
- ✅ Chrome/Edge: Full support since 2015
- ✅ Firefox: Full support
- ✅ Safari 16+: Full support (macOS Ventura+)

**Mobile:**
- ✅ Android Chrome: Full support since 2015
- ✅ iOS Safari 16.4+: **Requires PWA installation** (Add to Home Screen)
- ✅ Samsung Internet, Opera: Full support

**Key Limitation:** iOS requires the app to be installed as PWA (not just open tab)

### Technology Stack

**Core APIs:**
- **Service Worker** - Background script that receives push events
- **Push API** - `PushManager.subscribe()` for creating subscriptions
- **Notifications API** - `Notification.requestPermission()` and `showNotification()`
- **VAPID Keys** - Voluntary Application Server Identification for authentication

**Architecture:**
```
Browser                    Service Worker              Backend
   ↓                            ↓                         ↓
1. Request permission    →  Register SW              
2. Subscribe to push     →  Create subscription      
3. Send subscription     ────────────────────────→  Store in DB
                                                    
                        ← Push message sent ←────  4. Story completes
5. Show notification     ←  'push' event fires
6. Click notification    →  'notificationclick'
7. Open story page       →  Navigate to /story/{id}
```

---

## Implementation Options

### Option A: Simple Notification API (No Service Worker)

**Approach:** Use basic Notification API when user is on the page.

**Pros:**
- ✅ Very simple (2-3 hours)
- ✅ No service worker needed
- ✅ No backend push infrastructure
- ✅ Works immediately
- ✅ No VAPID keys needed

**Cons:**
- ❌ Only works if browser tab is still open
- ❌ Doesn't work if user navigates away
- ❌ Doesn't work if browser is minimized/background
- ❌ Not a true "push" notification

**Implementation:**
```typescript
// When story completes (in polling callback):
if (Notification.permission === 'granted') {
    new Notification('Your Story is Ready! 📖', {
        body: storyTitle,
        icon: '/logo.png',
        badge: '/badge.png',
        tag: 'story-complete',
        requireInteraction: false
    });
}
```

**Estimated Time:** 2-3 hours  
**Best For:** Quick win, minimal effort

---

### Option B: Service Worker + Self-Hosted Push (Full Control)

**Approach:** Implement complete Web Push API with service worker and backend push endpoint.

**Pros:**
- ✅ Works even if tab closed/navigated away
- ✅ Full control over push infrastructure
- ✅ No third-party dependencies
- ✅ Works on Android, desktop, iOS PWA
- ✅ Privacy-friendly (no external services)

**Cons:**
- ❌ Complex setup (service worker, VAPID keys, subscriptions)
- ❌ Requires backend push endpoint
- ❌ iOS requires PWA installation
- ❌ Need to manage subscription database
- ❌ VAPID key management

**Architecture:**

**Frontend:**
1. Register service worker (`public/sw.js`)
2. Request notification permission
3. Subscribe to push (get PushSubscription object)
4. Send subscription to backend (`POST /api/push/subscribe`)
5. Service worker listens for 'push' events

**Backend:**
1. Store push subscriptions (new DB table)
2. Generate VAPID keys (one-time setup)
3. When story completes, send push to subscription
4. Use `web-push` library (Node.js) or `pywebpush` (Python)

**Implementation Complexity:**

**Backend:**
- New DB table: `push_subscriptions` (endpoint, keys, user_agent)
- New endpoint: `POST /api/push/subscribe` (save subscription)
- New endpoint: `POST /api/push/unsubscribe` (remove subscription)
- Install: `pywebpush==2.0.1`
- Generate VAPID keys: `python -c "from pywebpush import webpush; print(webpush.Vapid().generate_keys())"`
- Send push when story completes:
  ```python
  from pywebpush import webpush, WebPushException
  
  # In run_pipeline after story completes:
  subscription = get_push_subscription_for_job(job_id)
  if subscription:
      webpush(
          subscription_info=subscription,
          data=json.dumps({
              "title": "Your Story is Ready! 📖",
              "body": final_state["title"],
              "url": f"/story/{job_id}"
          }),
          vapid_private_key=settings.vapid_private_key,
          vapid_claims={"sub": "mailto:noreply@taleweaver.app"}
      )
  ```

**Frontend:**
- Create `public/sw.js` service worker
- Register on app load
- Request permission (button in settings or on first visit)
- Subscribe to push and send to backend
- Handle notification clicks (navigate to story)

**Estimated Time:** 8-10 hours  
**Best For:** Best UX, works offline, full control

---

### Option C: Hybrid Approach (Recommended)

**Approach:** Start with simple notifications (Option A), add service worker later if needed.

**Phase 1 (Immediate):**
- Use Notification API for tab-open notifications
- Show notification when story completes if user still on page
- 2-3 hours

**Phase 2 (Future):**
- Add service worker + push API
- Enable true push for users who navigate away
- 8-10 hours additional

**Pros:**
- ✅ Quick win now (Phase 1)
- ✅ Can enhance later (Phase 2)
- ✅ Progressive enhancement
- ✅ Lower initial investment

**Cons:**
- ❌ Phase 1 doesn't solve "navigated away" case
- ❌ Two implementation cycles

**Estimated Time:** 2-3 hours (Phase 1), +8-10 hours (Phase 2)  
**Best For:** Iterative approach, prove value first

---

### Option D: Third-Party Service (OneSignal, PushEngage)

**Approach:** Use existing push notification service.

**Providers:**
- OneSignal (free tier available, popular)
- PushEngage (PWA-focused)
- Firebase Cloud Messaging (Google)

**Pros:**
- ✅ Faster implementation (4-5 hours)
- ✅ Handles service worker management
- ✅ iOS PWA support included
- ✅ Delivery analytics/tracking
- ✅ Subscription management handled
- ✅ Works across all browsers

**Cons:**
- ❌ Third-party dependency
- ❌ Privacy concerns (user data sent to third party)
- ❌ Potential costs at scale
- ❌ Less control
- ❌ Vendor lock-in

**OneSignal Example:**
```typescript
// Install OneSignal SDK
npm install react-onesignal

// Initialize on app load
import OneSignal from 'react-onesignal';

useEffect(() => {
    OneSignal.init({
        appId: 'YOUR_ONESIGNAL_APP_ID',
    });
}, []);

// When story completes:
OneSignal.sendSelfNotification(
    'Your Story is Ready! 📖',
    storyTitle,
    `/story/${jobId}`
);
```

**Estimated Time:** 4-5 hours  
**Best For:** Quick implementation, analytics needed

---

## Recommended Approach: Option C (Hybrid)

### Phase 1: Simple Notifications (Implement First)

**Effort:** 2-3 hours  
**Works:** If tab is open (covers 80% of use cases)  
**Complexity:** Low

#### Implementation Tasks

**1. Request Notification Permission**
- [ ] Add permission request on first story generation
- [ ] Show friendly prompt explaining benefit
- [ ] Store permission status in localStorage
- [ ] Don't ask again if denied

**2. Show Notification on Completion**
- [ ] In StoryRoute polling callback, detect completion
- [ ] Check Notification.permission === 'granted'
- [ ] Create notification with story title
- [ ] Add click handler to focus window and navigate

**3. Handle Notification Click**
- [ ] Listen for notification click
- [ ] Focus browser window
- [ ] Ensure story page is visible

**Code:**
```typescript
// StoryRoute.tsx

// Request permission on mount (if not already asked)
useEffect(() => {
    const asked = localStorage.getItem('notification_permission_asked');
    if (!asked && 'Notification' in window) {
        // Show friendly prompt
        setShowNotificationPrompt(true);
    }
}, []);

const requestNotificationPermission = async () => {
    if ('Notification' in window) {
        const permission = await Notification.requestPermission();
        localStorage.setItem('notification_permission_asked', 'true');
        setShowNotificationPrompt(false);
        return permission === 'granted';
    }
    return false;
};

// In polling callback when story completes:
if (status.status === "complete" && "title" in status) {
    // Show notification if permission granted
    if (Notification.permission === 'granted') {
        const notification = new Notification('Your Story is Ready! 📖', {
            body: status.title,
            icon: '/logo-192.png',
            badge: '/badge-72.png',
            tag: `story-${id}`,
            requireInteraction: false,
            data: { url: `/story/${id}` }
        });
        
        notification.onclick = () => {
            window.focus();
            notification.close();
        };
    }
    
    // Continue with normal completion flow...
}
```

**Files Modified:**
- `frontend/src/routes/StoryRoute.tsx` - Permission request + notification
- `frontend/src/components/NotificationPrompt.tsx` - NEW (friendly permission UI)
- `public/logo-192.png` - Notification icon (may already exist)
- `public/badge-72.png` - NEW (badge icon for notification)

---

### Phase 2: Service Worker Push (Future Enhancement)

**Effort:** 8-10 hours  
**Works:** Even if tab closed/navigated away  
**Complexity:** High

#### Implementation Tasks

**Backend:**

**1. Add Push Subscription Storage**
- [ ] Create `push_subscriptions` table:
  ```sql
  CREATE TABLE push_subscriptions (
      id TEXT PRIMARY KEY,
      job_id TEXT,  -- Link to story generation job
      endpoint TEXT NOT NULL,
      p256dh_key TEXT NOT NULL,  -- Encryption key
      auth_key TEXT NOT NULL,     -- Auth secret
      user_agent TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
  ```
- [ ] Add CRUD functions for subscriptions

**2. Generate VAPID Keys**
- [ ] Install `pywebpush==2.0.1`
- [ ] Generate VAPID keys once:
  ```bash
  python3 -c "from pywebpush import Vapid; v = Vapid(); v.generate_keys(); print('Public:', v.public_key); print('Private:', v.private_key)"
  ```
- [ ] Store in environment variables:
  ```
  VAPID_PUBLIC_KEY=your-public-key
  VAPID_PRIVATE_KEY=your-private-key
  VAPID_SUBJECT=mailto:noreply@taleweaver.app
  ```

**3. Add Push Endpoints**
- [ ] `POST /api/push/subscribe` - Save subscription linked to job_id
  ```python
  @app.post("/api/push/subscribe")
  async def subscribe_to_push(subscription: PushSubscriptionRequest):
      # subscription contains: endpoint, keys (p256dh, auth), job_id
      save_push_subscription(subscription)
      return {"status": "subscribed"}
  ```
- [ ] `POST /api/push/unsubscribe` - Remove subscription
- [ ] `GET /api/push/vapid-public-key` - Return public key for frontend

**4. Send Push on Story Completion**
- [ ] In run_pipeline, after story completes:
  ```python
  subscription = get_push_subscription_for_job(job_id)
  if subscription:
      try:
          webpush(
              subscription_info={
                  "endpoint": subscription.endpoint,
                  "keys": {
                      "p256dh": subscription.p256dh_key,
                      "auth": subscription.auth_key
                  }
              },
              data=json.dumps({
                  "title": "Your Story is Ready! 📖",
                  "body": final_state["title"],
                  "icon": "/logo-192.png",
                  "badge": "/badge-72.png",
                  "url": f"/story/{job_id}"
              }),
              vapid_private_key=settings.vapid_private_key,
              vapid_claims={
                  "sub": settings.vapid_subject
              }
          )
          logger.info(f"Push notification sent for job {job_id}")
      except WebPushException as e:
          logger.error(f"Push notification failed: {e}")
          # Delete expired subscription
          if e.response.status_code in [404, 410]:
              delete_push_subscription(subscription.id)
  ```
- [ ] Clean up subscription after notification sent

**Frontend:**

**5. Create Service Worker**
- [ ] Create `public/sw.js`:
  ```javascript
  self.addEventListener('push', (event) => {
      const data = event.data ? event.data.json() : {};
      
      const options = {
          body: data.body || 'Your story is ready!',
          icon: data.icon || '/logo-192.png',
          badge: data.badge || '/badge-72.png',
          data: { url: data.url },
          tag: 'story-complete',
          requireInteraction: false,
      };
      
      event.waitUntil(
          self.registration.showNotification(
              data.title || 'Story Complete',
              options
          )
      );
  });
  
  self.addEventListener('notificationclick', (event) => {
      event.notification.close();
      
      const url = event.notification.data.url || '/';
      event.waitUntil(
          clients.openWindow(url)
      );
  });
  ```

**6. Register Service Worker**
- [ ] Register on app load (App.tsx or main entry):
  ```typescript
  useEffect(() => {
      if ('serviceWorker' in navigator) {
          navigator.serviceWorker.register('/sw.js')
              .then(registration => {
                  console.log('Service Worker registered:', registration);
              })
              .catch(error => {
                  console.error('Service Worker registration failed:', error);
              });
      }
  }, []);
  ```

**7. Subscribe to Push**
- [ ] Fetch VAPID public key from backend
- [ ] Create push subscription:
  ```typescript
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
  });
  ```
- [ ] Send subscription to backend with job_id
- [ ] Do this when starting story generation

**8. Add Web App Manifest**
- [ ] Create/update `public/manifest.json`:
  ```json
  {
      "name": "Taleweaver",
      "short_name": "Taleweaver",
      "display": "standalone",
      "start_url": "/",
      "scope": "/",
      "theme_color": "#7c3aed",
      "background_color": "#0f0820",
      "icons": [
          {
              "src": "/logo-192.png",
              "sizes": "192x192",
              "type": "image/png"
          },
          {
              "src": "/logo-512.png",
              "sizes": "512x512",
              "type": "image/png"
          }
      ]
  }
  ```
- [ ] Link in index.html: `<link rel="manifest" href="/manifest.json">`

**Files to Create/Modify:**

**Backend:**
- `backend/app/db/models.py` - PushSubscription model
- `backend/app/db/crud.py` - Push subscription CRUD
- `backend/app/routes/push.py` - NEW push endpoints
- `backend/app/routes/story.py` - Send push on completion
- `backend/requirements.txt` - Add pywebpush
- `backend/.env.example` - Add VAPID keys

**Frontend:**
- `public/sw.js` - NEW service worker
- `public/manifest.json` - NEW or update existing
- `frontend/src/hooks/usePushNotifications.ts` - NEW hook
- `frontend/src/components/NotificationPrompt.tsx` - NEW permission UI
- `frontend/src/App.tsx` - Register service worker
- `frontend/src/routes/StoryRoute.tsx` - Subscribe on generation start

**Estimated Time:** 8-10 hours  
**Best For:** Full-featured solution, best UX

---

### Option C: Page Visibility API (Lightweight Alternative)

**Approach:** Detect when user returns to tab and show in-app notification.

**Pros:**
- ✅ Very simple (1-2 hours)
- ✅ No service worker
- ✅ No backend changes
- ✅ Works on all browsers
- ✅ In-app banner is less intrusive

**Cons:**
- ❌ Requires user to return to tab manually
- ❌ No browser notification
- ❌ Doesn't solve "forgot about it" problem

**Implementation:**
```typescript
// In StoryRoute, detect page visibility
useEffect(() => {
    const handleVisibilityChange = () => {
        if (!document.hidden && storyCompleted && !notificationShown) {
            // Show in-app banner/modal
            setShowCompletionBanner(true);
            setNotificationShown(true);
        }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
}, [storyCompleted, notificationShown]);
```

**Estimated Time:** 1-2 hours  
**Best For:** Minimal viable solution

---

## Comparison Matrix

| Feature | Option A (Simple) | Option B (Full Push) | Option C (Visibility) | Option D (3rd Party) |
|---------|-------------------|----------------------|-----------------------|---------------------|
| **Works if tab closed** | ❌ | ✅ | ❌ | ✅ |
| **Works if navigated away** | ❌ | ✅ | ❌ | ✅ |
| **iOS Support** | ✅ (tab open) | ⚠️ (PWA only) | ✅ | ⚠️ (PWA only) |
| **Service Worker** | ❌ | ✅ Required | ❌ | ✅ (Managed) |
| **Backend Changes** | ❌ | ✅ Major | ❌ | ⚠️ Minor |
| **Complexity** | Low | High | Very Low | Medium |
| **Privacy** | ✅ Perfect | ✅ Good | ✅ Perfect | ⚠️ Third-party |
| **Cost** | Free | Free | Free | Free-$$ |
| **Time Estimate** | 2-3h | 8-10h | 1-2h | 4-5h |
| **Maintenance** | None | Medium | None | Low |

---

## Recommended Implementation Plan

### Immediate: Option A (Simple Notifications)

**Why:**
- Solves 80% of the problem (most users keep tab open)
- Quick to implement (2-3 hours)
- No infrastructure changes
- Can always upgrade later

**Implementation:**

**Step 1: Request Permission (Friendly UX)**
```typescript
// Show after first story generation completes
const showNotificationPermission = () => {
    if ('Notification' in window && Notification.permission === 'default') {
        return (
            <motion.div className="glass-card p-4 mb-4">
                <p className="text-starlight mb-2">
                    🔔 Get notified when your stories are ready?
                </p>
                <button onClick={handleEnableNotifications} className="btn-glow text-sm">
                    Enable Notifications
                </button>
            </motion.div>
        );
    }
};
```

**Step 2: Show Notification on Completion**
```typescript
const showCompletionNotification = (title: string, jobId: string) => {
    if (Notification.permission === 'granted') {
        const notification = new Notification('Your Story is Ready! 📖', {
            body: title,
            icon: '/logo-192.png',
            tag: `story-${jobId}`,
            requireInteraction: false
        });
        
        notification.onclick = () => {
            window.focus();
            notification.close();
        };
        
        // Auto-close after 10 seconds
        setTimeout(() => notification.close(), 10000);
    }
};
```

**Step 3: Integrate into Story Generation Flow**
- [ ] In StoryRoute polling callback
- [ ] When status === "complete"
- [ ] Call showCompletionNotification()

**Testing:**
- [ ] Test on Chrome/Edge (desktop)
- [ ] Test on Firefox
- [ ] Test on Safari 16+
- [ ] Test permission denied case
- [ ] Test permission granted case
- [ ] Test notification click behavior

---

### Future: Option B (Service Worker Push)

**When to implement:**
- User feedback indicates need for offline notifications
- Significant % of users navigate away during generation
- Ready to invest in PWA features

**Prerequisites:**
- Option A implemented and tested
- HTTPS in production (already have ✅)
- VAPID keys generated
- Push subscription database table

---

## Privacy & UX Considerations

### Permission Request Best Practices

**DON'T:**
- ❌ Request permission immediately on first visit
- ❌ Show browser's default ugly permission dialog without context
- ❌ Ask repeatedly if user denies

**DO:**
- ✅ Explain the benefit first ("Get notified when your story is ready")
- ✅ Show custom UI explaining feature
- ✅ Request after user starts their first story (contextual)
- ✅ Respect user's choice (don't ask again if denied)
- ✅ Provide way to disable in settings

### GDPR/Privacy

**Considerations:**
- Notification permission is opt-in ✅
- No personal data in push subscriptions (just endpoint URLs)
- Can implement without tracking individual users
- Should have privacy policy mention

---

## Success Metrics

**Phase 1 (Simple Notifications):**
- [ ] X% of users grant notification permission
- [ ] Users report knowing when story is ready
- [ ] Reduced support questions about "how long does it take"

**Phase 2 (Service Worker Push):**
- [ ] Push delivery rate >90%
- [ ] Notification click-through rate >30%
- [ ] User satisfaction with feature

---

## Testing Strategy

### Desktop Testing
```bash
# Chrome DevTools → Application → Service Workers
# Firefox → about:debugging → Service Workers
# Safari → Develop → Service Workers

# Test notifications:
1. Grant permission
2. Generate story
3. Switch to another tab
4. Wait for completion
5. Verify notification appears
6. Click notification
7. Verify navigation to story
```

### Mobile Testing
```bash
# Android Chrome: Works out of box
# iOS Safari: Requires PWA installation

# iOS Testing:
1. Safari → Share → Add to Home Screen
2. Open PWA from home screen
3. Generate story
4. Close app
5. Wait for notification
6. Tap notification
7. Verify app opens to story
```

---

## Implementation Recommendation

**Start with Option A (Simple Notifications):**

1. **Immediate value** with minimal effort (2-3 hours)
2. **Covers majority use case** (users keep tab open)
3. **No infrastructure complexity**
4. **Can gather feedback** before investing in service worker
5. **Easy to enhance later** (progressive enhancement)

**Upgrade to Option B later if:**
- User feedback shows need for offline notifications
- Significant users navigate away during generation
- Ready to become a PWA
- Have time to invest in full push infrastructure

---

## Next Steps

1. Review this plan and choose approach
2. If Option A: Implement simple notifications (2-3 hours)
3. If Option B: Start with backend push infrastructure
4. Create icons (logo-192.png, badge-72.png) if needed
5. Test across browsers
6. Monitor user adoption of notification permission

---

**Recommended:** Start with **Option A** (Simple Notifications) - 2-3 hours  
**Future Enhancement:** **Option B** (Service Worker Push) - 8-10 hours

Both approaches documented above with complete implementation details.
