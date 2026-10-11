const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { prepareEnvironment, prepareBuildContext } = require('./prepare.cjs');
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'mygpt-handoff-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const local = path.join(root, '.mygpt-local'); fs.mkdirSync(local);
  return { root, local };
}
test('restart preserves existing SSO, model list and encryption keys byte-for-byte', t => {
  const { root, local } = fixture(t);
  const env = 'OPENID_ISSUER=https://example.invalid\nALLOW_SOCIAL_LOGIN=true\nOPENAI_MODELS=gpt-6-luna\nCREDS_KEY=fixture-key\n';
  const p = path.join(local, 'runtime.env'); fs.writeFileSync(p, env, { mode: 0o644 });
  prepareEnvironment(root, local);
  assert.equal(fs.readFileSync(p, 'utf8'), env);
  assert.equal(fs.statSync(p).mode & 0o777, 0o600);
  assert.equal(fs.existsSync(path.join(local, 'secrets.json')), false);
});
test('fresh environment keeps persistent generated keys across subsequent preparation', t => {
  const { root, local } = fixture(t);
  fs.writeFileSync(path.join(root, '.env'), 'OPENAI_API_KEY=fixture-only\n');
  prepareEnvironment(root, local);
  const env = fs.readFileSync(path.join(local, 'runtime.env'));
  const secrets = fs.readFileSync(path.join(local, 'secrets.json'));
  prepareEnvironment(root, local);
  assert.deepEqual(fs.readFileSync(path.join(local, 'runtime.env')), env);
  assert.deepEqual(fs.readFileSync(path.join(local, 'secrets.json')), secrets);
});
test('build context excludes env files and generated directories', t => {
  const { root, local } = fixture(t);
  for (const dir of ['api', 'client', 'packages', 'config']) fs.mkdirSync(path.join(root, dir));
  for (const file of ['package.json', 'package-lock.json', '.npmrc']) fs.writeFileSync(path.join(root, file), '{}');
  fs.writeFileSync(path.join(local, 'Dockerfile'), 'FROM scratch');
  fs.writeFileSync(path.join(root, 'api', '.env.private'), 'fixture-secret');
  fs.mkdirSync(path.join(root, 'api', 'node_modules'));
  fs.writeFileSync(path.join(root, 'api', 'index.js'), 'fixture');
  prepareBuildContext(root, local);
  const target = path.join(local, 'build-context', 'api');
  assert.equal(fs.existsSync(path.join(target, '.env.private')), false);
  assert.equal(fs.existsSync(path.join(target, 'node_modules')), false);
  assert.equal(fs.readFileSync(path.join(target, 'index.js'), 'utf8'), 'fixture');
});
for (const scenario of ['official', 'custom', 'missing-overlay']) {
  test(`startup selects ${scenario} safely`, t => {
    const { root, local } = fixture(t); const bin = path.join(root, 'bin'); fs.mkdirSync(bin);
    fs.copyFileSync(path.join(__dirname, 'start.sh'), path.join(local, 'start.sh'));
    fs.writeFileSync(path.join(local, 'interpreter-mode'), scenario === 'custom' ? 'custom' : 'official');
    if (scenario === 'official') fs.writeFileSync(path.join(local, 'official-interpreter.yml'), '{}');
    fs.writeFileSync(path.join(bin, 'git'), '#!/bin/sh\nprintf fixture\\n\n', { mode: 0o755 });
    fs.writeFileSync(path.join(bin, 'node'), `#!/bin/sh\ntouch '${root}/prepared'\n`, { mode: 0o755 });
    fs.writeFileSync(path.join(bin, 'docker'), `#!/bin/sh\nprintf '%s\\n' "$@" > '${root}/compose-args'\n`, { mode: 0o755 });
    const r = spawnSync('/bin/sh', [path.join(local, 'start.sh')], { env: { ...process.env, PATH: bin + ':' + process.env.PATH } });
    if (scenario === 'missing-overlay') {
      assert.equal(r.status, 1); assert.equal(fs.existsSync(path.join(root, 'prepared')), false);
    } else {
      assert.equal(r.status, 0);
      const args = fs.readFileSync(path.join(root, 'compose-args'), 'utf8');
      assert.equal(args.includes('official-interpreter.yml'), scenario === 'official');
    }
  });
}
test('SSH tunnel binds loopback and forwards to the existing server interface', t => {
  const { root } = fixture(t); const bin = path.join(root, 'bin'); fs.mkdirSync(bin);
  fs.writeFileSync(path.join(bin, 'ssh'), `#!/bin/sh\nprintf '%s\\n' "$@" > '${root}/ssh-args'\n`, { mode: 0o755 });
  const script = path.resolve(__dirname, '../scripts/mygpt2/interpreter-tunnel.sh');
  const r = spawnSync('/bin/sh', [script, 'steve@example.invalid', '2222'], { env: { ...process.env, PATH: bin + ':' + process.env.PATH } });
  assert.equal(r.status, 0);
  const args = fs.readFileSync(path.join(root, 'ssh-args'), 'utf8');
  assert.ok(args.includes('127.0.0.1:33114:100.68.21.112:33114'));
  assert.ok(args.includes('ExitOnForwardFailure=yes'));
  assert.ok(args.includes('2222'));
  assert.equal(args.includes('StrictHostKeyChecking=no'), false);
});
test('SSH tunnel rejects invalid ports and option-like destinations', () => {
  const script = path.resolve(__dirname, '../scripts/mygpt2/interpreter-tunnel.sh');
  for (const args of [['-unsafe', '22'], ['steve@example.invalid', 'invalid'], ['steve@example.invalid', '65536']]) {
    assert.equal(spawnSync('/bin/sh', [script, ...args]).status, 1);
  }
});
