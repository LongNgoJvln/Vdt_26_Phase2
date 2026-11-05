# MCP tools without Qdrant (k8s / kubectl tools stay callable)

> Tiếng Việt / English notes below. Nắm bắt nhanh: **MCP tools giờ không còn
> phụ thuộc Qdrant. Khi không host được Qdrant, toàn bộ schema MCP đang kết nối
> vẫn được gửi cho LLM — giống bản `nc_v7_monolith`. Khi có Qdrant trong cluster,
> hàm embedding/selection tự kích hoạt lại để thu hẹp MCP tools theo retrieval.**

## Tóm tắt vấn đề (vấn đề gốc)

Trước đây, `nc_v7_monolith_v2` đã refactor phần chọn tool sao cho **schema MCP
cũng bị lọc bởi insieme `_relevant_tools`** lấy từ RAG index dựa trên Qdrant
(`src/tool_index.py`). Điều đó có nghĩa:

- Schema MCP luôn được build từ `McpManager` (trong RAM, không qua Qdrant) — OK.
- Nhưng việc **schema nào thực sự gửi tới LLM lại bị chặn bởi Qdrant** qua bộ lọc
  `_relevant_tools`.
- Khi Qdrant không chạy được (ví dụ không thể host container Qdrant ở đây),
  retrieval trả về rỗng → toàn bộ MCP tools bị lọc bỏ trước khi tới model.
- Triệu chứng: đã kết nối `mcp-k8s-server` (23 tools) nhưng agent không bao giờ
  gọi `kubectl_*`; thay vào đó bịa ra `api_call` rồi crash stream (`TypeError:
  sequence item 0: expected str instance, dict found`) → trả lỗi 500 cho người dùng.

Bản `nc_v7_monolith` (bản chạy được) thì ngược lại: **luôn gửi hết schema MCP
khi có server kết nối**, độc lập với Qdrant. Nên k8s tools vẫn gọi được dù
Qdrant sập.

## Cách sửa trong `nc_v7_monolith_v2`

Logic chọn schema (trong `src/agent_loop.py`, khối build `all_tool_schemas`)
đã được tách rời khả năng nhìn thấy MCP khỏi tình trạng Qdrant:

- Thêm cờ `_mcp_rag_active` — chỉ `True` khi retrieval thực sự chạy thành công
  dựa trên index Qdrant khỏe (hoặc khi caller truyền sẵn `relevant_tools`).
- Khi `_mcp_rag_active == True` (Qdrant up): MCP schemas được thu hẹp theo
  `_relevant_tools` — hành vi RAG như thiết kế refactor ban đầu.
- Khi `_mcp_rag_active == False` (Qdrant không chạy / keyword fallback): **gửi
  HẾT schema MCP đang kết nối**, không lọc — đúng như `nc_v7_monolith`.

Đồng thời sửa crash `TypeError` ở nhánh tool bị block: trước đây append một
`dict` vào `tool_results` (được `"\n\n".join(...)` trong path fenced-block),
nay append chuỗi để không bao giờ làm sập stream.

## Bảng hành vi

| Tình huống        | _mcp_rag_active | Schema MCP gửi tới LLM      | k8s/kubectl_* gọi được |
|-------------------|-----------------|------------------------------|------------------------|
| Qdrant up         | True            | thu hẹp theo retrieval       | Có (nếu retrieval khớp)|
| **Qdrant DOWN**   | **False**       | **gửi hết (như bản gốc)**    | **Có**                 |

## Khi nào "embedding function in Qdrant trigger later"

Khi triển khai Qdrant trong cluster (`QDRANT_URL` trỏ tới instance chạy được,
hoặc service `qdrant` có DNS phân giải), quá trình này diễn ra **tự động, không
cần đổi code**:

1. `src/tool_index.get_tool_index()` khởi tạo được `ToolIndex` (healthy = true).
2. Trong agent loop, `tool_idx.index_mcp_tools(mcp_mgr, ...)` đánh schema của
   các MCP server đang kết nối vào collection Qdrant (xem `src/tool_index.py`).
3. `get_tools_for_query()` trả về tên qualified `mcp__<server>__<tool>` khớp
   với câu truy vấn → `_mcp_rag_active = True`.
4. Khối build schema chuyển sang nhánh thu hẹp MCP theo retrieval.

Tức là: **không cần fallback khi deployment đầy đủ**. Behaviour lúc thiếu Qdrant
(gửi hết MCP) chỉ là fall-through an toàn cho môi trường dev/đơn lẻ.

## Cách xác minh lại

Trong `data/logs/app.log`, sau khi gửi một câu hỏi k8s:

- Nếu **không** có Qdrant: vẫn thấy
  `[tool-rag] Keyword fallback selected: ...` NHƯNG
  `[agent-debug] round=1 ... tools_sent=` giờ **bao gồm `mcp__...__kubectl_get`
  (và các tool MCP khác)**, và tool execution thật sự gọi MCP.
- Nếu có Qdrant: thấy `ToolIndex init` thành công, `Indexed N MCP tools`, và
  `[tool-rag] Retrieved tools for query: [... 'mcp__...__kubectl_get' ...]`.

## Files liên quan

- `src/agent_loop.py` — cờ `_mcp_rag_active`, khối build schema, nhánh tool block.
- `src/tool_index.py` — index Qdrant + retrieval (chỉ dùng khi Qdrant healthy).
- `src/mcp_manager.py` — `get_all_openai_schemas()` (luôn dùng, không phụ thuộc Qdrant).
