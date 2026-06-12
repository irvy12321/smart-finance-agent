# RBAC 权限系统实现总结

## 实现完成

已成功为 Smart Finance Agent 实现轻量级 RBAC 权限系统。

## 角色定义

| 角色 | 说明 | 默认 |
|------|------|------|
| `admin` | 管理员，拥有全部权限 | - |
| `analyst` | 分析师，可使用研究功能 | - |
| `viewer` | 查看者，仅查看报告 | ✓ |

## 权限矩阵

| 功能 | Admin | Analyst | Viewer |
|------|:-----:|:-------:|:------:|
| 用户管理 | ✓ | ✗ | ✗ |
| 系统配置 | ✓ | ✗ | ✗ |
| 创建研究任务 | ✓ | ✓ | ✗ |
| 执行研究任务 | ✓ | ✓ | ✗ |
| AI 对话 | ✓ | ✓ | ✗ |
| RAG 知识库管理 | ✓ | ✓ | ✗ |
| 删除 RAG 文档 | ✓ | ✗ | ✗ |
| 金融工具 | ✓ | ✓ | ✗ |
| 查看报告 | ✓ | ✓ | ✓ |
| 查看系统状态 | ✓ | ✓ | ✓ |

## 修改文件清单

### 后端文件 (11 个)

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `backend/app/auth/roles.py` | **新增** | 角色枚举、权限映射、权限检查函数 |
| `backend/app/auth/models.py` | **修改** | UserResponse 添加 role 字段 |
| `backend/app/auth/__init__.py` | **修改** | create_token_pair 添加 role 参数 |
| `backend/app/auth/dependencies.py` | **修改** | 添加 require_role() 和 require_permission() |
| `backend/app/api/auth.py` | **修改** | 注册/登录返回 role |
| `backend/app/api/task.py` | **修改** | 添加角色依赖 |
| `backend/app/api/chat.py` | **修改** | 添加角色依赖 |
| `backend/app/api/tools.py` | **修改** | 添加角色依赖 |
| `backend/app/api/rag.py` | **修改** | 添加角色依赖 (DELETE/REINDEX 仅 Admin) |
| `backend/app/storage.py` | **修改** | 添加 role 列 migration |

### 前端文件 (4 个)

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `frontend/src/types/api.ts` | **修改** | UserResponse 添加 role 字段 |
| `frontend/src/contexts/AuthContext.tsx` | **修改** | 添加 hasRole/hasAnyRole/isAdmin 等方法 |
| `frontend/src/components/ProtectedRoute.tsx` | **修改** | 支持 roles 属性检查 |
| `frontend/src/components/Sidebar.tsx` | **修改** | 菜单权限过滤，显示角色徽章 |
| `frontend/src/App.tsx` | **修改** | 路由配置 |

## 核心实现

### 1. 角色定义 (`auth/roles.py`)

```python
class Role(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

ROLE_PERMISSIONS = {
    Role.ADMIN: ["user:manage", "system:manage", "task:create", ...],
    Role.ANALYST: ["task:create", "chat:use", "rag:manage", ...],
    Role.VIEWER: ["report:view", "system:view"],
}
```

### 2. 权限依赖 (`auth/dependencies.py`)

```python
def require_role(*roles: Role):
    """FastAPI dependency to require specific roles"""
    def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in [r.value for r in roles]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker
```

### 3. API 端点使用

```python
@router.post("/task/create")
async def create_task(
    ...,
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST))
):
    """Only Admin and Analyst can create tasks"""
    ...
```

### 4. JWT Payload

```json
{
    "user_id": 1,
    "username": "john_doe",
    "role": "analyst",
    "exp": 1718123456,
    "type": "access"
}
```

### 5. 前端菜单控制

```typescript
const allNavigation = [
    { name: 'Dashboard', href: '/', roles: ['admin', 'analyst', 'viewer'] },
    { name: 'Research', href: '/research', roles: ['admin', 'analyst'] },
    { name: 'Chat', href: '/chat', roles: ['admin', 'analyst'] },
    { name: 'RAG', href: '/rag', roles: ['admin', 'analyst'] },
    { name: 'System', href: '/system', roles: ['admin', 'analyst', 'viewer'] },
]

const navigation = allNavigation.filter(item => hasAnyRole(item.roles))
```

## 验证结果

```
Roles: ['admin', 'analyst', 'viewer']
Default role: viewer
Admin has user:manage: True
Viewer has task:create: False
require_role imported successfully
require_permission imported successfully
```

## 使用示例

### 注册 (默认 viewer)
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'

# 响应包含 role: "viewer"
```

### 登录
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'

# 响应包含 role: "viewer"
```

### 访问受限端点
```bash
# Viewer 尝试创建任务
curl -X POST http://localhost:8000/api/task/create \
  -H "Authorization: Bearer <viewer_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze Tesla stock"}'

# 响应: 403 Forbidden
# {"detail": "Insufficient permissions. Required roles: ['admin', 'analyst']"}
```

## 扩展性

### 添加新角色

1. 在 `auth/roles.py` 添加角色枚举
2. 在 `ROLE_PERMISSIONS` 添加权限映射
3. 在 API 端点使用新角色

### 添加新权限

1. 在 `PERMISSIONS` 添加权限定义
2. 在 `ROLE_PERMISSIONS` 为角色添加权限
3. 在 API 端点使用 `require_permission()`

---

**实现完成，可投入使用。**
