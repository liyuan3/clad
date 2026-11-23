# M1 API contract
All JSON. Base /api. IDs strings, timestamps UTC ISO8601. Errors {detail:string}. User auth Bearer token; device credentials distinct. Every resource access checks ownership. Frontend same origin, served at / by FastAPI.

POST /api/auth/login {username,password} -> {access_token,username}. Provision initial users via local CLI, no open registration; hashed passwords, no default credentials.
GET /api/devices -> [{id,name,status:online|offline|busy}]
POST /api/devices/pairing -> {code,expires_at}; short-lived single-use code owned by authenticated user.
POST /api/runner/pair {code,name} -> {device_id,device_token}; one device per user for M1, reject second binding.
GET /api/conversations -> [{id,title,device_id,created_at}]
POST /api/conversations {device_id,title} -> same object.
GET /api/conversations/{id}/messages -> [{id,role:user|assistant,content,created_at}]
POST /api/conversations/{id}/runs {prompt,request_id} -> {id,status}; request_id deduplicated per user; offline 409, busy 409. Persist accepted user message.
GET /api/runs/{id} -> {id,status:accepted|running|completed|failed|cancelled|unknown,error:null|string}
GET /api/runs/{id}/events?after=0 -> [{seq,type:text|log|status,data:string}]; persistent sequenced events, frontend polls each second initially. text events append assistant output; persist final assistant message once.
POST /api/runs/{id}/cancel -> {id,status}; request cancellation, do not claim stopped until runner acknowledges.
GET /api/runs/{id}/artifacts -> [{id,name,size}]
GET /api/artifacts/{id}/download -> authenticated download; never accept arbitrary server/local paths.

Runner outbound websocket /api/runner/ws with Authorization Bearer device_token. Server commands {type:run,run_id,conversation_id,prompt} or {type:cancel,run_id}. Runner events {type:event,run_id,seq,event_type:text|log|status,data:string}; server ACK {type:ack,run_id,seq}. heartbeat {type:heartbeat}; connection alive timeout. Runner stores execution journal, session IDs and unacked events on local disk, replays events not commands. Reconnection must not execute accepted jobs twice; uncertain execution becomes unknown, not automatically retried. Server restart makes stale in-flight jobs unknown until reconciled.

Runner uses argument arrays, no shell interpolation. One workspace per conversation, persistent; Claude session_id scoped to conversation. Stream JSON parsing, tool permissions explicit; never blanket bypass permissions. If approval cannot be handled in M1, fail clearly. Cancel entire owned process tree with bounded graceful period; validate Windows behavior separately. No user-supplied command lines.

M1 single server process + SQLite. Multi-worker routing unsupported and documented. Artifacts uploaded by runner to POST /api/runner/runs/{id}/artifacts (multipart file), authenticated device bound to run; size cap and safe generated storage name.

## Accepted H001a additions
GET /api/health -> {status,version}, public liveness endpoint.
GET /api/runner/device -> {id,name,status}, requires device Bearer credential; user tokens rejected.
