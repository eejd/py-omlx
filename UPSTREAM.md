# Work carried on `local` that is not in jundot/omlx

`local` = upstream release tag + the commits below. `main` mirrors `jundot/omlx` `main`
(fast-forward only). `local` is based on `v0.7.0`, the release the `py-omlx` port ships;
upstream `main` is far ahead of it. The two packaging-only patches of the stable `py-omlx`
port (`patch-no-update-check`, `patch-private-mcp-path`) are not carried here.

| What | Branch | Upstream status |
|---|---|---|
| Do not add a second BOS to chat prompts whose template already emits it (Llama 3: 238/195/91 instead of 237/194/90 prompt tokens): `BatchedEngine.chat`/`stream_chat` hand the scheduler ids tokenized with one BOS; `count_chat_tokens`, `preflight_chat` and the SpecPrefill system-end count use the same rule | `topic/chat-template-no-double-bos` (based on `local`; the scheduler tokenization is unchanged on upstream `main`, read not run) | not submitted; nothing is posted upstream before the quantbench + agentbench soak (ADR-0008); eejd/py-omlx#1 |
