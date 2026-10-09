const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const dotenv = require('dotenv');
const root = path.resolve(__dirname, '..');
const context = path.join(__dirname, 'build-context');
fs.mkdirSync(context, { recursive: true });
const excluded = new Set(['node_modules', 'dist', 'logs', '__pycache__', 'data', 'coverage', '.cache']);
for (const name of ['api', 'client', 'packages', 'config']) {
  const target = path.join(context, name);
  fs.rmSync(target, { recursive: true, force: true });
  fs.cpSync(path.join(root, name), target, {
    recursive: true,
    filter: source => !excluded.has(path.basename(source)) && !path.basename(source).startsWith('.env') && !source.endsWith('.log'),
  });
}
for (const name of ['package.json', 'package-lock.json']) fs.copyFileSync(path.join(root, name), path.join(context, name));
fs.copyFileSync(path.join(__dirname, 'Dockerfile'), path.join(context, 'Dockerfile'));
const secretPath = path.join(__dirname, 'secrets.json');
if (!fs.existsSync(secretPath)) fs.writeFileSync(secretPath, JSON.stringify(Object.fromEntries(['JWT_SECRET', 'JWT_REFRESH_SECRET', 'CREDS_KEY', 'CREDS_IV'].map(k => [k, crypto.randomBytes(k === 'CREDS_IV' ? 16 : 32).toString('hex')]))), { mode: 0o600 });
const env = dotenv.parse(fs.readFileSync(path.join(root, '.env')));
Object.assign(env, JSON.parse(fs.readFileSync(secretPath)), {
  HOST: '0.0.0.0', PORT: '3080', NODE_ENV: 'production',
  DOMAIN_CLIENT: 'http://localhost:3080', DOMAIN_SERVER: 'http://localhost:3080',
  MONGO_URI: 'mongodb://mongodb:27017/LibreChat',
  MEILI_HOST: 'http://meilisearch:7700', MEILI_MASTER_KEY: 'mygpt2-local-search-key',
  ALLOW_EMAIL_LOGIN: 'true', ALLOW_REGISTRATION: 'true',
  ALLOW_SOCIAL_LOGIN: 'false', ALLOW_SOCIAL_REGISTRATION: 'false',
  ALLOW_UNVERIFIED_EMAIL_LOGIN: 'true',
  LIBRECHAT_CODE_BASEURL: 'http://host.docker.internal:8080/v1/librechat',
  RAG_API_URL: 'http://rag_api:8000', CONFIG_PATH: '/app/librechat.yaml',
});
for (const key of Object.keys(env)) if (/^(OPENID_|SMTP_|EMAIL_)/.test(key)) delete env[key];
const envPath = path.join(__dirname, 'runtime.env');
fs.writeFileSync(envPath, Object.entries(env).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join('\n') + '\n', { mode: 0o600 });
fs.chmodSync(envPath, 0o600);
console.log('Prepared current source and private local environment for Docker Compose.');
