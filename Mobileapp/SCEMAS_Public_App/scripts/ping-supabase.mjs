import { createClient } from '@supabase/supabase-js';
import fs from 'node:fs';

function readDotEnv(path) {
  const env = {};
  const lines = fs.readFileSync(path, 'utf8').split(/\r?\n/);
  for (const line of lines) {
    if (!line) continue;
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const i = trimmed.indexOf('=');
    if (i === -1) continue;
    const key = trimmed.slice(0, i).trim();
    let value = trimmed.slice(i + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    env[key] = value;
  }
  return env;
}

const table = process.argv[2] ?? 'active_alerts';
const limit = Number(process.argv[3] ?? '1');

const env = readDotEnv('.env');
const url = env.EXPO_PUBLIC_SUPABASE_URL;
const key = env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !key) {
  console.error(
    'Missing env vars in .env: EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_ANON_KEY',
  );
  process.exit(1);
}

const supabase = createClient(url, key);

const { data, error } = await supabase.from(table).select('*').limit(limit);
if (error) {
  console.error(error);
  process.exit(2);
}

console.log(JSON.stringify(data, null, 2));

