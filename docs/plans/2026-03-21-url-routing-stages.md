# URL Routing Implementation - Stages

**Feature:** URL-based navigation with React Router  
**Branch:** `feature/url-routing`  
**Status:** Stage 1 complete (1/4)

## Stage Overview

| Stage | Description | Status | 
|-------|-------------|--------|
| 1 | Setup React Router | ✅ COMPLETE |
| 2 | Convert simple routes (Hero, Library) | 🔄 NEXT |
| 3 | Convert complex routes (Craft, Story) | ⏳ PENDING |
| 4 | Test & Polish | ⏳ PENDING |

---

## Stage 1: Setup ✅ COMPLETE

- ✅ Add react-router-dom dependency
- ✅ Configure BrowserRouter in main.tsx
- ✅ Create StandalonePlayer component
- ✅ Backup App.tsx

**Commits:** 4

---

## Stage 2: Simple Routes (Hero, Library)

Convert stateless screens to routes:
- [ ] Add Routes wrapper to App.tsx
- [ ] Create / route (HeroScreen)
- [ ] Create /library route (LibraryScreen)  
- [ ] Create /s/:shortId route (StandalonePlayer)
- [ ] Update HeroScreen to navigate() instead of callbacks
- [ ] Update LibraryScreen to navigate() instead of callbacks
- [ ] Test: Visit /, /library, /s/abc123 directly

**Target:** ~8 commits, 1 hour

---

## Stage 3: Complex Routes (Craft, Story with state)

Convert stateful screens:
- [ ] Create /craft route with form state
- [ ] Create /story/:jobId route with generation polling
- [ ] Move story creation logic to route handlers
- [ ] Handle session storage for form data only
- [ ] Add migration logic for old sessions
- [ ] Test: Full create flow, refresh mid-generation

**Target:** ~10 commits, 1.5 hours

---

## Stage 4: Test & Polish

- [ ] Test all navigation paths
- [ ] Test browser back button
- [ ] Test refresh behavior
- [ ] Test permalink sharing
- [ ] Build production container
- [ ] Merge to main

**Target:** ~5 commits, 1 hour

