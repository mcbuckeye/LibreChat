const mockFetch = jest.fn();
jest.mock(
  'node-fetch',
  () =>
    (...args) =>
      mockFetch(...args),
);
const { createCodeExecutionTool } = require('@librechat/agents');

describe('MyGPT2 interpreter compatibility with Agents SDK 4', () => {
  beforeEach(() => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ stdout: '6', stderr: '', session_id: 'test-session', files: [] }),
    });
  });

  test('executes Python using the SDK 4 schema without the old Zod workaround', async () => {
    const tool = createCodeExecutionTool({
      baseUrl: 'http://interpreter.invalid/v1/librechat',
      user_id: 'test-user',
    });
    const result = await tool.invoke({ lang: 'py', code: 'print(6)' });
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('http://interpreter.invalid/v1/librechat/exec');
    expect(JSON.parse(options.body)).toMatchObject({
      lang: 'py',
      code: 'print(6)',
      user_id: 'test-user',
    });
    expect(JSON.stringify(result)).toContain('6');
  });

  test('sends previously generated files to subsequent executions', async () => {
    const files = [{ id: 'file-1', name: 'input.csv', session_id: 'previous-session' }];
    const tool = createCodeExecutionTool({
      baseUrl: 'http://interpreter.invalid/v1/librechat',
      files,
    });
    await tool.invoke({ lang: 'py', code: 'print(6)', args: ['a'] });
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toMatchObject({ files, args: ['a'] });
  });

  test('does not let model arguments opt into stateful execution', async () => {
    const tool = createCodeExecutionTool({
      baseUrl: 'http://interpreter.invalid/v1/librechat',
      executionProfile: 'default',
    });
    await tool.invoke({
      lang: 'py',
      code: 'print(6)',
      runtime_session_hint: 'untrusted-workspace',
    });
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).not.toHaveProperty('runtime_session_hint');
  });
});
