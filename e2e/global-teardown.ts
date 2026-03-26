/**
 * Playwright global teardown: remove the test user from the app container.
 */
import { execSync } from 'child_process';
import { readFileSync, unlinkSync } from 'fs';
import path from 'path';

const AUTH_FILE = path.join(__dirname, '.test-auth.json');

export default async function globalTeardown() {
  let auth: { email: string; containerId: string };
  try {
    auth = JSON.parse(readFileSync(AUTH_FILE, 'utf-8'));
  } catch {
    return; // No auth file — setup didn't run
  }

  try {
    const teardownScript = `
import sys
sys.path.insert(0, '/app')
from app.db.database import get_db
from app.db.models import User, Story

db = next(get_db())
try:
    user = db.query(User).filter(User.email == '${auth.email}').first()
    if user:
        db.query(Story).filter(Story.user_id == user.id).delete()
        db.delete(user)
        db.commit()
        print(f'deleted:{user.id}')
    else:
        print('not_found')
finally:
    db.close()
`.trim();

    const result = execSync(
      `docker exec ${auth.containerId} python -c "${teardownScript.replace(/"/g, '\\"')}"`,
      { encoding: 'utf-8' },
    ).trim();
    console.log(`[e2e teardown] Test user: ${result}`);
  } catch (err) {
    console.warn('[e2e teardown] Cleanup failed:', err);
  }

  try {
    unlinkSync(AUTH_FILE);
  } catch { /* ignore */ }
}
