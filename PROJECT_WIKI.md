# PROJECT WIKI — All Things Agentic Hackathon
> Tài liệu tham khảo tổng hợp cho Claude Code trong quá trình build dự án.
> Đọc kỹ trước khi viết bất kỳ dòng code nào — đặc biệt phần 6 (Eligibility Constraint), phần 7.5 (ADK Technical Patterns), và phần 8 (Kiến trúc mục tiêu).

## 0. NGUỒN TÀI LIỆU GỐC ĐÃ IMPORT VÀO PROJECT (danh mục tham chiếu)

Toàn bộ nội dung dưới đây được tổng hợp/chắt lọc từ các tài liệu sau (đều nằm trong project knowledge, có thể tra cứu lại nguyên văn nếu cần chi tiết hơn):

| Tài liệu nguồn | Nội dung | Dùng cho mục nào trong wiki này |
|---|---|---|
| `Build_next-gen_AI_agents_in_the_All_things_agentic_hackathon` | Video giới thiệu hackathon (transcript) — tổng quan, track, giải thưởng, cách nộp bài | Mục 1, 2, 3, 5 |
| `TRACKS` | Mô tả chi tiết track Collaborative Partner | Mục 3.2 |
| `Requirements` | "What to Build" — mô tả 3 track + yêu cầu kỹ thuật bắt buộc | Mục 2, 3 |
| `Judging_Criteria` | 3 tiêu chí chấm điểm chính + trọng số % | Mục 4 |
| `Rules` (48K — file luật chơi đầy đủ, dài nhất) | Toàn bộ Official Rules: eligibility, contest period, judging 3-stage, prize, IP, disclosure... | Mục 4, 5, 6, 11 |
| `What_to_Submit_` | Checklist chi tiết nộp bài (video, repo, diagram, bonus) | Mục 5 |
| `PRO_TIPS_TO_KEEP_YOUR_COSTS_DOWN` | Mẹo tiết kiệm chi phí GCP | Mục 10 (lịch trình), phần chi phí |
| `Give_your_project_a_self-check__pro_tips_inside_` | Self-check trước deadline — nhấn mạnh video là thứ giám khảo xem nhiều nhất | Mục 5, 10, 11 |
| `everything_you_need_to_finish_strong` | Tổng hợp resource giữa chặng đường — link tool, credit, cảnh báo dùng AI khi build | Mục 5, 11 |
| `_Architecting_Multi-Agent_Teams...` (2 file, workshop ADK2) | Transcript workshop kỹ thuật: Single Agent → ADK1.x → ADK2 (Graph/Collaborative/Dynamic Pattern) | **Mục 7.5** |
| `_Build_a_Long-Running_Agent__Persistent_Workflows_with_Google_ADK` | Transcript workshop: Session vs Memory, Memory Service backends, Runner | **Mục 7.5.6** |
| `_Build_a_Self-Evolving_Agent__Autonomous_Self-Improvement` | Transcript workshop: ADK eval framework, reward hacking | **Mục 7.5.7** |
| `đồ_án_CritiqAI_đoạt_giải_AI_hackathon_của_kaggle_và_google` | Tài liệu kỹ thuật đầy đủ của CritiqAI (dự án cũ, dùng làm case study) | Mục 9 |

---

## 1. TỔNG QUAN CUỘC THI

**Tên:** All Things Agentic Hackathon
**Ban tổ chức:** Google Cloud
**Trang nộp bài:** allthingsagentichackathon.devpost.com
**Submission Period:** 3/8/2026 (9:00 AM PT) → 31/8/2026 (5:00 PM PT)
**Judging Period:** 1/9/2026 → 1/10/2026
**Tổng giải thưởng:** $180,000 (tiền mặt + Google Cloud credits)

**Mission:** Build và deploy một AI Agent tự hành thế hệ mới — không phải chatbot đơn giản. Agent phải:
- Chạy bất đồng bộ (asynchronous) trong nền
- Quản lý workflow nhiều bước phức tạp
- Tự hành động thay mặt người dùng, không chỉ trò chuyện

---

## 2. YÊU CẦU KỸ THUẬT BẮT BUỘC (mọi track, không có ngoại lệ)

Thiếu 1 trong 3 mục dưới đây → **rớt ngay ở Stage One (pass/fail)**, bất kể ý tưởng hay đến đâu.

| # | Bắt buộc | Lựa chọn |
|---|---|---|
| 1 | Model | **Gemini 3.5 hoặc mới hơn**, truy cập qua Gemini API hoặc Vertex AI |
| 2 | Agent Framework | Chọn ≥1: **Google ADK**, GenAI SDK, Antigravity SDK, hoặc Genkit |
| 3 | Google Cloud Infra | Chọn ≥1: Cloud Run, Cloud SQL, Firestore, GKE, Pub/Sub, ... |

---

## 3. BA TRACK (chỉ chọn 1) — DỰ ÁN NÀY CHỌN: **Collaborative Partner**

### 3.1 Taskmaster
Build workflow hoàn chỉnh, không chỉ chatbot. Agent giám sát sự kiện, phối hợp công cụ, hoàn thành workflow nhiều bước không cần giám sát liên tục. Tiêu chí BYOF (Bring Your Own Friction): phải là vấn đề cá nhân/nghề nghiệp có thật.

### 3.2 Collaborative Partner ✅ (TRACK ĐÃ CHỌN)
Build agent đồng hành: hỏi câu hỏi đúng, dẫn dắt người dùng qua thử thách phức tạp, học từ mỗi lần tương tác. Agent phải nhớ context, tiếp nhận feedback, và **trở nên hữu ích hơn theo thời gian** — không bắt đầu lại từ đầu mỗi lần.
> Ví dụ chính thức: "an expert guide that helps you understand a dense legal document, quizzes you as you go, learns which concepts you struggle with, and adapts future explanations."

### 3.3 Fortified Enterprise Fleet
Mạng lưới agent cấp doanh nghiệp: Agent Registry, Agent Runtime, Memory Bank, Agent Identity, Agent Gateway, Model Armor, Agent Observability.

### 3.4 Startup Excellence Prize (bổ sung)
Doanh nghiệp đã thành lập (email công ty) có thể apply thêm giải này khi làm 1 trong 3 track gắn với bài toán kinh doanh cụ thể.

---

## 3.5 GHI CHÚ VỀ TÊN GỌI KHÔNG NHẤT QUÁN TRONG RULES

Văn bản Rules gốc có 1 đoạn dùng tên khác cho 3 track (có vẻ là bản nháp cũ chưa đồng bộ hết):
- "The Continuous Action Engine" ≈ Taskmaster
- "The Evolving Knowledge Engine" ≈ Collaborative Partner
- "The Multi-Agent Nexus" ≈ Fortified Enterprise Fleet

**Khi nộp bài, LUÔN dùng tên chính thức trên Devpost: Taskmaster / Collaborative Partner / Fortified Enterprise Fleet.** Không dùng tên thay thế ở trên trong bất kỳ tài liệu nộp bài nào.

---

## 4. JUDGING — 3 STAGE

### Stage One (pass/fail)
Kiểm tra baseline: đủ submission requirements, có địa chỉ đúng challenge, áp dụng đúng yêu cầu kỹ thuật (mục 2).

### Stage Two (chấm điểm 1–5 mỗi tiêu chí, trung bình lại)

| Tiêu chí | Trọng số | Nội dung |
|---|---|---|
| **Innovation & Operational Utility** | **40%** | Agent loại bỏ được bao nhiêu friction thực tế **tự thân**? Thưởng cho hành động tự hành, giá trị cao, ít cần con người can thiệp — hơn là chat đơn thuần. |
| **Architectural Discipline & Tech Stack** | 30% | Quyết định kỹ thuật có vững không? Cách decouple hệ thống, quản lý state/memory, bảo mật credentials, xử lý lỗi — agent production-minded, không phải script mong manh. |
| **Demo & Production Readiness** | 30% | Video và repo chứng minh rõ ràng thế nào? Cần: demo live không chỉnh sửa, sơ đồ kiến trúc sạch, setup tái lập được, bằng chứng chạy trên Google Cloud. |

**Câu hỏi chấm điểm riêng theo từng track** (trích nguyên văn từ Rules — chỉ track Collaborative Partner áp dụng cho dự án này, 2 track kia để tham khảo/so sánh):

- **Taskmaster**: *"Does the agent successfully intercept and complete a multi-step background workflow without human intervention? Did the team successfully utilize the 'Bring Your Own Friction' (BYOF) mandate to solve a unique, personal problem?"*
- **Collaborative Partner** ✅ (track đã chọn): *"Does the agent actively synthesize or mutate data, rather than just reading it? Did the team ingest unusual, messy, or highly complex unstructured data streams?"*
- **Fortified Enterprise Fleet**: *"Is the task complex enough to warrant a multi-agents system? Does the system intelligently delegate tasks to specialized sub-agents? Did they build this for an 'Unlikely Hero' outside of standard corporate roles?"*

→ **2 câu hỏi của Collaborative Partner là CỐT LÕI** mà kiến trúc dự án phải trả lời được rõ ràng trong video: (1) agent phải tổng hợp/biến đổi dữ liệu, không chỉ đọc lại; (2) dữ liệu đầu vào phải đủ "khó" (phi cấu trúc/lộn xộn/phức tạp), không phải input sạch đơn giản.

**Tiêu chí bổ sung áp dụng cho mọi track** (từ Rules, phần Architectural Discipline và Demo):
> *"We are evaluating your engineering decisions, not just your ability to call an API. How well did your team decouple systems, manage state, and design robust, failure-tolerant agentic systems?"*
> **"Proof of Action"**: *"Does the video show an unedited, live execution of the agent performing its task (via terminal logs, database updates, or UI changes)?"*

### Stage Three (Bonus Contributions — cộng điểm)
- Publish nội dung (blog/podcast/video) về quá trình build, public, phải ghi rõ làm cho hackathon này → **+0.2 điểm**
- Đăng MXH kèm hashtag #AllThingsAgenticHackathon → **+0.2 điểm**
- Tích hợp thêm Google AI model khác (Gemma, Veo, Lyria) → tính vào Optional Developer Contributions

---

## 5. YÊU CẦU NỘP BÀI (What to Submit)

1. **URL hosted project** (nếu có) — khuyến khích mạnh, không bắt buộc
2. **Mô tả text**: features/functionality, technologies used, other data sources, findings & learnings
3. **Repo code** (public/private — nếu private phải share với `testing@devpost.com` và `cloudhackathons@google.com`)
4. **README.md — Spin-up Instructions**: hướng dẫn từng bước setup/run/deploy, viết như thể người lạ phải tự chạy được từ đầu
5. **Architecture Diagram**: Gemini kết nối backend/database/frontend ra sao — không cần đẹp, cần rõ
6. **Demo video ≤ 4 phút** (chỉ 4 phút đầu được chấm), public trên YouTube/Vimeo, tiếng Anh hoặc phụ đề tiếng Anh. Phải có:
   - Vấn đề + giá trị giải pháp
   - Nói rõ dùng Gemini model nào + agent framework nào (đừng giấu, nói thẳng)
   - Agent **thực sự làm việc** — log thật, record cập nhật thật, tin nhắn gửi thật. **KHÔNG mockup, không slideware.**
   - **Bằng chứng bắt buộc**: chạy trên Google Cloud (Cloud Console / Cloud Run dashboard / Vertex AI logs / .run URL)

---

## 6. ⚠️ RÀNG BUỘC QUAN TRỌNG NHẤT — "NEW PROJECTS ONLY" & VIỆC TÁI SỬ DỤNG CritiqAI

### 6.1 Nguyên văn điều khoản (Rules, dòng 91)
> *"Projects must be newly created during the Submission Period. Participants may use standard development tools, including frameworks, libraries, starter templates, and AI coding assistants, but must disclose any other pre-existing code or work incorporated into the Project. The work described and submitted must have been built during the Submission Period."*

### 6.2 Bối cảnh: dự án CritiqAI trước đó
Người dùng (Eiki Tomobe / Loc Nguyen Thi Phuoc) đã xây và **thắng giải** với CritiqAI (multi-agent AI debate coach, ADK) tại **Kaggle/Google AI Agents Intensive Vibe Coding Capstone 2026** (top 12/6000+ đội, giải Agents for Good - Education track). Source code đầy đủ được import vào project này để Claude Code tham khảo (xem phần 9 bên dưới).

### 6.3 Đánh giá rủi ro — Claude Code PHẢI tuân thủ nguyên tắc sau khi build

| Mức độ | Hành động | Được phép? |
|---|---|---|
| 🟢 An toàn | Dùng lại **ý tưởng/triết lý/pattern kiến trúc** (VD: Generate→Validate→Escalate, tách Validator độc lập khỏi Generator, HITL gate ở OAuth scope) nhưng **viết code hoàn toàn mới** | ✅ Luôn an toàn |
| 🟡 Cân nhắc | Copy vài đoạn code tiện ích nhỏ, không phải lõi (VD: 1 hàm regex check) | ⚠️ Chỉ nếu có khai báo rõ, tránh nếu không cần thiết |
| 🔴 Rủi ro cao | Copy nguyên khối logic 6-agent pipeline (Orchestrator/Summarizer/Persona Selector/Debate/Validator/Report) gần như y hệt, chỉ đổi model | ❌ **TRÁNH** — có thể vi phạm "must have been built during Submission Period" |

### 6.4 Chỉ thị cho Claude Code
- **Coi source code CritiqAI là TÀI LIỆU THAM KHẢO / CASE STUDY, KHÔNG PHẢI base code để fork.**
- Được phép: học pattern, học cách đặt tên agent, học cách chia trách nhiệm, học lỗi đã gặp (single-prompt chatbot → answer-leak) để **thiết kế lại từ đầu, tốt hơn**.
- Không được: copy-paste nguyên văn class/function lõi của pipeline debate cũ vào repo mới.
- Toàn bộ agent, prompt, schema Firestore, logic validator... của dự án MỚI phải được **viết mới trong Submission Period** (3/8–31/8/2026).
- Người dùng đã gửi email hỏi ban tổ chức (cloudhackathons@google.com) để xác nhận rõ hơn — **nếu có phản hồi mới, cập nhật section này trước khi tiếp tục.**
- Trong mô tả submission, PHẢI có disclosure: *"Kiến trúc lấy cảm hứng từ kinh nghiệm cá nhân của tác giả ở dự án CritiqAI (dự thi tại cuộc thi khác trước đây). Toàn bộ code trong submission này được viết mới hoàn toàn trong Submission Period của All Things Agentic Hackathon."*

---

## 7. CÂU CHUYỆN & VẤN ĐỀ CỐT LÕI (BYOF / Problem Framing)

**Bối cảnh:** Giáo dục ở nông thôn thiếu giáo viên nghiêm trọng. Học sinh không theo kịp bạn bè thành thị vì thiếu người kèm cặp cá nhân hoá. Giáo viên hiện có không đủ thời gian để theo sát từng em trong lớp đông.

**Nguyên tắc sư phạm cốt lõi (kế thừa từ CritiqAI):**
> *"Using AI to teach students not to depend on AI."*
Agent KHÔNG đưa đáp án, KHÔNG viết lại bài giúp học sinh — mà dùng phương pháp Socratic (tranh biện/gợi mở) để rèn tư duy phản biện. Đây là điểm khác biệt triết lý cốt lõi, phải thể hiện xuyên suốt trong UX và trong video.

**2 phía người dùng — 1 hệ thống thống nhất:**
- **Phía học sinh:** có "personal mentor" theo sát, nhớ persona/điểm yếu đã gặp qua nhiều bài luận, không lặp lại cách tiếp cận cũ, ngày càng cá nhân hoá.
- **Phía giáo viên:** không cần đọc từng báo cáo riêng lẻ — agent tự tổng hợp, xếp hạng học sinh nào cần chú ý trước, giáo viên vẫn là **gate quyết định cuối cùng** trước khi bất kỳ thông tin nào được gửi ra (email, thông báo phụ huynh...).

---

## 7.5 KIẾN THỨC KỸ THUẬT ADK (trích từ 3 workshop Google đã import vào project)

> Nguồn: `_Architecting_Multi-Agent_Teams...` (2 file), `_Build_a_Long-Running_Agent...`, `_Build_a_Self-Evolving_Agent...` — transcript workshop chính thức của Google Cloud cho hackathon này. Claude Code nên áp dụng trực tiếp các khái niệm này khi thiết kế Tầng 1 và Tầng 2.

### 7.5.1 Single Agent — điểm khởi đầu, nhưng có giới hạn rõ ràng
Một agent đơn với toàn bộ logic nhét vào 1 prompt: dễ làm, linh hoạt, nhưng **không đáng tin cậy** khi workflow phức tạp — vì LLM không deterministic, không đảm bảo luôn làm đúng thứ tự A→B→C, khó test từng bước, khó swap step. Nguyên tắc: **bắt đầu đơn giản, chỉ thêm phức tạp khi single agent thực sự không đáp ứng được.**

### 7.5.2 ADK 1.x — workflow agent cơ bản
- **LlmAgent**: agent cơ bản, cấu trúc cây (tree) — root agent + sub-agent, thường dùng làm **router pattern** (agent cha quyết định delegate cho sub-agent nào dựa trên reasoning của LLM — vẫn non-deterministic).
- **SequentialAgent**: đảm bảo chạy đúng thứ tự A→B→C.
- **ParallelAgent**: chạy đồng thời — nhưng **bắt buộc TẤT CẢ** sub-agent trong đó phải chạy song song, không chọn lọc được subset.
- **LoopAgent**: chạy lặp tới khi đạt điều kiện hoặc max iteration (đang dần deprecated).
- **Agent-as-tool**: bọc 1 agent thành tool thay vì sub-agent — giữ agent ở trạng thái **stateless**, cha vẫn giữ quyền kiểm soát (không mất control như khi delegate qua sub-agent thường).
- **Giới hạn cốt lõi của ADK1.x**: mọi node đều là "agent node" → non-deterministic; muốn mix sequential+parallel+loop lồng nhau thì được nhưng không linh hoạt/trực quan.

### 7.5.3 ADK 2 — Ba Pillar (Orchestration Patterns chính, ĐÂY LÀ TRỌNG TÂM)

**Nguyên tắc nền tảng của ADK2**: cho phép trộn **node xác định (deterministic — function node)** và **node không xác định (non-deterministic — agent node)** trong cùng 1 graph, thay vì mọi thứ đều phải là agent như ADK1. *"Functions prepare context, edges are the workflows, router decides the path, model synthesizes the answer."* → **luôn ưu tiên function/deterministic logic ở bất kỳ đâu không cần LLM reasoning**, chỉ dùng agent node khi thực sự cần suy luận.

| Pillar | Khi nào dùng | Đặc điểm |
|---|---|---|
| **1. Graph Workflow** | Biết trước luồng xử lý ngay từ lúc thiết kế (design time) | Kết hợp function node (deterministic, VD: fetch data, tính toán) + agent node (cần reasoning), nối bằng edge cố định. Có thể có router node với **rule cứng** (VD: if temperature > 70 → hot_strategy) thay vì để LLM tự quyết — tăng độ tin cậy, giảm token. Hỗ trợ fan-out/join (chạy song song 1 phần rồi gộp kết quả) |
| **2. Collaborative Pattern** | Không biết trước hình dạng chính xác của luồng, nhưng biết rõ **đội ngũ agent nào** có thể giải quyết | Agent cha có thể chạy 1 hoặc nhiều sub-agent tuỳ tình huống, qua 3 chế độ (xem 7.5.4) |
| **3. Dynamic Pattern** | Hình dạng luồng phụ thuộc hoàn toàn vào input, không thể biết trước | Hoàn toàn code-driven (Python): agent tự phân rã câu hỏi mở thành N câu hỏi con tại runtime, sinh ra N worker song song, có thể đệ quy (giới hạn bằng max depth để kiểm soát token) |

### 7.5.4 Ba chế độ (mode) khi gọi sub-agent trong ADK2
- **Chat mode**: giống ADK1 — cha delegate hết quyền kiểm soát cho sub-agent, không chạy song song được.
- **Single-turn mode**: sub-agent được bọc như 1 tool, **stateless**, cha giữ quyền kiểm soát → cho phép chạy song song nhiều sub-agent.
- **Task mode**: sub-agent có thể "đi lại nhiều vòng" (back-and-forth) để hoàn thành 1 tác vụ phức tạp trước khi trả kết quả về cho cha — không chỉ 1 lượt hỏi-đáp đơn giản.

### 7.5.5 Yếu tố quyết định số lượng agent / khi nào tách sub-agent (từ Q&A cuối workshop)
- **Context isolation**: nếu 2 việc cần ngữ cảnh khác nhau, không muốn 1 agent bị "nhiễu"/ảnh hưởng bởi context của việc kia → tách agent riêng.
- **Cần chạy song song** → tách để fan-out được.
- **Cần test độc lập từng phần** → tách để dễ viết eval riêng cho từng agent.
- **Có thể dùng model khác nhau cho từng sub-agent** tuỳ độ phức tạleast (agent đơn giản dùng Flash, agent cần reasoning sâu dùng Pro) — tối ưu chi phí.

**Ứng dụng trực tiếp cho dự án này**: Tầng 1 (Orchestrator→Summarizer→Persona Selector→Debate↔Validator→Report) nên thiết kế theo **Graph Workflow** (đã biết rõ thứ tự từ trước) với Validator là 1 **function node thuần regex** (deterministic, không tốn token) chứ không phải agent node. Tầng 2 (Class Aggregator quét nhiều học sinh, mức độ ưu tiên khác nhau tuỳ dữ liệu) phù hợp với **Collaborative Pattern hoặc Dynamic Pattern** vì số lượng học sinh "cần chú ý" thay đổi tuỳ input mỗi lần chạy.

### 7.5.6 ADK Session & Memory (từ workshop Long-Running Agent) — QUAN TRỌNG cho Memory Agent

Đây là kiến thức trực tiếp quyết định cách implement Tầng 2 (Memory Agent):

- **Session**: giống "web session" — giữ trạng thái hội thoại (session state) trong suốt 1 phiên làm việc liên tục (VD: 3 vòng debate của 1 bài luận). Session state mất đi khi phiên kết thúc, trừ khi cấu hình lưu bền (persistent).
- **Runner**: thành phần trung tâm định nghĩa nơi lưu session (SQLite cho local/dev, hoặc backend production như Firestore/Vertex), quản lý session service + memory service + artifact service.
- **Memory (khác Session)**: dùng để nhớ **xuyên nhiều session** — VD gắn prefix `user:` vào state để đánh dấu đây là thông tin cần nhớ lâu dài về 1 người dùng cụ thể, không chỉ trong 1 phiên. **Đây chính xác là cơ chế cần dùng cho `student_profile` xuyên nhiều bài luận/nhiều tuần.**
- **3 loại Memory Service ADK hỗ trợ**:
  1. **In-memory**: mất khi tắt máy — chỉ dùng để test/dev, KHÔNG dùng cho production.
  2. **RAG / semantic search**: lưu bền, tìm lại qua semantic similarity.
  3. **Memory Bank** (dịch vụ managed của Google): cũng hỗ trợ semantic search, quản lý memory chuyên biệt hơn.
- **Artifacts**: nơi lưu file/dữ liệu lớn gắn với session (khác với state — state dùng cho dữ liệu nhỏ, có cấu trúc).
- ADK tự động **compact** các event/lịch sử hội thoại cũ và đưa vào memory khi session kết thúc — không cần tự viết logic tổng hợp từ đầu.

**Khuyến nghị cụ thể cho dự án**: Memory Agent nên dùng **Firestore làm Session/Memory backend** (thay vì SQLite chỉ dùng cho local dev) — vừa thoả mãn yêu cầu GCP infra bắt buộc, vừa cho phép `student_profile` tồn tại bền vững xuyên nhiều tuần, đúng tinh thần "long-running agent" mà Google khuyến nghị trong chính workshop của họ.

### 7.5.7 Self-Evolving / Eval (từ workshop Self-Evolving Agent) — tham khảo cho Validator & Testing

- ADK có **eval framework** built-in: định nghĩa dataset đánh giá + metric (VD: response match score, trajectory match) để kiểm tra agent có "làm đúng việc" không.
- **Cảnh báo quan trọng — Reward Hacking**: nếu chọn sai metric/tiêu chí đánh giá, agent (hoặc quá trình tối ưu) có thể "lách" để đạt điểm cao mà không thực sự giải quyết đúng vấn đề. Bài học: nên tự viết **custom metric/judge** rõ ràng, deterministic khi có thể, thay vì chỉ dựa vào built-in metric chung chung.
- **Áp dụng cho dự án**: nếu có thời gian, nên viết 1 evalset nhỏ cho Debate Agent (VD: kiểm tra không có answer-leak, đúng persona được assign) — vừa tăng độ tin cậy, vừa là điểm cộng cho "Architectural Discipline" khi nói trong video *"chúng tôi có eval pipeline trước khi deploy"* — đúng tinh thần **build → eval → deploy** mà CritiqAI gốc cũng áp dụng qua `agents-cli`.

---

## 8. KIẾN TRÚC MỤC TIÊU — 2 TẦNG

```
                    TẦNG 1 — Per-Student Agent Pipeline (THIẾT KẾ MỚI, lấy cảm hứng pattern cũ)
[Bài luận học sinh] → Orchestrator → Summarizer → Persona Selector → Debate ↔ Validator → Score
                                                          ↑                                    |
                                                          |                                    ↓
                                                [Memory Agent — MỚI HOÀN TOÀN]  ←────  Firestore
                                                đọc/ghi lịch sử: persona đã dùng,
                                                điểm yếu lặp lại, xu hướng điểm
                                                qua nhiều bài luận theo thời gian
                                                          |
════════════════════════════════════════════════════════════════════════════════════════
                    TẦNG 2 — Class Aggregator Agent (MỚI HOÀN TOÀN, không có trong bản gốc)
                                                          |
                                    [Event-driven: Pub/Sub trigger khi có bài luận mới]
                                                          ↓
                                    Quét toàn bộ student_profile trong Firestore của lớp
                                    → phát hiện: học sinh kẹt ở cùng persona nhiều lần
                                      (không tiến bộ), pattern lỗi chung cả lớp,
                                      em nào lâu chưa nộp bài
                                    → TỰ xếp hạng ưu tiên "cần giáo viên chú ý trước"
                                                          ↓
                                    [Teacher Digest — báo cáo tổng hợp cả lớp]
                                                          ↓
                                    [Gmail MCP: compose-only — giáo viên vẫn là gate cuối]
```

### 8.1 Tầng 1 — Per-Student Agent (thiết kế mới, học pattern từ CritiqAI)
Vai trò tương tự bản cũ nhưng **code viết mới**:
- Orchestrator: nhận input, sanitize chống prompt injection, route session state
- Summarizer: nén bài luận, trích luận điểm chính + điểm yếu
- Persona Selector: chọn persona tranh biện (Skeptic / Devil's Advocate / Nitpicker / Expander) — **NÂNG CẤP MỚI**: đọc thêm lịch sử từ Memory Agent để không lặp lại persona đã dùng, ưu tiên nhắm điểm yếu DAI DẲNG qua nhiều bài
- Debate Agent: 3 vòng tranh biện leo thang, escalation logic để trong skill file riêng
- Challenge Validator: kiểm tra answer-leak, single-question rule, độ dài — ưu tiên rule-based/regex trước khi dùng LLM
- Analytics/Report Agent: tổng hợp báo cáo, ghi Firestore/Sheets, soạn email nháp (compose-only)

### 8.2 Tầng 2 — Memory Agent + Class Aggregator (MỚI HOÀN TOÀN — trọng tâm của submission này)
Đây là phần khác biệt lớn nhất so với CritiqAI gốc, và là câu trả lời trực tiếp cho:
- Yêu cầu track: *"remember context... become more helpful over time"*
- Yêu cầu kỹ thuật: thêm Firestore (Google Cloud service riêng biệt ngoài Cloud Run)
- Bài toán gốc: giáo viên quán xuyến nhiều học sinh cùng lúc

**Firestore schema gợi ý — `student_profile`:**
```
student_profile/{student_id}
  - name, class_id
  - essay_history: [{ essay_id, timestamp, persona_used, scores: {logical_coherence, evidence_quality, counterargument_handling, scope_awareness}, weakness_detected }]
  - persona_streak: { current_persona, times_repeated_without_improvement }
  - flags: { needs_attention: bool, reason: string, last_updated }
```

**Class Aggregator logic ưu tiên hoá (đề xuất, cần thiết kế cụ thể hơn):**
1. Học sinh kẹt ở cùng persona ≥ N lần liên tiếp không cải thiện điểm → ưu tiên cao
2. Điểm trung bình giảm dần qua các bài gần nhất → ưu tiên cao
3. Lâu chưa nộp bài (so với chu kỳ lớp) → ưu tiên trung bình
4. Pattern lỗi lặp lại giống nhau ở nhiều học sinh → gợi ý giáo viên dạy lại khái niệm chung cho cả lớp

### 8.3 Tech stack tổng hợp

| Thành phần | Công nghệ | ADK Pattern áp dụng (xem 7.5) |
|---|---|---|
| Model | Gemini 3.5 Flash (mặc định), Pro chỉ cho reasoning phức tạp cuối | — |
| Framework | Google ADK (ADK2) | Tầng 1 = Graph Workflow; Tầng 2 = Collaborative/Dynamic Pattern |
| Memory/State dài hạn | Firestore, dùng làm ADK Memory Service backend (prefix `user:`/`student:`) | Session & Memory (7.5.6) |
| Validator | Function node thuần Python/regex, KHÔNG phải agent node | Deterministic-first (7.5.3) |
| Router chọn ưu tiên (Class Aggregator) | Rule cứng trong code (VD: nếu persona_streak ≥ 3 → flag) trước, chỉ gọi LLM khi cần tổng hợp ngôn ngữ tự nhiên cho Teacher Digest | Deterministic router node (7.5.3) |
| Chạy nền/event | Cloud Run + Pub/Sub (event-driven khi có bài luận mới) | — |
| Input phi cấu trúc | Gemini multimodal nếu cần đọc ảnh chụp bài viết tay (optional, cân nhắc theo thời gian còn lại) | — |
| Email | Gmail MCP — compose-only, giáo viên bấm gửi | HITL gate (học từ CritiqAI, mục 9) |
| Audit log | Google Sheets MCP (append-only) | — |
| Eval (nếu kịp) | ADK eval framework, custom metric/judge cho Debate Agent | Self-evolving/Eval (7.5.7) |

---

## 9. THAM KHẢO KỸ THUẬT TỪ CritiqAI (case study — KHÔNG PHẢI base code để fork)

> Nhắc lại: phần này chỉ để Claude Code HIỂU PATTERN và BÀI HỌC THIẾT KẾ. Không copy code lõi. Xem ràng buộc ở mục 6.

**Nguồn gốc:** https://github.com/francisnguyenanh/CritqAI.git (repo cũ, đã thắng giải ở cuộc thi khác — dùng để đọc hiểu, không phải để fork)

### 9.1 Nguyên lý thiết kế đã được kiểm chứng (bài học, không phải code)
1. **Single-prompt chatbot sẽ luôn fail** khi phải đồng thời giữ persona + track history + score + format output → đây là lý do phải tách multi-agent, không phải vì "nghe hoành tráng hơn".
2. **Validator phải độc lập về logic/reasoning path với Generator** — Debate Agent và Challenge Validator không được dùng chung 1 lần gọi LLM, nếu không risk kiểm tra chính là risk cần kiểm tra.
3. **Deterministic-first**: luôn ưu tiên rule-based/regex/keyword trước khi gọi LLM, ở bất kỳ đâu có thể — tiết kiệm token + tăng khả năng audit (giáo viên hiểu được TẠI SAO có điểm đó).
4. **1 điểm HITL duy nhất ở bước rủi ro cao nhất** — không rải rác approval ở mọi bước trung gian (VD: chỉ cần giáo viên duyệt trước khi gửi email, không cần duyệt từng bước nội bộ).
5. **Least-privilege**, không chỉ ở tầng logic prompt — VD Gmail compose-only nghĩa là dù AI có "muốn" gửi, nó cũng KHÔNG THỂ về mặt kỹ thuật.
   > ⚠️ **CẬP NHẬT (Phase 0, test thật ngày 2026-08-24, xem TODO.md ADR-001):** giả định "OAuth scope `gmail.compose` chặn cứng `send()`" đã được kiểm chứng là SAI. Theo tài liệu chính thức của Google, `gmail.compose` bao gồm cả quyền gửi ("create, read, update, delete drafts; **send** messages and drafts") — test thật với token chỉ xin scope này cho thấy `messages.send()` vẫn thành công. Không có scope Gmail nào chỉ tạo draft mà chặn cứng gửi ở tầng Google.
   > **Thiết kế lại:** least-privilege cho Teacher Digest Mailer phải enforce ở **tầng code** (codebase không bao giờ gọi `messages.send`/`drafts.send` trong luồng digest — kỷ luật + code review/lint, không phải rào kỹ thuật của Google), và "gate" HITL thật sự là hành động người thật: giáo viên tự mở Gmail của họ và bấm Send trên draft, ngoài mọi code path hệ thống kiểm soát. Phải nói đúng điều này trong video/README — không được nói "OAuth chặn kỹ thuật".
6. **Agent giao tiếp qua shared session state, không gọi trực tiếp nhau** — giữ data lineage rõ ràng, từng agent test/thay thế độc lập được.

### 9.2 Pattern tổng quát rút ra (an toàn để tái sử dụng vì là khái niệm, không phải code)
**Generate → Validate → Escalate**, 4 nguyên tắc:
1. Orchestrator chỉ route, không tự sinh nội dung rủi ro
2. Validator độc lập về logic với thứ nó kiểm tra
3. Deterministic-first trước khi dùng LLM
4. 1 điểm HITL duy nhất ở bước rủi ro cao nhất

### 9.3 Hạn chế đã biết của bản cũ (tránh lặp lại hoặc cân nhắc cải thiện)
- Chỉ xử lý text-based essay, chưa multimodal
- Argument-scorer rule-based có thể bị "học tủ" (học sinh chèn từ khóa để qua mặt)
- Chưa có memory dài hạn xuyên nhiều buổi học — **đây chính là gap mà dự án MỚI phải lấp (Tầng 2)**
- Debate Agent đôi khi "tuột persona" giữa chừng (mất chất adversarial, chuyển sang giọng trợ lý dễ dãi) — cần persona anchoring mạnh hơn trong prompt mới

---

## 10. LỊCH TRÌNH 7 NGÀY (tham khảo, điều chỉnh theo eligibility email phản hồi)

| Ngày | Việc |
|---|---|
| 1 | Chốt scope, setup ADK + Gemini 3.5 + Firestore skeleton — bắt đầu viết MỚI (không fork) |
| 2–3 | Build Tầng 1 (Orchestrator → Summarizer → Persona Selector → Debate ↔ Validator) — chạy end-to-end được |
| 4 | Build Memory Agent (Firestore) — Persona Selector đọc lịch sử |
| 5 | Build Class Aggregator + Teacher Digest — chạy trên Cloud Run/Pub/Sub thật |
| 6 | Deploy Cloud Run, chụp bằng chứng GCP, viết README, vẽ architecture diagram |
| 7 | Quay + edit video 4 phút, viết mô tả, nộp sớm 1 ngày dự phòng |

**Lưu ý khi quay demo:** được phép giả lập việc "nộp bài luận" xảy ra đúng lúc quay (input giả lập hợp lệ), nhưng agent phải xử lý THẬT (log thật, Firestore ghi thật) — không được dàn dựng sẵn output. Nên seed trước 4–5 student_profile với lịch sử khác nhau để Class Aggregator có dữ liệu đủ phong phú để thể hiện giá trị khi demo.

---

## 11. RỦI RO CẦN NÉ (checklist nhanh)

- [ ] Đủ 3 yêu cầu bắt buộc (Gemini 3.5+, ADK, GCP service) — thiếu 1 = rớt Stage One
- [ ] Không copy nguyên lõi code CritiqAI — chỉ học pattern (xem mục 6)
- [ ] Có disclosure rõ ràng về CritiqAI trong mô tả submission
- [ ] Video ≤ 4 phút, có bằng chứng GCP, không mockup/slideware
- [ ] README có spin-up instructions rõ ràng, test lại bằng incognito window nếu repo private
- [ ] Không để lộ API key trong repo public (.env + .gitignore)
- [ ] Track ghi đúng "Collaborative Partner" trong form nộp bài (không được ghi tên track không tồn tại)
- [ ] Sau deadline (31/8 17:00 PT) — TUYỆT ĐỐI không sửa gì trong repo/video/link

---

## 12. VIỆC ĐANG CHỜ XỬ LÝ

> Cập nhật 2026-08-24, sau khi hoàn thành Phase 0–4 + "ĐỀ XUẤT CẢI TIẾN ĐỢT 1 & 2" trong TODO.md. Các mục cũ dưới đây đã có câu trả lời thật (xem TODO.md để có chi tiết đầy đủ từng bước verify) nên không còn là "đang chờ" nữa — giữ lại có gạch để tra cứu lịch sử quyết định, không xoá.

**Đã chốt (không còn chờ nữa):**
- [x] Eligibility CritiqAI: chưa nhận phản hồi chính thức từ `cloudhackathons@google.com`, nhưng đã tự áp dụng nguyên tắc an toàn nhất trong lúc chờ — 100% code mới, disclosure rõ trong Devpost (xem mục 6, TODO.md Phase 8). Nếu có phản hồi khác đi, cập nhật lại mục 6.
- [x] Class Aggregator: **event-driven qua Pub/Sub**, đã build và verify thật ở Phase 3 (topic + DLQ + subscription thật trên GCP, chaos test thật ở Phase 4) — không dùng Cloud Scheduler.
- [x] Multimodal (OCR ảnh viết tay): dời có chủ đích sang Phase 6, đặt SAU Tầng 2 để không đe doạ xương sống nếu hết thời gian (xem TODO.md "Rủi ro & phương án dự phòng").

**Quyết định kiến trúc mới phát sinh khi làm "ĐỀ XUẤT CẢI TIẾN ĐỢT 2" (TODO.md), chưa có ADR riêng trong README/mục 9 nên ghi tạm ở đây:**
- **Bilingual (VI/EN) chỉ áp dụng ở lớp diễn đạt, không áp dụng ở lớp phân loại nội bộ.** `summarizer.fallacies_draft` LUÔN giữ thuật ngữ tiếng Anh chuẩn (`"hasty generalization"`, ...) bất kể ngôn ngữ bài luận, vì `persona_selector` match persona bằng regex tiếng Anh trên chính field này — dịch nhãn nguỵ biện sang tiếng Việt sẽ âm thầm làm hỏng logic chọn persona (lỗi sẽ không ném exception, chỉ chọn persona sai). Chỉ nội dung học sinh THỰC SỰ đọc (câu hỏi debate, `student_feedback`) mới đổi ngôn ngữ theo `detect_language()` (deterministic, zero LLM — cùng triết lý mục 9.1 nguyên tắc #3).
- ~~**Interactive Debate Step Helper (`interactive.py`) dùng session state in-process (dict), KHÔNG dùng Firestore.**~~ **ĐÃ BỊ THAY THẾ bởi ADR-015 (ĐỢT 10), và ADR-015 lại được sửa ở ĐỢT 12.** Chính điều kiện mà mục này ghi nợ ("nếu sau này cần chạy nhiều Cloud Run instance") đã xảy ra thật: một phiên tranh biện 3 lượt là 3+ HTTP request, Cloud Run load-balance qua nhiều instance, nên state in-process làm mất phiên giữa cuộc. Hiện tại session nằm ở `debate_sessions/{session_id}` trên Firestore (`memory/firestore_session.py`), dict in-process **hạ cấp thành read cache 3 giây**. ĐỢT 12 phát hiện bản ADR-015 đầu tiên vẫn ưu tiên cache trong suốt 24h TTL của session → lượt 3 quay về instance A đọc bản cũ rồi ghi đè Firestore, tức đúng bug mà ADR-015 tuyên bố đã sửa. Ranh giới Session vs Memory (mục 7.5.6) KHÔNG bị phá: `debate_sessions` vẫn là Session (ngắn hạn, có `expire_at` + TTL policy ACTIVE, bị xoá bởi `end_debate_session()`); Memory dài hạn vẫn chỉ là `student_profiles`.
- **Digest lịch sử (`class_analytics/{class_id}/digests/{digest_id}`) dùng chính `event_id` làm `digest_id`.** Không sinh UUID riêng — tận dụng luôn tính idempotent đã có sẵn từ `processed_events` (Phase 3): một event bị redeliver ghi đè đúng 1 document thay vì tạo bản ghi lịch sử trùng lặp.

**Quyết định kiến trúc mới phát sinh khi làm "ĐỀ XUẤT CẢI TIẾN ĐỢT 3 / 6 TRỤ CỘT" (TODO.md), chưa có ADR riêng trong README nên ghi tạm ở đây:**
- **Digest coalescing (debounce) hoạt động trên "đã có digest gần đây" cho `class_id`, không phải "đã có essay gần đây" cho `student_id`.** Lý do: mỗi lần Tầng 2 chạy đều đọc lại TOÀN BỘ profile của cả lớp (`load_class_profiles`), nên bỏ qua việc sinh digest mới cho 1 event không làm mất dữ liệu — event tiếp theo của lớp đó (từ bất kỳ học sinh nào) sẽ tự động phản ánh cả bài vừa bị coalesce. Nếu debounce theo `student_id` thay vì `class_id`, sẽ cần thêm logic hàng đợi riêng phức tạp hơn nhiều mà không cần thiết ở quy mô 1 lớp/1 giáo viên.
- ~~**Interactive REST API (`api.py`) KHÔNG chạm `cognitive_scorer`/`profile_mutator`.**~~ **ĐÃ LỖI THỜI từ ĐỢT 5/ĐỢT 9** — `interactive.complete_debate_session()` giờ gọi `score_essay()` (dùng chung hàm với graph node, không phải bản sao) rồi `apply_essay_result()` + publish Pub/Sub, nên Web UI hiện CÓ hiển thị điểm/radar và CÓ mutate profile thật. Nguyên tắc chống trùng lặp vẫn được giữ bằng cách khác: cả 2 đường đều gọi CÙNG hàm `score_essay()`/`apply_essay_result()`, không viết lại logic lần thứ hai. Đoạn gạch dưới đây giữ lại làm lịch sử quyết định. Bản gốc: `start_debate()`/`start_debate_from_image()`/`submit_debate_turn()` dừng lại ở cuối turn 3 (transcript xong), không tự chấm điểm hay ghi Firestore student_profiles. Lý do: 2 node đó vẫn thuộc về ADK2 graph, chạy qua `Context` — viết lại logic chấm điểm/mutate profile lần 2 ở tầng REST (không có `Context`) sẽ tạo ra 2 cài đặt độc lập cho cùng 1 hành vi, đúng rủi ro mà `interactive.py`'s docstring đã cảnh báo cho debate turns. Hệ quả: trang demo Web UI hiện KHÔNG hiển thị điểm/Cognitive Profile sau khi tranh biện xong — batch pipeline (`scripts/demo_tier1_run.py`, hoặc graph thật) vẫn là đường DUY NHẤT một essay được chấm điểm + mutate profile thật.
- **OCR qua REST (`start_debate_from_image`) dùng lại `transcribe_essay_image()` (tách ra từ `nodes/ocr.py`), nhưng KHÔNG park vào `pending_essays` khi confidence thấp.** Cơ chế `pending_essays` (Phase 4/6) chỉ có ý nghĩa khi có 1 `profile_mutator` thật sự định ghi/không ghi Firestore — REST path này không mutate Firestore ở bất kỳ nhánh nào (xem điểm trên), nên "confidence thấp" ở đây chỉ là 1 field cảnh báo (`ocr.degraded`) trả về cho UI hiển thị cho học sinh biết, không có ý nghĩa "essay này có được tính vào hồ sơ hay không".
- **`thinking_budget` là optional kwarg mặc định `None` (giữ hành vi cũ), không phải 1 config toàn cục.** Chỉ 2 call site (`ocr.py`, `summarizer.py`) truyền `thinking_budget=0` — Scorer và Digest Synthesizer cố tình không đổi, vì 2 node đó cần suy luận sâu hơn (chấm điểm/tổng hợp báo cáo), khác với OCR/Summarizer (trích xuất cấu trúc thuần).
- **Session TTL (`interactive.py`) quét lazy, không dùng cron/scheduler riêng.** `evict_stale_sessions()` chạy mỗi lần `start_debate_session()` được gọi — đủ để chặn leak không giới hạn trên 1 Cloud Run instance sống lâu, mà không cần thêm hạ tầng (Cloud Scheduler, background thread riêng) chỉ để dọn dẹp state tạm.

**Quyết định kiến trúc mới phát sinh khi làm "ĐỢT 12 — AUDIT TOÀN DIỆN" (TODO.md), đã có ADR chính thức trong README:**

- **ADR-016 — Khoá ký session phải đến từ Secret Manager; tiến trình TỪ CHỐI KHỞI ĐỘNG nếu không có.** `auth.py::_resolve_session_secret()` phát hiện Cloud Run qua biến `K_SERVICE` và raise nếu `EDUAGENT_SESSION_SECRET` chưa set / vẫn là default đã commit / ngắn hơn 32 ký tự. Bối cảnh: audit phát hiện service live chưa từng được set biến này, tức đang ký token bằng chuỗi công khai trong repo — ai đọc repo cũng tự ký được token `role=teacher` cho lớp bất kỳ, vô hiệu hoá hoàn toàn ADR-013. Lý do chọn "chết hẳn" thay vì "log cảnh báo": biến môi trường thiếu là lỗi im lặng, đã im lặng suốt cả vòng đời deployment; container không boot được là lỗi ồn ào.
- **ADR-017 — Implement rate limiting thật thay vì xoá claim khỏi bảng STRIDE.** Bảng STRIDE ghi "Token bucket rate limiting" nhưng `grep` ra 0 kết quả trong `src/`. Nguy cơ là thật (mỗi call tranh biện fan-out thành nhiều request Gemini trên URL public), nên hướng xử lý đúng là xây, không phải rút claim. `rate_limit.py` là token bucket theo IP, **per-process** — trần thật là `N_instances × capacity`; ràng buộc chi phí và chặn lạm dụng thường, KHÔNG phải rate limiter phân tán. Giới hạn này được ghi thẳng vào docstring + bảng STRIDE + README thay vì để người đọc tự suy ra.
- **ADR-018 — 5 endpoint tranh biện của học sinh phải có token, `role=student` chỉ hành động thay chính mình.** Trước đó chúng nhận `student_id` tuỳ ý không kiểm token nào, trong khi mọi route `/api/classes/*` đều đã gate — trên service `--allow-unauthenticated`. Với `/api/debate/turn` (payload chỉ có `session_id`), quyền sở hữu suy ra từ `student_id`/`class_id` lưu trong session, và token được verify **TRƯỚC** khi tra session — nếu không, route trở thành oracle phân biệt `session_id` thật (403) với bịa (404); chính test viết trong ĐỢT 12 bắt được lỗi thứ tự này. Token `teacher` cùng lớp vẫn được chấp nhận vì giáo viên tái hiện phiên của học sinh là hành động hợp lệ.
- **ADR-019 — Mọi eval case phải có khả năng FAIL, và phải chứng minh bằng sabotage test.** Audit tìm ra 12/50 case không thể fail: 8 case "cognitive growth" của Layer 4 làm phép trừ trên hằng số khai trong chính file fixture (`8 - 2 >= 4`, xanh cả khi xoá sạch `src/`), và nhóm persona-fidelity tự nối chuỗi system instruction trong test rồi assert anchor có trong chuỗi vừa nối. Cả hai giờ gọi code production. Kiểm chứng: bỏ persona anchoring → 4/4 case FAIL; xoá artifact đo lường → 4/4 case Layer 4 FAIL. **Bài học tổng quát: reward hacking không cần reward model** — một con người viết assertion lặp lại chính setup của nó cũng tạo ra đúng loại metric vô giá trị đó.
- **Learning outcome: đo thật bằng scorer production, chấp nhận con số nhỏ hơn.** `scripts/evaluate_learning_outcomes.py` trước đây khai `before_scores`/`after_scores` là hằng số gõ tay rồi trừ, và báo cáo còn ghi "Chấm lại độc lập" cho hành vi không tồn tại. Nay chạy `summarize_essay()` → `score_essay()` thật qua Vertex AI, scorer chỉ thấy 1 văn bản mỗi lần và không được cho biết đâu là bản chỉnh sửa. Kết quả: **+2.75** (không phải +5.62), **7/8** kịch bản (không phải 8/8). Chọn giữ nguyên kịch bản không cải thiện thay vì nới ngưỡng cho đủ 8/8.
- **`--live-persona` là chế độ opt-in, ghi ra báo cáo RIÊNG.** Suite mặc định phải giữ được đảm bảo "zero LLM call", nên một lần chạy có gọi Gemini không được ghi đè `eval_report.md`. Kết quả live hiện tại được công bố nguyên trạng: **2/4 persona bị drift** sang giọng Skeptic trên bài luận khó — anchoring giữ được câu lệnh trong prompt, nhưng không bảo đảm model tuân thủ. Không nới lexicon để test xanh, vì đó chính là reward hacking mà ADR-019 vừa cấm.
- **Ngưỡng "lỗi chung của lớp" chốt ở 2 học sinh khác nhau, không phải 3.** Doc từng ghi ≥3 trong khi code là 2. Chọn giữ 2 và sửa doc: phát biểu sư phạm là "đây không phải lỗi riêng của một em", và 2 học sinh độc lập đúng là điểm mà phát biểu đó bắt đầu đúng; ngưỡng 3 cũng chưa từng được verify và gần như không đạt được trong lớp demo 5 em. `common_fallacies()` nhận tham số nên deployment lớp 40 em nâng lên được mà không sửa module.
- **Bỏ cơ chế tắt code path bằng `PYTEST_CURRENT_TEST`, thay bằng dependency injection.** `interactive.complete_debate_session()` từng bọc toàn bộ ghi Firestore + publish Pub/Sub trong `and not os.getenv("PYTEST_CURRENT_TEST")`. Điều đó không chỉ giữ test offline mà làm code path **không thể chạm tới từ bất kỳ test nào** — nên tính năng ĐỢT 9 tuyên bố "đã sửa xong" và Task 10.5 đều có 0 test bảo vệ, và "190/190 pass" không nói gì về chúng. Nay quyết định nằm trong seam tiêm được (`persist_essay_result`/`publish_event`/`client=`), vừa giữ offline-by-default vừa cho test assert payload thật.

**Quyết định kiến trúc mới phát sinh khi làm "ĐỢT 15" (review ngoài lần 2), đã có ADR chính thức trong README:**

- **ADR-021 — `interactive.py` là kiến trúc đúng cho graph FunctionNode, không phải bridge tạm.** Suốt từ Phase 1, TODO ghi rằng sẽ thay nó bằng cơ chế interrupt/resume của ADK2 Workflow (`RequestInput`, *"đã thấy trong `google.adk.workflow`"*). ĐỢT 15 verify: **câu đó sai**. `google.adk.workflow` (google-adk 2.3.0) chỉ export `BaseNode, DEFAULT_ROUTE, Edge, FunctionNode, JoinNode, Node, NodeTimeoutError, RetryConfig, START, Workflow`; import `RequestInput` từ đó raise `ImportError`. `RequestInput` thật ở `google.adk.events.request_input`, được `_request_input_tool` bọc thành `LongRunningFunctionTool` cho luồng `llm_flows` — graph toàn `FunctionNode` không đi vào luồng đó. Dùng được thì phải đổi debate node thành `LlmAgent` gọi tool, tức trao model quyền quyết persona anchoring/escalation/termination, phá deterministic-first. **Hệ quả:** món "nợ kỹ thuật" tồn 4 phase thực chất không phải nợ; đã đảo kết luận và đính chính ở `TODO.md:133`, docstring `interactive.py`, README ADR-021.
- **Nguyên tắc mới: credit sai cũng phải verify như chỉ trích sai.** Review lần 2 ghi dự án "có circuit breaker" trong phần cho 5.0/5.0 Architectural Discipline. `grep -rniE "circuit.?breaker" src/` → **0 kết quả**. Đã từ chối, và cố ý **không** để câu đó lọt vào tài liệu nào — đây đúng lớp lỗi ĐỢT 12 phải sửa cả đợt (mô tả biện pháp không tồn tại trong tài liệu kiến trúc), nhưng nguy hiểm hơn vì nó đến dưới dạng lời khen nên dễ được copy mà không ai kiểm.
- **Latency multimodal: đo, không đoán.** Review dự đoán OCR gây `504 Deadline Exceeded` trên Cloud Run. Đo thật: OCR 2 lượt = **22.5s**, cả luồng `start-with-image` = **24.2s**, Cloud Run timeout = **300s** ⇒ headroom ~12x, không có rủi ro 504. Rủi ro thật là **24s chết lặng trong video 240s** — vấn đề kịch bản, xử lý ở `docs/video_script.md` (nói lấp vào đúng beat OCR), không phải vấn đề config.

**Quyết định kiến trúc phát sinh khi làm "ĐỢT 15 — Senior Staff Engineer Audit" (2026-08-26), đã có ADR chính thức trong README:**

- **ADR-022 — reflection phải gắn vào một phiên tranh biện đã hoàn thành, và chỉ được dùng một lần.** `/api/debate/reflect` từng nhận `student_id`, `class_id`, `original_claim`, `original_fallacy` trực tiếp từ client, không gắn với phiên nào. Một sai sót thiết kế duy nhất đó sinh ra **hai lỗ hỏng** (nên đóng bằng **một** thay đổi): (1) *farm điểm* — gọi trần endpoint là được cộng `growth_bonus`/`breakthrough_count` dù không có bài luận và không có tranh biện nào; ADR-018 chặn việc bơm điểm cho **người khác** nhưng không chặn tự bơm cho chính mình — và cái sau tệ hơn cho sản phẩm, vì chỉ số metacognitive mà giáo viên đọc không còn nghĩa là "em này đã sửa lại cách nghĩ của mình"; (2) *prompt injection* — `original_claim`/`original_fallacy` được nhúng thẳng vào prompt Gemini không qua sanitize, trong khi chỉ `revised_claim` được làm sạch — vi phạm ADR-012 tại đúng endpoint không ai rà lại sau khi ADR-012 được viết. **Cách sửa:** payload chỉ còn `session_id` + `revised_claim`; mọi trường khác đọc từ session server-side — không còn gì để forge, và không phát sinh sanitizer thứ hai (bài luận đã được sanitize từ intake trước khi lưu). **Hệ quả về vòng đọi session:** `complete_debate_session()` **không còn xóa** session — nó đánh dấu `completed` và giữ lại (vẫn 24h `expire_at`/TTL), vì bước reflection diễn ra **sau** khi debate xong, nên xóa bằng chứng ngay lúc hoàn thành chính là thứ buộc endpoint sau đó phải tin client. Phiên đã `completed` là **terminal**: `step_debate_turn()` từ chối thêm lượt (không phụ thuộc số turn), và `submit_reflection()` mới là chỗ tear down thật. Cờ `has_reflected` ghi **trước** khi gọi LLM để double-click không ăn được 2 bonus trong lúc request đầu còn đợi Gemini. Điều này **không** làm nhòe ranh giới Session-vs-Memory (mục 7.5.6): `debate_sessions` vẫn là session (ngắn hạn, có TTL, xóa khi xong), long-term memory vẫn chỉ là `student_profiles`.
- **ADR-023 — `score_trend` có thêm verdict `volatile`; độ dốc tính bằng hồi quy, không bằng `sum(diffs)/len(diffs)`.** Biểu thức cũ **telescoping** (`(x1-x0)+(x2-x1) = x2-x0`) nên chỉ đọc bài đầu và bài cuối của cửa sổ. **Nói cho đúng:** ở `TREND_WINDOW == 3`, OLS cho ra **đúng cùng một số** (`(y2-y0)/2`), nên nửa này là sửa để code nói đúng điều nó tính và vẫn đúng nếu ai đó nới cửa sổ — không phải thay đổi hành vi. **Nửa còn lại mới là vấn đề thật mà audit chỉ ra:** học sinh `[10, 0, 10]` có xu hướng phẳng thật, nên bị xếp `stagnant` và góp **0** vào Priority Index — xếp ngang học sinh giữ điểm 5 đều đặn, dù một em sụp hẳn một bài. Giải pháp: giữ độ dốc đúng nghĩa của nó, và báo biên độ như một tín hiệu riêng (`volatile` khi biên độ peak-to-trough ≥ 2.0 điểm mà độ dốc vẫn trong flat band), có trọng số riêng `score_volatility = 1.5` — **dưới** `score_decline = 2.5`, vì sụt kéo dài vẫn đáng lo hơn bất ổn đã hồi. **Đã cân nhắc và loại:** gán thẳng cho dip nhãn `declining` để nó lên hạng — đúng học sinh nhưng sai lý do, và cái sai đó chạy tiếp vào parent note (`skills/parent_note.py` đọc chính `reason` block đó), tức nói với phụ huynh một điều không đúng.
- **Lỗi nền tảng đa nền tảng: `subprocess.run(["gcloud", ...])` chết trên Windows.** gcloud trên Windows là `gcloud.cmd`, không có binary không phần mở rộng, nên `scripts/doctor.py` và `scripts/deploy_to_cloud_run.py` raise `FileNotFoundError` — đúng trên loại máy mà giám khảo hay chạy nhất. Đã đổi sang `shutil.which()` (tôn trọng PATHEXT) thay vì `shell=True`, và check trong doctor giờ degrade thành WARN thay vì làm sập cả lần chạy. Có test AST (`tests/test_doctor_gcloud_resolution.py`) chặn việc tái xuất hiện chuỗi `"gcloud"` trần.

---

*Tài liệu này nên được cập nhật liên tục trong quá trình build — coi đây là "wiki sống" của dự án, không phải tài liệu tĩnh.*
