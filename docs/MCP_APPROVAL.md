# MCP exact-plan review

Run `rashi mcp` over stdio. This is a small serial JSON-RPC server, not a complete MCP SDK.

Builds require a client that advertises form elicitation. Protocols 2025-06-18 and 2025-11-25
support it; legacy 2024-11-05 / 2025-03-26 connections may call the other tools but builds fail
closed. Under the current specification, `elicitation: {}` is form-only compatibility shorthand;
`elicitation: {"form": {}}` explicitly declares it. URL-only clients cannot approve builds.

The server sends `elicitation/create` after drafting, review and task splitting, with the exact
spec, reviewer findings, workdir, task goals/checks, agent templates and iteration bound. Only
`action: "accept"` with `content: {"approve": true}` for that request allows coding agents to
start. Tool arguments cannot approve a plan. A missing/malformed reply, decline, cancellation,
end-of-input or 15-minute approval timeout denies execution. No planning call changes the plan afterward.

The client is a trusted human-approval surface. Use only clients that display the complete review
and obtain the person's decision, not clients that auto-answer form requests. The server cannot
prove what a third-party client showed. The workdir receives planning artifacts before approval.
CLI coding agents run with host privileges, not inside the check sandbox. Use a disposable workspace
without secrets; the plan warning is intentional. Approval does not authorize paid services.

Current limit: tool calls are serial. While waiting for approval, other requests receive a busy
error. Cancellation is honored before approval, not during a running build; individual coding CLI
invocations retain their timeout. This is adapter-tested locally, not verified in every MCP client.

Sources:
- https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation
- https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation
