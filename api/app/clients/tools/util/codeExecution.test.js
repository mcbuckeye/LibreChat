const { createCodeExecutionTool } = require('@librechat/agents');
const { normalizeCodeExecutionTool } = require('./codeExecution');

describe('code execution optional arguments', () => {
  function createTool() {
    const tool = normalizeCodeExecutionTool(createCodeExecutionTool({ apiKey: 'test-key' }));
    tool.func = jest.fn().mockResolvedValue(['stdout: 4', {}]);
    return tool;
  }

  test('executes when the model returns null for optional arguments', async () => {
    const tool = createTool();
    await tool.invoke({ lang: 'py', code: 'print(2 + 2)', session_id: null, args: null });
    expect(tool.func.mock.calls[0][0]).toEqual({
      lang: 'py',
      code: 'print(2 + 2)',
      session_id: undefined,
      args: undefined,
    });
  });

  test('preserves an existing session and command arguments', async () => {
    const tool = createTool();
    await tool.invoke({
      lang: 'py',
      code: 'print(2 + 2)',
      session_id: 'existing-session',
      args: ['a'],
    });
    expect(tool.func.mock.calls[0][0]).toMatchObject({
      session_id: 'existing-session',
      args: ['a'],
    });
  });

  test('still rejects invalid optional arguments', async () => {
    const tool = createTool();
    await expect(tool.invoke({ lang: 'py', code: 'print(4)', session_id: 123 })).rejects.toThrow();
    await expect(tool.invoke({ lang: 'py', code: 'print(4)', args: 'a' })).rejects.toThrow();
    expect(tool.func).not.toHaveBeenCalled();
  });
});
