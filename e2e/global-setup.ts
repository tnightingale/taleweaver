/**
 * Playwright global setup: seed a test user into the running app container.
 *
 * Finds the taleweaver container via `docker compose` or `docker ps`,
 * then execs a Python snippet to create a test user with known credentials.
 */
import { execSync } from 'child_process';
import { writeFileSync } from 'fs';
import path from 'path';

export const TEST_EMAIL = 'e2e-test@taleweaver.local';
export const TEST_PASSWORD = 'e2e-test-password';
export const AUTH_FILE = path.join(__dirname, '.test-auth.json');

function findContainer(): string {
  // Try docker compose first (from repo root)
  try {
    const cid = execSync('docker compose ps -q app 2>/dev/null', {
      cwd: path.join(__dirname, '..'),
    }).toString().trim();
    if (cid) return cid;
  } catch { /* ignore */ }

  // Fallback: find by image name
  const cid = execSync(
    'docker ps --filter "ancestor=ghcr.io/tnightingale/taleweaver" --format "{{.ID}}" | head -1'
  ).toString().trim();

  if (!cid) {
    // Try any taleweaver container
    const cid2 = execSync(
      'docker ps --filter "name=taleweaver" --format "{{.ID}}" | head -1'
    ).toString().trim();
    if (cid2) return cid2;
    throw new Error('No taleweaver container found. Run: docker compose up app');
  }
  return cid;
}

export default async function globalSetup() {
  const cid = findContainer();
  console.log(`[e2e setup] Using container: ${cid}`);

  // Create test user (idempotent — skips if exists)
  const seedScript = `
import sys, uuid
sys.path.insert(0, '/app')
from app.db.database import get_db
from app.db.models import User
from app.auth.passwords import hash_password

db = next(get_db())
try:
    existing = db.query(User).filter(User.email == '${TEST_EMAIL}').first()
    if existing:
        print(f'exists:{existing.id}')
    else:
        user = User(
            id=str(uuid.uuid4()),
            email='${TEST_EMAIL}',
            password_hash=hash_password('${TEST_PASSWORD}'),
            display_name='E2E Test',
        )
        db.add(user)
        db.commit()
        print(f'created:{user.id}')
finally:
    db.close()
`.trim();

  const result = execSync(`docker exec ${cid} python -c "${seedScript.replace(/"/g, '\\"')}"`, {
    encoding: 'utf-8',
  }).trim();
  console.log(`[e2e setup] Test user: ${result}`);

  // Write credentials for tests
  writeFileSync(AUTH_FILE, JSON.stringify({
    email: TEST_EMAIL,
    password: TEST_PASSWORD,
    containerId: cid,
  }));
}
