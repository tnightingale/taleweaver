import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getCachedUser, getCurrentUser, login, signup, logout } from './auth';

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

const storageMap = new Map<string, string>();
const mockLocalStorage = {
  getItem: vi.fn((key: string) => storageMap.get(key) ?? null),
  setItem: vi.fn((key: string, value: string) => storageMap.set(key, value)),
  removeItem: vi.fn((key: string) => storageMap.delete(key)),
};
Object.defineProperty(globalThis, 'localStorage', { value: mockLocalStorage });

beforeEach(() => {
  mockFetch.mockReset();
  storageMap.clear();
  vi.clearAllMocks();
});

function okResponse(data: unknown) {
  return { ok: true, status: 200, json: () => Promise.resolve(data) };
}

const testUser = { id: 'u1', email: 'tom@test.com', display_name: 'Tom' };

describe('auth localStorage caching', () => {
  it('getCurrentUser caches user in localStorage on success', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(testUser));
    const user = await getCurrentUser();
    expect(user).toEqual(testUser);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
      'tw-user',
      JSON.stringify(testUser),
    );
  });

  it('getCurrentUser returns null on 401 without caching', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401 });
    const user = await getCurrentUser();
    expect(user).toBeNull();
    expect(mockLocalStorage.setItem).not.toHaveBeenCalled();
  });

  it('login caches user in localStorage', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(testUser));
    const user = await login('tom@test.com', 'password');
    expect(user).toEqual(testUser);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
      'tw-user',
      JSON.stringify(testUser),
    );
  });

  it('signup caches user in localStorage', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(testUser));
    const user = await signup('tom@test.com', 'password', 'Tom', 'invite123');
    expect(user).toEqual(testUser);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
      'tw-user',
      JSON.stringify(testUser),
    );
  });

  it('logout clears cached user', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true });
    await logout();
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('tw-user');
  });

  it('getCachedUser returns cached user from localStorage', () => {
    storageMap.set('tw-user', JSON.stringify(testUser));
    expect(getCachedUser()).toEqual(testUser);
  });

  it('getCachedUser returns null when nothing cached', () => {
    expect(getCachedUser()).toBeNull();
  });

  it('getCachedUser returns null on corrupted data', () => {
    storageMap.set('tw-user', 'not-json');
    expect(getCachedUser()).toBeNull();
  });
});
