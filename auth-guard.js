/**
 * ============================================================
 *  auth-guard.js —— “刷新后必须重新登录才能跳转进入网站”守卫
 * ============================================================
 *
 *  实现机制（一次性登录票据）：
 *
 *    1. index.html（登录页）验证密钥通过后，调用 WBAuth.grant()
 *       在 localStorage 写入一张“一次性票据”；
 *
 *    2. workbench.html（工作台）每次加载时调用 WBAuth.verify()：
 *       - 票据存在 → 立即消费（删除）→ 放行，本次可以正常使用；
 *       - 票据不存在（说明是【刷新】、直接输入网址打开、
 *         或票据已被上一次加载消费）→ 强制跳回登录页。
 *
 *    3. 因为票据是一次性的，页面一刷新就不再存在，
 *       所以用户每次刷新后都必须重新登录才能进入网站。
 *
 *  使用方法：
 *    <script src="auth-guard.js"></script>
 *    登录成功后：      WBAuth.grant();
 *    工作台加载时：    if (!WBAuth.verify()) { 跳回登录页 }
 *    退出登录时：      WBAuth.logout();
 * ============================================================
 */
(function (global) {
    'use strict';

    /** 一次性票据在 localStorage 中的键名 */
    var TICKET_KEY = 'workbench_login_ticket';

    /** 登录页地址（校验失败时跳回这里） */
    var LOGIN_PAGE = 'index.html';

    var WBAuth = {

        /**
         * 发放一次性登录票据。
         * 登录页验证密钥成功后、跳转工作台之前调用。
         */
        grant: function () {
            try {
                localStorage.setItem(TICKET_KEY, String(Date.now()));
            } catch (e) {
                /* localStorage 不可用时静默失败，verify 会拒绝放行 */
            }
        },

        /**
         * 校验并消费一次性票据。
         * 只能通过一次：第一次进入工作台（刚登录跳转过来）放行；
         * 之后任何刷新 / 直接打开都会因为票据已不存在而失败。
         *
         * @returns {boolean} true = 放行；false = 需要重新登录
         */
        verify: function () {
            var ok = false;
            try {
                ok = !!localStorage.getItem(TICKET_KEY);
                // 立即消费票据，保证“一次性”
                localStorage.removeItem(TICKET_KEY);
            } catch (e) {
                ok = false;
            }
            return ok;
        },

        /**
         * 退出登录：清空票据和已保存的访问密钥。
         */
        logout: function () {
            try {
                localStorage.removeItem(TICKET_KEY);
                localStorage.removeItem('workbench_access_key');
            } catch (e) { /* 忽略 */ }
        },

        /**
         * 跳转到登录页（强制重新登录）。
         */
        redirectToLogin: function () {
            global.location.href = LOGIN_PAGE;
        }
    };

    // 暴露到全局，供 index.html / workbench.html 使用
    global.WBAuth = WBAuth;
})(window);
