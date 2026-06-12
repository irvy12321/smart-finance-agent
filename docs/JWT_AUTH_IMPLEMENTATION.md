# JWT 认证体系实现总结

## 实现完成

已成功为 Smart Finance Agent 实现完整的 JWT 认证体系，包括 Refresh Token 和自动刷新机制。

## 核心特性

### 1. Access Token
- **过期时间**: 15 分钟 (从 24 小时缩短)
- **类型标识**: `type: "access"` 防止误用
- **无状态验证**: 任何实例可验证

### 2. Refresh Token
- **过期时间**: 7 天
- **存储方式**: SHA256 哈希后存入数据库
- **安全生成**: `secrets.token_hex(64)` 生成 128 字符随机 token
- **Token 轮换**: 每次刷新生成新 token，旧 token 立即失效

### 3. API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/register` | POST | 注册，返回 access_token + refresh_token |
| `/auth/login` | POST | 登录，返回 access_token + refresh_token |
| `/auth/refresh` | POST | 刷新，返回新 access_token + 新 refresh_token |
| `/auth/logout` | POST | 登出，撤销 refresh_token |
| `/auth/me` | GET | 获取当前用户信息 |

### 4. 前端自动刷新
- **401 拦截**: 自动检测 token 过期
- **刷新锁**: 防止并发刷新
- **请求队列**: 刷新期间的请求自动排队
- **自动重试**: 刷新成功后自动重试失败的请求

## 修改文件清单

### 后端文件 (7 个)

| 文件 | 修改内容 |
|------|----------|
| `backend/app/auth/__init__.py` | 重写：添加 Refresh Token 生成、验证、轮换函数 |
| `backend/app/auth/models.py` | 更新：添加 `refresh_token` 到 Token 模型，新增 RefreshTokenRequest、LogoutRequest |
| `backend/app/auth/dependencies.py` | 更新：添加 Refresh Token 数据库操作函数 |
| `backend/app/api/auth.py` | 重写：实现双 Token 登录、Token 轮换刷新、登出 |
| `backend/app/storage.py` | 更新：添加 `refresh_tokens` 表 |
| `backend/.env.example` | 更新：添加 ACCESS_TOKEN_EXPIRE_MINUTES、REFRESH_TOKEN_EXPIRE_DAYS 配置 |
| `backend/app/main.py` | 无变化 (已正确配置) |

### 前端文件 (3 个)

| 文件 | 修改内容 |
|------|----------|
| `frontend/src/types/api.ts` | 更新：Token 接口添加 refresh_token，新增 RefreshTokenRequest、LogoutRequest |
| `frontend/src/contexts/AuthContext.tsx` | 重写：支持 Refresh Token 存储、自动刷新、登出时撤销 |
| `frontend/src/services/api.ts` | 重写：实现 401 自动刷新、刷新锁、请求队列、自动重试 |

## 数据库变更

### 新增表：refresh_tokens

```sql
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    token_hash      TEXT NOT NULL UNIQUE,
    expires_at      TEXT NOT NULL,
    revoked         BOOLEAN DEFAULT 0,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## 配置参数

| 参数 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| Access Token 过期 | `ACCESS_TOKEN_EXPIRE_MINUTES` | 15 | 分钟 |
| Refresh Token 过期 | `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | 天 |
| JWT Secret Key | `JWT_SECRET_KEY` | 必填 | >= 32 字符 |

## 安全特性

1. **Token 轮换**: 每次刷新生成新 RT，旧 RT 立即失效
2. **哈希存储**: Refresh Token 使用 SHA256 哈希后存储
3. **类型标识**: Access Token 包含 `type: "access"` 防止误用
4. **撤销支持**: 登出时撤销 Refresh Token
5. **并发安全**: 前端使用刷新锁防止并发刷新

## 验证结果

```bash
# 配置验证
Access Token: 15 minutes
Refresh Token: 7 days
Token pair created successfully

# 依赖验证
All dependencies imported successfully
```

## 使用示例

### 登录
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'

# 响应
{
  "access_token": "eyJ...",
  "refresh_token": "a1b2c3...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {...}
}
```

### 刷新
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "a1b2c3..."}'

# 响应 (新的 token 对)
{
  "access_token": "eyJ...(新)",
  "refresh_token": "x7y8z9...(新)",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {...}
}
```

### 登出
```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "a1b2c3..."}'

# 响应
{"message": "Successfully logged out"}
```

## 前端自动刷新流程

```
1. 请求 API → 401 错误
2. 检查是否有 refresh_token
3. 如果正在刷新，加入队列等待
4. 调用 /auth/refresh 获取新 token
5. 更新 localStorage
6. 重试原始请求
7. 处理队列中的等待请求
```

## 多实例部署

- 所有实例使用相同的 `JWT_SECRET_KEY` 环境变量
- Refresh Token 存储在共享数据库
- Access Token 无状态，任何实例可验证

---

**实现完成，可投入使用。**
