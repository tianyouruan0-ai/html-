<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>动态登录页面</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="login-container">
        <form id="loginForm">
            <h2>登录</h2>

            <div class="input-group">
                <label for="username">用户名</label>
                <input type="text" id="username" name="username"
                       autocomplete="username" placeholder="请输入用户名" required>
            </div>

            <div class="input-group">
                <label for="password">密码</label>
                <input type="password" id="password" name="password"
                       autocomplete="current-password" placeholder="请输入密码" required>
                <span class="toggle-pwd" id="togglePwd">👁️</span>
            </div>

            <!-- 记住我选项 -->
            <div class="remember-group">
                <label class="remember-label">
                    <input type="checkbox" id="rememberMe" class="remember-checkbox">
                    <span class="remember-text">记住我</span>
                </label>
                <a href="#" class="forgot-link">忘记密码？</a>
            </div>

            <button type="submit" class="login-btn">登录</button>
            <div id="loginMessage"></div>
        </form>
    </div>
    <script src="script.js"></script>
</body>
</html>