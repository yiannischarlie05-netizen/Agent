/**
 * Local Coding Agent - Frontend Application
 */

(function () {
    "use strict";

    // === State ===
    const state = {
        workspace: "",
        currentFile: null,
        originalContent: "",
        socket: null,
        commandHistory: [],
        historyIndex: -1,
    };

    // === DOM Elements ===
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const els = {
        workspaceInput: $("#workspace-input"),
        btnSetWorkspace: $("#btn-set-workspace"),
        btnAnalyze: $("#btn-analyze"),
        btnGitStatus: $("#btn-git-status"),
        btnNewFile: $("#btn-new-file"),
        btnRefresh: $("#btn-refresh"),
        fileTree: $("#file-tree"),
        taskInput: $("#task-input"),
        btnExecuteTask: $("#btn-execute-task"),
        btnClearTask: $("#btn-clear-task"),
        outputContent: $("#output-content"),
        codeEditor: $("#code-editor"),
        lineNumbers: $("#line-numbers"),
        editorFilename: $("#editor-filename"),
        btnSaveFile: $("#btn-save-file"),
        btnFindIssues: $("#btn-find-issues"),
        diffContent: $("#diff-content"),
        terminalOutput: $("#terminal-output"),
        terminalInput: $("#terminal-input"),
        projectInfo: $("#project-info"),
        taskHistory: $("#task-history"),
        statusText: $("#status-text"),
        connectionStatus: $("#connection-status"),
        modalOverlay: $("#modal-overlay"),
        modalTitle: $("#modal-title"),
        modalInput: $("#modal-input"),
        modalTextarea: $("#modal-textarea"),
        btnModalCancel: $("#btn-modal-cancel"),
        btnModalConfirm: $("#btn-modal-confirm"),
    };

    // === API Helper ===
    async function api(url, options = {}) {
        try {
            const resp = await fetch(url, {
                headers: { "Content-Type": "application/json", ...options.headers },
                ...options,
            });
            return await resp.json();
        } catch (err) {
            return { error: err.message };
        }
    }

    // === Status ===
    function setStatus(text) {
        els.statusText.textContent = text;
    }

    // === WebSocket ===
    function initSocket() {
        try {
            state.socket = io();

            state.socket.on("connect", () => {
                els.connectionStatus.textContent = "● Connected";
                els.connectionStatus.className = "connected";
            });

            state.socket.on("disconnect", () => {
                els.connectionStatus.textContent = "● Disconnected";
                els.connectionStatus.className = "disconnected";
            });

            state.socket.on("connected", (data) => {
                if (data.workspace) {
                    state.workspace = data.workspace;
                    els.workspaceInput.value = data.workspace;
                }
            });

            state.socket.on("command_start", (data) => {
                appendTerminal(`$ ${data.command}`, "terminal-cmd");
            });

            state.socket.on("command_result", (data) => {
                if (data.stdout) appendTerminal(data.stdout);
                if (data.stderr) appendTerminal(data.stderr, "terminal-error");
                if (data.error) appendTerminal(`Error: ${data.error}`, "terminal-error");
                setStatus("Ready");
            });

            state.socket.on("task_start", (data) => {
                appendOutput(`Task started: ${data.description}`, "info");
            });

            state.socket.on("task_plan", (data) => {
                appendOutput(formatPlan(data), "success");
            });

            state.socket.on("task_complete", (data) => {
                appendOutput(`Task ${data.task_id} completed.`, "success");
                setStatus("Ready");
                loadTaskHistory();
            });
        } catch (e) {
            console.warn("WebSocket not available, using REST API only");
        }
    }

    // === Output Panel ===
    function appendOutput(content, type = "info") {
        const welcome = els.outputContent.querySelector(".welcome-message");
        if (welcome) welcome.remove();

        const entry = document.createElement("div");
        entry.className = `output-entry ${type === "error" ? "error" : type === "success" ? "success" : ""}`;

        const header = document.createElement("div");
        header.className = "output-header";
        header.innerHTML = `<span>${new Date().toLocaleTimeString()}</span><span>${type.toUpperCase()}</span>`;

        const pre = document.createElement("pre");
        if (typeof content === "object") {
            pre.textContent = JSON.stringify(content, null, 2);
        } else {
            pre.textContent = content;
        }

        entry.appendChild(header);
        entry.appendChild(pre);
        els.outputContent.appendChild(entry);
        els.outputContent.scrollTop = els.outputContent.scrollHeight;
    }

    function formatPlan(plan) {
        let text = `=== Task Plan ===\n`;
        text += `Task ID: ${plan.task_id}\n`;
        text += `Description: ${plan.description}\n`;
        text += `Workspace: ${plan.workspace}\n\n`;

        if (plan.project_info) {
            const info = plan.project_info;
            text += `--- Project Info ---\n`;
            text += `Files: ${info.total_files} | Lines: ${info.total_lines}\n`;
            text += `Languages: ${Object.entries(info.languages || {}).map(([k, v]) => `${k}(${v})`).join(", ")}\n`;
            if (info.build_systems?.length) {
                text += `Build Systems: ${info.build_systems.join(", ")}\n`;
            }
            text += `Git: ${info.has_git ? "Yes" : "No"}\n`;
        }

        if (plan.git_info?.status?.stdout) {
            text += `\n--- Git Status ---\n${plan.git_info.status.stdout}`;
        }

        return text;
    }

    // === Terminal ===
    function appendTerminal(text, className = "") {
        const line = document.createElement("div");
        if (className) line.className = className;
        line.textContent = text;
        els.terminalOutput.appendChild(line);
        els.terminalOutput.scrollTop = els.terminalOutput.scrollHeight;
    }

    async function runCommand(command) {
        if (!command.trim()) return;

        state.commandHistory.push(command);
        state.historyIndex = state.commandHistory.length;

        setStatus(`Running: ${command}`);
        appendTerminal(`$ ${command}`, "terminal-cmd");

        const result = await api("/api/action", {
            method: "POST",
            body: JSON.stringify({
                action: "run_command",
                params: { command: command, cwd: state.workspace },
            }),
        });

        if (result.stdout) appendTerminal(result.stdout);
        if (result.stderr) appendTerminal(result.stderr, "terminal-error");
        if (result.error) appendTerminal(`Error: ${result.error}`, "terminal-error");

        setStatus("Ready");
    }

    // === File Explorer ===
    async function loadFileTree(path, parentEl, depth = 0) {
        if (!path) return;

        const result = await api(`/api/files?path=${encodeURIComponent(path)}`);
        if (result.error) {
            appendOutput(result.error, "error");
            return;
        }

        if (depth === 0) {
            els.fileTree.innerHTML = "";
            parentEl = els.fileTree;
        }

        const entries = result.entries || [];
        // Sort: directories first, then files
        entries.sort((a, b) => {
            if (a.is_dir === b.is_dir) return a.name.localeCompare(b.name);
            return a.is_dir ? -1 : 1;
        });

        for (const entry of entries) {
            const item = document.createElement("div");
            item.className = `file-item ${entry.is_dir ? "directory" : "file"}`;
            item.dataset.path = entry.path;
            item.dataset.depth = depth;

            const icon = document.createElement("span");
            icon.className = "icon";
            icon.textContent = entry.is_dir ? "📁" : getFileIcon(entry.name);

            const name = document.createElement("span");
            name.className = "name";
            name.textContent = entry.name;

            item.appendChild(icon);
            item.appendChild(name);
            parentEl.appendChild(item);

            if (entry.is_dir) {
                const childContainer = document.createElement("div");
                childContainer.className = "hidden";
                childContainer.dataset.dirPath = entry.path;
                parentEl.appendChild(childContainer);

                item.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    if (childContainer.classList.contains("hidden")) {
                        if (childContainer.children.length === 0) {
                            await loadFileTree(entry.path, childContainer, depth + 1);
                        }
                        childContainer.classList.remove("hidden");
                        icon.textContent = "📂";
                    } else {
                        childContainer.classList.add("hidden");
                        icon.textContent = "📁";
                    }
                });
            } else {
                item.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    await openFile(entry.path);
                });
            }
        }
    }

    function getFileIcon(name) {
        const ext = name.split(".").pop().toLowerCase();
        const icons = {
            py: "🐍", js: "📜", ts: "📘", jsx: "⚛️", tsx: "⚛️",
            html: "🌐", css: "🎨", json: "📋", md: "📝",
            sh: "💻", bash: "💻", yml: "⚙️", yaml: "⚙️",
            go: "🔵", rs: "🦀", java: "☕", rb: "💎",
            c: "⚡", cpp: "⚡", h: "⚡", hpp: "⚡",
            sql: "🗄️", xml: "📄", toml: "⚙️",
            txt: "📄", log: "📄", csv: "📊",
            png: "🖼️", jpg: "🖼️", gif: "🖼️", svg: "🖼️",
            zip: "📦", tar: "📦", gz: "📦",
        };
        return icons[ext] || "📄";
    }

    // === File Editor ===
    async function openFile(path) {
        setStatus(`Opening: ${path}`);
        const result = await api(`/api/file?path=${encodeURIComponent(path)}`);
        if (result.error) {
            appendOutput(result.error, "error");
            setStatus("Ready");
            return;
        }

        state.currentFile = path;
        state.originalContent = result.content;

        els.editorFilename.textContent = path;
        els.codeEditor.value = result.content;
        els.btnSaveFile.disabled = false;
        els.btnFindIssues.disabled = false;

        updateLineNumbers();
        switchTab("editor");
        setStatus(`Opened: ${path}`);

        // Highlight active file
        $$(".file-item").forEach((el) => el.classList.remove("active"));
        const activeItem = $(`.file-item[data-path="${CSS.escape(path)}"]`);
        if (activeItem) activeItem.classList.add("active");
    }

    function updateLineNumbers() {
        const lines = els.codeEditor.value.split("\n");
        els.lineNumbers.textContent = lines.map((_, i) => i + 1).join("\n");
    }

    async function saveFile() {
        if (!state.currentFile) return;

        setStatus("Saving...");
        const content = els.codeEditor.value;
        const result = await api("/api/file", {
            method: "PUT",
            body: JSON.stringify({ path: state.currentFile, content }),
        });

        if (result.error) {
            appendOutput(`Failed to save: ${result.error}`, "error");
        } else {
            appendOutput(`Saved: ${state.currentFile}`, "success");
            // Show diff if content changed
            if (state.originalContent !== content) {
                showDiff(state.originalContent, content, state.currentFile);
            }
            state.originalContent = content;
        }
        setStatus("Ready");
    }

    // === Diff View ===
    function showDiff(original, modified, filename) {
        const origLines = original.split("\n");
        const modLines = modified.split("\n");

        let html = `<div class="diff-header">--- a/${filename}</div>`;
        html += `<div class="diff-header">+++ b/${filename}</div>`;

        // Simple line-by-line diff
        const maxLen = Math.max(origLines.length, modLines.length);
        for (let i = 0; i < maxLen; i++) {
            if (i >= origLines.length) {
                html += `<div class="diff-line diff-add">+ ${escapeHtml(modLines[i])}</div>`;
            } else if (i >= modLines.length) {
                html += `<div class="diff-line diff-remove">- ${escapeHtml(origLines[i])}</div>`;
            } else if (origLines[i] !== modLines[i]) {
                html += `<div class="diff-line diff-remove">- ${escapeHtml(origLines[i])}</div>`;
                html += `<div class="diff-line diff-add">+ ${escapeHtml(modLines[i])}</div>`;
            } else {
                html += `<div class="diff-line">  ${escapeHtml(origLines[i])}</div>`;
            }
        }

        els.diffContent.innerHTML = html;
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // === Tab Switching ===
    function switchTab(tabName) {
        $$(".tab").forEach((t) => t.classList.remove("active"));
        $$(".tab-content").forEach((c) => c.classList.remove("active"));

        const tab = $(`.tab[data-tab="${tabName}"]`);
        const content = $(`#${tabName}-panel`);
        if (tab) tab.classList.add("active");
        if (content) content.classList.add("active");
    }

    // === Project Analysis ===
    async function analyzeProject() {
        setStatus("Analyzing project...");
        const result = await api("/api/analyze");
        if (result.error) {
            appendOutput(result.error, "error");
            setStatus("Ready");
            return;
        }

        displayProjectInfo(result);
        appendOutput(result, "success");
        setStatus("Ready");
    }

    function displayProjectInfo(info) {
        let html = "";
        html += `<div class="info-item"><span class="label">Files</span><span class="value">${info.total_files || 0}</span></div>`;
        html += `<div class="info-item"><span class="label">Lines</span><span class="value">${(info.total_lines || 0).toLocaleString()}</span></div>`;
        html += `<div class="info-item"><span class="label">Git</span><span class="value">${info.has_git ? "✓" : "✗"}</span></div>`;

        if (info.languages) {
            const top = Object.entries(info.languages)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);
            for (const [lang, count] of top) {
                html += `<div class="info-item"><span class="label">${lang}</span><span class="value">${count}</span></div>`;
            }
        }

        if (info.build_systems?.length) {
            html += `<div class="info-item"><span class="label">Build</span><span class="value">${info.build_systems.join(", ")}</span></div>`;
        }

        els.projectInfo.innerHTML = html;
    }

    // === Git Status ===
    async function gitStatus() {
        setStatus("Getting git status...");
        const [status, diff, log] = await Promise.all([
            api("/api/git/status"),
            api("/api/git/diff"),
            api("/api/git/log?count=10"),
        ]);

        let output = "=== Git Status ===\n";
        output += status.stdout || status.error || "Not a git repository\n";
        output += "\n=== Recent Commits ===\n";
        output += log.stdout || log.error || "No commits\n";

        appendOutput(output, "info");

        if (diff.stdout) {
            els.diffContent.innerHTML = formatGitDiff(diff.stdout);
        }

        setStatus("Ready");
    }

    function formatGitDiff(diffText) {
        return diffText
            .split("\n")
            .map((line) => {
                let cls = "diff-line";
                if (line.startsWith("+")) cls += " diff-add";
                else if (line.startsWith("-")) cls += " diff-remove";
                else if (line.startsWith("@@")) cls += " diff-hunk";
                else if (line.startsWith("diff ")) cls += " diff-header";
                return `<div class="${cls}">${escapeHtml(line)}</div>`;
            })
            .join("");
    }

    // === Task History ===
    async function loadTaskHistory() {
        const result = await api("/api/history");
        if (!result.tasks?.length) return;

        els.taskHistory.innerHTML = "";
        for (const task of result.tasks.slice(-10).reverse()) {
            const item = document.createElement("div");
            item.className = "history-item";
            item.innerHTML = `<div class="time">${task.timestamp}</div>${task.description}`;
            item.addEventListener("click", () => {
                els.taskInput.value = task.description;
            });
            els.taskHistory.appendChild(item);
        }
    }

    // === Modal ===
    function showModal(title, placeholder, onConfirm) {
        els.modalTitle.textContent = title;
        els.modalInput.placeholder = placeholder;
        els.modalInput.value = "";
        els.modalOverlay.classList.remove("hidden");

        els.btnModalConfirm.onclick = () => {
            onConfirm(els.modalInput.value);
            els.modalOverlay.classList.add("hidden");
        };
    }

    // === Event Listeners ===
    function initEventListeners() {
        // Workspace
        els.btnSetWorkspace.addEventListener("click", async () => {
            const path = els.workspaceInput.value.trim();
            if (!path) return;
            const result = await api("/api/workspace", {
                method: "POST",
                body: JSON.stringify({ path }),
            });
            if (result.error) {
                appendOutput(result.error, "error");
            } else {
                state.workspace = result.workspace;
                loadFileTree(result.workspace, els.fileTree);
                appendOutput(`Workspace set to: ${result.workspace}`, "success");
            }
        });

        els.workspaceInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") els.btnSetWorkspace.click();
        });

        // Analyze & Git
        els.btnAnalyze.addEventListener("click", analyzeProject);
        els.btnGitStatus.addEventListener("click", gitStatus);

        // File explorer
        els.btnRefresh.addEventListener("click", () => {
            if (state.workspace) loadFileTree(state.workspace, els.fileTree);
        });

        els.btnNewFile.addEventListener("click", () => {
            showModal("New File", "Enter file path (relative to workspace)...", async (path) => {
                if (!path) return;
                const result = await api("/api/file", {
                    method: "POST",
                    body: JSON.stringify({ path, content: "" }),
                });
                if (result.error) {
                    appendOutput(result.error, "error");
                } else {
                    appendOutput(`Created: ${path}`, "success");
                    if (state.workspace) loadFileTree(state.workspace, els.fileTree);
                }
            });
        });

        // Task
        els.btnExecuteTask.addEventListener("click", async () => {
            const desc = els.taskInput.value.trim();
            if (!desc) return;

            setStatus("Processing task...");
            if (state.socket?.connected) {
                state.socket.emit("execute_task", { description: desc });
            } else {
                const result = await api("/api/task", {
                    method: "POST",
                    body: JSON.stringify({ description: desc }),
                });
                appendOutput(formatPlan(result), result.error ? "error" : "success");
                setStatus("Ready");
                loadTaskHistory();
            }
        });

        els.btnClearTask.addEventListener("click", () => {
            els.taskInput.value = "";
        });

        els.taskInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                els.btnExecuteTask.click();
            }
        });

        // Editor
        els.codeEditor.addEventListener("input", updateLineNumbers);
        els.codeEditor.addEventListener("scroll", () => {
            els.lineNumbers.scrollTop = els.codeEditor.scrollTop;
        });
        els.codeEditor.addEventListener("keydown", (e) => {
            if (e.key === "Tab") {
                e.preventDefault();
                const start = els.codeEditor.selectionStart;
                const end = els.codeEditor.selectionEnd;
                els.codeEditor.value =
                    els.codeEditor.value.substring(0, start) + "    " + els.codeEditor.value.substring(end);
                els.codeEditor.selectionStart = els.codeEditor.selectionEnd = start + 4;
                updateLineNumbers();
            }
            if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                e.preventDefault();
                saveFile();
            }
        });

        els.btnSaveFile.addEventListener("click", saveFile);
        els.btnFindIssues.addEventListener("click", async () => {
            if (!state.currentFile) return;
            setStatus("Finding issues...");
            const result = await api(`/api/issues?path=${encodeURIComponent(state.currentFile)}`);
            if (result.issues?.length) {
                appendOutput(`Found ${result.issues.length} issues in ${state.currentFile}:\n` +
                    result.issues.map((i) => `  Line ${i.line}: [${i.type}] ${i.message}`).join("\n"),
                    "info"
                );
            } else {
                appendOutput(`No issues found in ${state.currentFile}`, "success");
            }
            setStatus("Ready");
        });

        // Tabs
        $$(".tab").forEach((tab) => {
            tab.addEventListener("click", () => switchTab(tab.dataset.tab));
        });

        // Terminal
        els.terminalInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                const cmd = els.terminalInput.value;
                els.terminalInput.value = "";
                runCommand(cmd);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                if (state.historyIndex > 0) {
                    state.historyIndex--;
                    els.terminalInput.value = state.commandHistory[state.historyIndex];
                }
            } else if (e.key === "ArrowDown") {
                e.preventDefault();
                if (state.historyIndex < state.commandHistory.length - 1) {
                    state.historyIndex++;
                    els.terminalInput.value = state.commandHistory[state.historyIndex];
                } else {
                    state.historyIndex = state.commandHistory.length;
                    els.terminalInput.value = "";
                }
            }
        });

        // Quick commands
        $$(".quick-cmd").forEach((btn) => {
            btn.addEventListener("click", () => {
                const cmd = btn.dataset.cmd;
                switchTab("terminal");
                runCommand(cmd);
            });
        });

        // Modal
        els.btnModalCancel.addEventListener("click", () => {
            els.modalOverlay.classList.add("hidden");
        });

        els.modalOverlay.addEventListener("click", (e) => {
            if (e.target === els.modalOverlay) {
                els.modalOverlay.classList.add("hidden");
            }
        });
    }

    // === Initialize ===
    async function init() {
        initEventListeners();
        initSocket();

        // Load initial workspace
        const result = await api("/api/workspace");
        if (result.workspace) {
            state.workspace = result.workspace;
            els.workspaceInput.value = result.workspace;
            loadFileTree(result.workspace, els.fileTree);
        }

        setStatus("Ready");
    }

    document.addEventListener("DOMContentLoaded", init);
})();
