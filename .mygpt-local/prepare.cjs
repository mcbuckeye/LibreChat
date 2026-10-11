const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const dotenv = require('dotenv');

function prepareBuildContext(root, localDir) {
  const context = path.join(localDir, 'build-context');
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
  for (const name of ['package.json', 'package-lock.json', '.npmrc']) fs.copyFileSync(path.join(root, name), path.join(context, name));
  fs.copyFileSync(path.join(localDir, 'Dockerfile'), path.join(context, 'Dockerfile'));
}

function prepareEnvironment(root, localDir) {
  const envPath = path.join(localDir, 'runtime.env');
  // Existing runtime owns SSO, encryption keys, models and deployment settings.
  if (fs.existsSync(envPath)) {
    if (!fs.statSync(envPath).isFile() || fs.lstatSync(envPath).isSymbolicLink()) {
      throw new Error('runtime.env must be a regular private file');
    }
    fs.chmodSync(envPath, 0o600);
    return;
  }
  fs.mkdirSync(localDir, { recursive: true });
  const secretPath = path.join(localDir, 'secrets.json');
  if (!fs.existsSync(secretPath)) fs.writeFileSync(secretPath, JSON.stringify(Object.fromEntries(['JWT_SECRET', 'JWT_REFRESH_SECRET', 'CREDS_KEY', 'CREDS_IV'].map(k => [k, crypto.randomBytes(k === 'CREDS_IV' ? 16 : 32).toString('hex')]))), { mode: 0o600 });
  const localSecrets = JSON.parse(fs.readFileSync(secretPath));
  if (!localSecrets.POSTGRES_PASSWORD) {
    localSecrets.POSTGRES_PASSWORD = crypto.randomBytes(32).toString('hex');
    fs.writeFileSync(secretPath, JSON.stringify(localSecrets), { mode: 0o600 });
  }
  const env = dotenv.parse(fs.readFileSync(process.env.MYGPT_ENV_SOURCE || path.join(root, '.env')));
  Object.assign(env, localSecrets, {
    HOST: '0.0.0.0', PORT: '3080', NODE_ENV: 'production', APP_TITLE: 'MyGPT2',
    SCHEDULES_SINGLE_PROCESS: 'true',
    DOMAIN_CLIENT: 'http://localhost:3081', DOMAIN_SERVER: 'http://localhost:3081',
    MONGO_URI: 'mongodb://mongodb:27017/LibreChat',
    MEILI_HOST: 'http://meilisearch:7700', MEILI_MASTER_KEY: 'mygpt2-local-search-key',
    ALLOW_EMAIL_LOGIN: 'true', ALLOW_REGISTRATION: 'true',
    ALLOW_SOCIAL_LOGIN: 'false', ALLOW_SOCIAL_REGISTRATION: 'false',
    ALLOW_UNVERIFIED_EMAIL_LOGIN: 'true',
    LIBRECHAT_CODE_BASEURL: 'http://host.docker.internal:8084/v1/librechat',
    RAG_API_URL: 'http://rag_api:8000', CONFIG_PATH: '/app/librechat.yaml',
  });
  for (const key of Object.keys(env)) if (/^(OPENID_|SMTP_|EMAIL_)/.test(key)) delete env[key];
  fs.writeFileSync(envPath, Object.entries(env).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join('\n') + '\n', { mode: 0o600 });
  fs.chmodSync(envPath, 0o600);
}

if (require.main === module) {
  const root = path.resolve(__dirname, '..');
  prepareEnvironment(root, __dirname);
  prepareBuildContext(root, __dirname);
  console.log('Prepared source; preserved existing private runtime configuration.');
}

module.exports = { prepareEnvironment, prepareBuildContext };
