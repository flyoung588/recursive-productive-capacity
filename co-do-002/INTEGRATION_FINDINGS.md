# OpenHands #18981: independent regression results and integration boundary

Checked 2026-10-28. This is not an OpenHands integration or framework test.

Original detector commit: 7539a825d424d09ff109acc4d1ce49ad5caa71a3.
Canvas source: 6354932e87f99e1583f482f2cea49d6d573443e0.
SDK source: 46b1fa5cb91ada17e6ec938c7e8624a4fa19fa98.

## Actual execution

`python3 -m unittest discover -s co-do-002 -v`

Original suite: 13/13 pass. Extended suite: 16/16 pass using real temporary Git
repositories, without model calls or network. Raw outputs are in evidence/.
New regressions cover staged dirty-to-dirty edits, independent linked-worktree
working files, and explicitly record rejection of an unborn repository.
The latter is a documented limitation, not acceptance-criterion fulfillment.

## Current upstream work

Issue remains open. PR https://github.com/OpenHands/OpenHands/pull/19014 is open
and overlaps the UI work. Review already asks for dirty-to-dirty coverage and
agent-context delivery. No duplicate implementation PR was created.

## Source-owned integration constraints

Canvas AGENTS.md assigns conversation lifecycle and REST/client contracts to
software-agent-sdk. Canvas depends on public typed client interfaces; no private
backend or shell endpoint should be invented inside its resume hook.

At the pinned SDK source, agent_server/conversation_router.py run_conversation
calls event_service.run(). agent_server/event_router.py send_message calls
EventService.send_message(message, request.run), so resume-only /run and a new
message with run=True must both be considered. EventService's background run
supports native arun and sync fallback. SDK conversation/impl/local_conversation.py
implements both run and arun; completion capture must cover both without
recording an intermediate state as the final baseline.

Existing git_router.py exposes changes/diffs/commits; its changes endpoint is a
list of GitChange, not a persisted prior-turn fingerprint. A file-count comparison
cannot distinguish two different edits to one already-dirty file. The standalone
content hashes demonstrate that case; they do not establish a public drift API.

A real implementation needs a durable server-owned baseline keyed by actual
workspace/worktree identity, refreshed after the completed turn and compared
before the next agent step. It must produce an agent-visible event/context item
as well as UI information. Ownership/release decisions for that typed contract
remain unresolved here. Canvas currently requires minimumAgentServer 1.57.0;
new required behavior needs the corresponding compatibility bump and typed client.
Local and Cloud transports require separate coverage per the repository guide.

## Remaining detector limits

The reference detector raises on non-Git/unborn repos and Git failures. A real
advisory integration must catch unavailable checks and continue, without confusing
unavailable with unchanged. Its hashes contain no file bodies but computing them
reads tracked diffs and untracked content. It has no total hashing budget: huge
untracked files can be expensive. Each Git command has a timeout, but untracked
file reads do not. It reports categories, not changed paths, does not persist or
bind snapshots to a worktree, and does not capture/inject lifecycle events.
No performance benchmark, UI test, server integration test, or maintained release
compatibility test was run. The linked-worktree regression only proves isolated
working-file detection, not persistence-key correctness.
