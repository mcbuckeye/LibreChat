/** Accept omitted optional code-tool arguments when a model sends explicit nulls. */
function normalizeCodeExecutionTool(tool) {
  const { session_id, args } = tool.schema.shape;
  tool.schema = tool.schema.extend({
    session_id: session_id.nullable().transform((value) => value ?? undefined),
    args: args.nullable().transform((value) => value ?? undefined),
  });
  return tool;
}

module.exports = { normalizeCodeExecutionTool };
