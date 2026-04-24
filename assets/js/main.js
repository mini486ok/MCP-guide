/* =========================================================
   Python MCP 서버 가이드라인 - 공통 스크립트
   - 모바일 사이드바 토글
   - 코드 블록 복사 버튼 자동 주입
   - 스크롤 진행률 바
   - 다크 모드 토글 (localStorage)
   - 현재 페이지 사이드바 하이라이트
   ========================================================= */

(function () {
    "use strict";

    /* ----- 1. 다크 모드 ----- */
    const THEME_KEY = "mcp-guide-theme";
    const root = document.documentElement;

    function applyTheme(theme) {
        if (theme === "dark") {
            root.setAttribute("data-theme", "dark");
        } else {
            root.removeAttribute("data-theme");
        }
    }

    function initTheme() {
        const stored = localStorage.getItem(THEME_KEY);
        const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
        const theme = stored || (prefersDark ? "dark" : "light");
        applyTheme(theme);
    }

    function toggleTheme() {
        const current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
        const next = current === "dark" ? "light" : "dark";
        applyTheme(next);
        localStorage.setItem(THEME_KEY, next);
        updateThemeButtons(next);
    }

    function updateThemeButtons(theme) {
        document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
            btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
            const labelEl = btn.querySelector(".theme-label");
            if (labelEl) labelEl.textContent = theme === "dark" ? "라이트 모드" : "다크 모드";
        });
    }

    initTheme();

    /* ----- 2. 모바일 사이드바 토글 ----- */
    const sidebar = document.querySelector(".sidebar");
    const backdrop = document.querySelector(".sidebar-backdrop");

    function openSidebar() {
        if (!sidebar) return;
        sidebar.classList.add("open");
        if (backdrop) {
            backdrop.classList.add("show");
        }
        document.body.style.overflow = "hidden";
    }

    function closeSidebar() {
        if (!sidebar) return;
        sidebar.classList.remove("open");
        if (backdrop) backdrop.classList.remove("show");
        document.body.style.overflow = "";
    }

    /* ----- 3. 현재 페이지 하이라이트 ----- */
    function highlightCurrent() {
        const here = (location.pathname.split("/").pop() || "index.html").toLowerCase();
        document.querySelectorAll(".sidebar nav a").forEach((a) => {
            const href = (a.getAttribute("href") || "").toLowerCase();
            if (href === here || (here === "" && href === "index.html")) {
                a.setAttribute("aria-current", "page");
            } else {
                a.removeAttribute("aria-current");
            }
        });
    }

    /* ----- 4. 코드 블록 복사 버튼 자동 주입 ----- */
    function injectCopyButtons() {
        document.querySelectorAll(".code-wrap").forEach((wrap) => {
            if (wrap.querySelector(".copy-btn")) return;
            const head = wrap.querySelector(".code-head");
            if (!head) return;
            const btn = document.createElement("button");
            btn.className = "copy-btn";
            btn.type = "button";
            btn.setAttribute("aria-label", "코드 복사");
            btn.textContent = "복사";
            btn.addEventListener("click", async () => {
                const code = wrap.querySelector("pre");
                if (!code) return;
                const text = code.innerText;
                try {
                    await navigator.clipboard.writeText(text);
                } catch (e) {
                    // Fallback
                    const ta = document.createElement("textarea");
                    ta.value = text;
                    document.body.appendChild(ta);
                    ta.select();
                    try { document.execCommand("copy"); } catch (_) {}
                    ta.remove();
                }
                btn.classList.add("copied");
                btn.textContent = "복사됨";
                showToast("코드가 복사되었습니다");
                setTimeout(() => {
                    btn.classList.remove("copied");
                    btn.textContent = "복사";
                }, 1600);
            });
            head.appendChild(btn);
        });
    }

    /* ----- 5. 토스트 ----- */
    let toastEl = null;
    let toastTimer = null;
    function showToast(msg) {
        if (!toastEl) {
            toastEl = document.createElement("div");
            toastEl.className = "toast";
            toastEl.setAttribute("role", "status");
            toastEl.setAttribute("aria-live", "polite");
            document.body.appendChild(toastEl);
        }
        toastEl.textContent = msg;
        toastEl.classList.add("show");
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => {
            toastEl.classList.remove("show");
        }, 1800);
    }

    /* ----- 6. 스크롤 진행률 바 ----- */
    function initProgress() {
        const bar = document.querySelector(".progress-bar");
        if (!bar) return;
        let ticking = false;
        function update() {
            const doc = document.documentElement;
            const scrollTop = window.scrollY || doc.scrollTop;
            const max = doc.scrollHeight - window.innerHeight;
            const pct = max > 0 ? Math.min(100, (scrollTop / max) * 100) : 0;
            bar.style.width = pct + "%";
            ticking = false;
        }
        window.addEventListener("scroll", () => {
            if (!ticking) {
                window.requestAnimationFrame(update);
                ticking = true;
            }
        }, { passive: true });
        update();
    }

    /* ----- 7. 이벤트 바인딩 ----- */
    document.addEventListener("DOMContentLoaded", () => {
        highlightCurrent();
        injectCopyButtons();
        initProgress();

        // 햄버거
        document.querySelectorAll("[data-sidebar-open]").forEach((btn) =>
            btn.addEventListener("click", openSidebar)
        );
        document.querySelectorAll("[data-sidebar-close]").forEach((btn) =>
            btn.addEventListener("click", closeSidebar)
        );
        if (backdrop) backdrop.addEventListener("click", closeSidebar);
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") closeSidebar();
        });

        // 사이드바 링크 클릭 시 모바일에서는 닫기
        document.querySelectorAll(".sidebar nav a").forEach((a) =>
            a.addEventListener("click", () => {
                if (window.matchMedia("(max-width: 767px)").matches) closeSidebar();
            })
        );

        // 테마 토글
        document.querySelectorAll("[data-theme-toggle]").forEach((btn) =>
            btn.addEventListener("click", toggleTheme)
        );
        updateThemeButtons(root.getAttribute("data-theme") === "dark" ? "dark" : "light");

        // "맨 위로" 버튼
        document.querySelectorAll("[data-scroll-top]").forEach((btn) =>
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                window.scrollTo({ top: 0, behavior: "smooth" });
            })
        );
    });
})();
