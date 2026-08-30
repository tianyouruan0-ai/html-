-- ============================================================
-- 任务管理器云同步 · Supabase 建表脚本
-- ============================================================
-- 使用方法：
--   1. 打开 https://supabase.com 并登录（就是你「新登录工作台」用的那个账号）
--   2. 进入你的项目（oidrtpdaplsnctxkeml）
--   3. 左侧菜单点击「SQL Editor」→ New query
--   4. 把本文件全部内容粘贴进去，点 Run 执行
--   5. 显示 Success 即完成，任务数据从此存到云端，所有设备同步
--
-- 说明：
--   - 每个登录账号在表中占一行，任务列表以 JSON 形式整存整取
--   - 手机 / 电脑 / 任何浏览器登录同一账号 → 看到同一份任务数据
-- ============================================================

-- 任务数据表：按账号存储任务列表
create table if not exists public.app_tasks (
    username    text primary key,          -- 登录账号（主键，一个账号一条记录）
    data        jsonb not null default '[]'::jsonb,  -- 任务列表 JSON
    updated_at  timestamptz not null default now()  -- 最后同步时间
);

-- 更新时间自动刷新
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_app_tasks_touch on public.app_tasks;
create trigger trg_app_tasks_touch
    before update on public.app_tasks
    for each row execute function public.touch_updated_at();

-- 行级安全（RLS）：开放给匿名密钥读写
-- ⚠️ 安全等级与你现有项目（新登录工作台）一致：匿名密钥本身就在前端网页里公开。
--    如需更严格（按登录会话隔离数据），需要接入 Supabase Auth，可让助手升级。
alter table public.app_tasks enable row level security;

drop policy if exists "app_tasks public read" on public.app_tasks;
create policy "app_tasks public read" on public.app_tasks
    for select to anon, authenticated using (true);

drop policy if exists "app_tasks public write" on public.app_tasks;
create policy "app_tasks public write" on public.app_tasks
    for insert to anon, authenticated with check (true);

drop policy if exists "app_tasks public update" on public.app_tasks;
    for update to anon, authenticated using (true) with check (true);
