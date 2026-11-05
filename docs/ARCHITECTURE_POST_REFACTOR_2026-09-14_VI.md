# Kiến trúc nc_v7 monolith — sau refactor Network Change

> **Ngày cập nhật:** 2026-09-14  
> **Mốc đối chiếu:** `ARCHITECTURE_BASELINE_2026-09-14_VI.md`  
> **Profile mặc định:** `APP_PROFILE=network_change`

## 1. Kết quả refactor

Ứng dụng vẫn là một FastAPI monolith và một lead agent loop. Refactor không tạo
planner/triage/executor agent service mới, không thay đổi cách chọn model của
session, và không tạo PostgreSQL/Qdrant container khi chạy Uvicorn.

Những thay đổi đã triển khai:

- Profile Network Change allow-list route/tool tại composition boundary.
- Prompt recall bằng Arrow Up/Down, theo session và có giữ draft hiện tại.
- Một registry chung cho built-in và MCP tool với ID canonical.
- Ba mode theo session: `disabled`, `auto`, `pinned`.
- Similarity filtering áp dụng cho tên MCP qualified, không còn gửi toàn bộ MCP
  schema khi chỉ một số tool liên quan.
- Knowledge/instruction có thể ingest bằng CLI hoặc Settings > Knowledge Base.
- Document của session được mirror ra `data/generated/` ngoài bản SQL/MinIO.
- Artifact `network-cli` và `kubernetes` có editor; nút **Validate** không gọi
  host shell.
- Validator trả các mức kiểm chứng, thay vì một boolean gây hiểu nhầm.
- MCP Kubernetes sandbox là process riêng, chỉ dùng kubeconfig lab riêng.

Quyết định với ba tool orchestration cũ:

- `create_session` được giữ: lead agent có thể tạo một session/chat mới khi
  nhiệm vụ thực sự cần một workspace tách biệt.
- `send_to_session` bị chặn trong profile mặc định vì nó điều phối một agent
  loop ở session khác, không cần cho Q&A, report hay document của lead hiện tại.
- Generic `pipeline` bị chặn vì nó chạy nhiều prompt/model theo stage và tạo
  một lớp orchestration thứ hai. Network-change proposal vẫn có staged plan,
  nhưng chính một lead agent loop thực hiện các stage bằng tool calls.
- Teacher escalation và việc tự ghi skill từ kết quả teacher cũng không chạy
  trong profile này; skill/instruction do người dùng quản lý vẫn được giữ.

Hai tool bị chặn không bị xóa vật lý; `APP_PROFILE=legacy` là đường rollback nếu
server soak-test cho thấy một workflow cũ thực sự phụ thuộc vào chúng.

## 2. Kiến trúc thành phần sau refactor

```mermaid
flowchart TB
    UI[Network Change SPA] --> API[FastAPI monolith]
    API --> Chat[Chat/session routes]
    API --> Docs[Document + local mirror]
    API --> KB[Knowledge ingest]
    API --> MCPAdmin[MCP administration]

    Chat --> Intent[action_intents]
    Intent --> Lead[Single agent_loop]
    Lead --> Registry[Unified tool_registry]
    Registry --> Similarity[Qdrant tool_index]
    Lead --> Builtin[Built-in handlers]
    Lead --> MCP[MCP manager]

    Builtin --> Net[Network change tools]
    Net --> SQL[(SQLite/PostgreSQL)]
    Docs --> SQL
    Docs --> Files[data/generated]
    KB --> Qdrant[(Qdrant)]

    MCP --> ProdMCP[K8s/network MCP read-only]
    MCP --> SandboxMCP[k8s-sandbox MCP optional]
    ProdMCP --> Prod[Managed/lab cluster observations]
    SandboxMCP --> Sandbox[Dedicated disposable cluster]
```

## 3. Trình tự chat và chọn tool

```mermaid
sequenceDiagram
    participant U as Người dùng
    participant UI as Chat UI
    participant CR as chat_routes
    participant AG as agent_loop
    participant REG as tool_registry
    participant TI as tool_index
    participant LLM as Session model
    participant EX as Tool dispatcher

    U->>UI: Chọn disabled/auto/pinned và gửi prompt
    UI->>CR: Chat request
    CR->>AG: Message + owner + session
    AG->>REG: Đọc profile và preference theo session
    REG-->>AG: Disabled set + pinned set + registry
    AG->>TI: Similarity query trên built-in và MCP qualified name
    TI-->>AG: Auto tools liên quan
    AG->>AG: Union(auto, pinned) - disabled
    AG->>LLM: Prompt + đúng tool schemas
    LLM-->>AG: Text hoặc tool calls
    AG->>AG: Recheck disabled trước execution
    AG->>EX: Tool call hợp lệ
    EX-->>AG: Kết quả
    AG-->>UI: SSE response/tool events
```

## 4. Trình tự network change và validation

```mermaid
sequenceDiagram
    participant U as Operator
    participant A as Lead agent
    participant RO as Read-only MCP
    participant N as Network tools
    participant D as Document editor
    participant S as Sandbox MCP

    U->>A: Yêu cầu network change
    A->>RO: Lấy resource/status/event/log cần thiết
    RO-->>A: Evidence read-only
    A->>N: collect snapshot / compare / prepare
    N-->>A: Proposal + risk + validation levels
    N->>D: Tạo command-only .cli hoặc manifest
    D-->>U: File có thể edit, copy/export và Validate
    U->>D: Validate
    D->>N: Static validation
    N-->>D: pass/fail/warning, không execute
    opt Sandbox MCP đã cấu hình
        A->>S: server-side dry-run
        S-->>A: API errors/evidence
        A->>S: isolated apply + observe + rollback + cleanup
        S-->>A: stage results
    end
    A-->>U: Tổng hợp intent, risk, evidence và trạng thái
```

## 5. Ý nghĩa các mức validation

| Mức | Nguồn kiểm chứng | Có thể báo gì |
|---|---|---|
| `static` | Parser/linter trong monolith | Cú pháp, placeholder, lệnh nguy hiểm |
| `instruction_grounding` | Knowledge/instructions đã retrieve | Lệnh có căn cứ tài liệu hay chưa |
| `live_preconditions` | Snapshot MCP read-only mới | Target và precondition hiện tại |
| `api_dry_run` | Sandbox API server | Kubernetes schema/admission |
| `sandbox_apply` | Namespace disposable | Resource có tạo được trong lab |
| `runtime_probes` | Quan sát workload sandbox | Readiness/resource observation |
| `rollback_test` | Apply rollback trong sandbox | Rollback có thực hiện được |
| `vendor_runtime` | Emulator/test node vendor | Chỉ pass khi có môi trường thật |

Không có sandbox/evidence đầy đủ thì status là `partially_verified`; model không
được tự nâng thành `passed`.

## 6. Lưu trữ sau refactor

| Dữ liệu | Nơi lưu |
|---|---|
| Session/chat/document/version/proposal/snapshot | SQLite hoặc PostgreSQL |
| Knowledge và tool embeddings | Qdrant |
| Document object | MinIO nếu bật |
| Bản file đọc trực tiếp | `data/generated/<owner>/<session>/` |
| Tool preference | `data/tool_preferences.json`, theo owner/session |
| Knowledge thêm từ UI | `knowledge_base/user/<owner>/<role>/` + Qdrant |

Uvicorn không tạo Docker image cho bất kỳ database nào.

## 7. Đối chiếu với baseline

| Baseline | Sau refactor |
|---|---|
| MCP similarity chỉ thực tế lọc built-in | Lọc cả built-in và MCP qualified schema |
| Toggle built-in/MCP rời rạc | Registry chung + tri-state theo session |
| Không có prompt recall | Arrow Up/Down theo lịch sử user prompt |
| Document chủ yếu SQL/MinIO | Thêm local mirror trong `data/generated` |
| Knowledge ingest chỉ CLI/generic upload | CLI + UI có role knowledge/instructions |
| Validator static boolean | Validation levels + `partially_verified` |
| Run Bash có thể gọi host shell | Network CLI không có Run; chỉ Validate |
| Không có sandbox | Có adapter MCP riêng, opt-in, lab-only |
| Route Odysseus đăng ký rộng | Profile Network Change không đăng ký route legacy |

## 8. Những phần còn thiếu/cần update

1. Chưa có vendor EMS/MME emulator; vendor CLI chưa thể runtime-pass.
2. Sandbox chưa mô phỏng đầy đủ CNI, traffic thật, node failure, storage hoặc
   controller đặc thù của production.
3. Chưa có UI timeline riêng cho snapshot/proposal/sandbox run; hiện kết quả đi
   qua response/tool event và document panel.
4. Chưa có automatic repair policy riêng cho từng stage; bounded agent loop có
   thể sửa theo lỗi tool nhưng model không được tự chứng nhận kết quả.
5. Tool preference hiện là JSON owner-scoped, chưa migrate sang PostgreSQL.
6. Các module legacy còn nằm trong source để rollback nhưng không được register
   ở profile mặc định; có thể xóa vật lý ở đợt sau khi server soak-test ổn định.
7. Agent-run replay vẫn ở RAM, chưa bền qua restart và chưa phù hợp multi-replica.
8. Cần test tích hợp trên sandbox cluster nội bộ với RBAC tối thiểu trước khi bật
   `K8S_SANDBOX_ENABLE_APPLY=true`.
9. Sandbox result đã bị buộc với SHA-256 của artifact và phải có stage
   `api_dry_run`, nhưng chưa có chữ ký/attestation độc lập; về dài hạn nên lưu
   execution record phía server thay vì để model chuyển tiếp JSON tool result.
