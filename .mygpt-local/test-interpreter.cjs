const assert = require('node:assert/strict');
(async () => {
  const base = process.env.LIBRECHAT_CODE_BASEURL;
  assert(base, 'MyGPT2 interpreter URL must be configured');
  const headers = { 'Content-Type': 'application/json', 'X-API-Key': process.env.LIBRECHAT_CODE_API_KEY || '' };
  const health = await fetch(new URL('/health', base), { signal: AbortSignal.timeout(10000) });
  assert.equal(health.status, 200);
  console.log('Interpreter reachable from MyGPT2 container: PASS');
  const code = [
    'import pandas as pd',
    'import matplotlib',
    'matplotlib.use("Agg")',
    'import matplotlib.pyplot as plt',
    'df = pd.DataFrame({"value": [1, 2, 3]})',
    'assert int(df["value"].sum()) == 6',
    'df.to_excel("mygpt2-smoke.xlsx", index=False)',
    'plt.plot(df["value"])',
    'plt.savefig("mygpt2-smoke.png")',
    'print("MYGPT2_INTERPRETER_SMOKE_OK")',
  ].join('\n');
  const result = await fetch(base + '/exec', { method: 'POST', headers, body: JSON.stringify({ lang: 'py', code, user_id: 'mygpt2-local-smoke-test' }), signal: AbortSignal.timeout(180000) });
  const body = await result.json();
  assert.equal(result.status, 200, JSON.stringify(body));
  assert.equal(body.stdout.trim(), 'MYGPT2_INTERPRETER_SMOKE_OK', 'Python output should contain no compatibility warnings');
  assert.equal(body.stderr.trim(), '', 'Python should complete without errors');
  for (const name of ['mygpt2-smoke.xlsx', 'mygpt2-smoke.png']) {
    const file = (body.files || []).find(f => f.name === name);
    assert(file, 'Generated file missing: ' + name);
    const download = await fetch(base + '/download/' + body.session_id + '/' + file.id, { headers, signal: AbortSignal.timeout(10000) });
    assert.equal(download.status, 200, 'Download failed: ' + name);
    const bytes = Buffer.from(await download.arrayBuffer());
    assert(bytes.length > 100, 'Downloaded file is empty: ' + name);
    assert(bytes.subarray(0, name.endsWith('.png') ? 4 : 2).equals(name.endsWith('.png') ? Buffer.from([137,80,78,71]) : Buffer.from('PK')), 'Invalid file format: ' + name);
    console.log('Python generated and downloaded ' + name + ': PASS (' + bytes.length + ' bytes)');
  }
  console.log('Python execution, pandas, Excel and chart smoke test: PASS');
})().catch(e => { console.error(e.message); process.exit(1); });
